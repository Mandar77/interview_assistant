"""
Speech Streaming - WebSocket handler for real-time transcription
Location: backend/services/speech_service/streaming.py
"""

import asyncio
import logging
import tempfile
import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
import wave
import io

from fastapi import WebSocket, WebSocketDisconnect
import numpy as np

from services.speech_service.transcriber import transcriber
from services.speech_service.analyzer import speech_analyzer, analyze_speech, analyze_language
from services.speech_service.session_store import session_store

logger = logging.getLogger(__name__)


@dataclass
class StreamingSession:
    """Tracks state for a streaming transcription session."""
    session_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    audio_chunks: List[bytes] = field(default_factory=list)
    partial_transcripts: List[Dict] = field(default_factory=list)
    full_transcript: str = ""
    total_audio_bytes: int = 0
    chunk_count: int = 0
    is_active: bool = True
    last_activity: datetime = field(default_factory=datetime.utcnow)


class SpeechStreamingHandler:
    """
    Handle real-time speech streaming via WebSocket.
    Buffers audio chunks, runs incremental transcription, and emits partial results.
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, StreamingSession] = {}
        self.transcription_buffer_size = 5  # Process every N chunks
        self.min_audio_duration_ms = 1000  # Minimum audio for transcription
        
    async def handle_connection(self, websocket: WebSocket, session_id: str):
        """
        Main WebSocket handler for speech streaming.
        
        Protocol:
        - Client sends binary audio chunks (webm/opus or raw PCM)
        - Server responds with JSON: {"partial_transcript": "...", "is_final": false}
        - On disconnect, server finalizes and persists the session
        """
        await websocket.accept()
        logger.info(f"WebSocket connected for session: {session_id}")
        
        # Initialize session
        session = StreamingSession(session_id=session_id)
        self.active_sessions[session_id] = session
        
        # Send acknowledgment
        await websocket.send_json({
            "type": "connected",
            "session_id": session_id,
            "message": "Ready to receive audio"
        })
        
        try:
            while True:
                # Receive audio chunk (binary)
                data = await websocket.receive()
                
                if "bytes" in data:
                    await self._process_audio_chunk(websocket, session, data["bytes"])
                elif "text" in data:
                    # Handle control messages
                    await self._handle_control_message(websocket, session, data["text"])
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error for session {session_id}: {e}")
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        finally:
            # Finalize session
            await self._finalize_session(session)
            del self.active_sessions[session_id]
    
    async def _process_audio_chunk(
        self,
        websocket: WebSocket,
        session: StreamingSession,
        audio_bytes: bytes
    ):
        """Process incoming audio chunk."""
        session.audio_chunks.append(audio_bytes)
        session.total_audio_bytes += len(audio_bytes)
        session.chunk_count += 1
        session.last_activity = datetime.utcnow()
        
        # Process every N chunks or when buffer is large enough
        if session.chunk_count % self.transcription_buffer_size == 0:
            await self._run_incremental_transcription(websocket, session)
    
    async def _run_incremental_transcription(
        self,
        websocket: WebSocket,
        session: StreamingSession
    ):
        """Run transcription on buffered audio and emit partial result."""
        if not session.audio_chunks:
            return
        
        try:
            # Combine recent chunks for transcription
            combined_audio = b''.join(session.audio_chunks[-self.transcription_buffer_size:])
            
            # Save to temp file for Whisper
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(combined_audio)
                tmp_path = tmp.name
            
            try:
                # Run transcription (this blocks - consider running in thread pool)
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: transcriber.transcribe(tmp_path, word_timestamps=False)
                )
                
                partial_text = result.get("text", "").strip()
                
                if partial_text:
                    # Store partial transcript
                    partial_entry = {
                        "text": partial_text,
                        "timestamp": datetime.utcnow().isoformat(),
                        "chunk_index": session.chunk_count
                    }
                    session.partial_transcripts.append(partial_entry)
                    
                    # Send to client
                    await websocket.send_json({
                        "type": "partial_transcript",
                        "partial_transcript": partial_text,
                        "is_final": False,
                        "chunk_index": session.chunk_count
                    })
                    
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except Exception as e:
            logger.error(f"Incremental transcription failed: {e}")
            await websocket.send_json({
                "type": "transcription_error",
                "message": str(e)
            })
    
    async def _handle_control_message(
        self,
        websocket: WebSocket,
        session: StreamingSession,
        message: str
    ):
        """Handle text control messages from client."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "end_session":
                session.is_active = False
                await self._finalize_session(session)
                await websocket.send_json({
                    "type": "session_ended",
                    "session_id": session.session_id
                })
                
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
            elif msg_type == "get_status":
                await websocket.send_json({
                    "type": "status",
                    "session_id": session.session_id,
                    "chunk_count": session.chunk_count,
                    "total_bytes": session.total_audio_bytes,
                    "partial_count": len(session.partial_transcripts)
                })
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid control message: {message}")
    
    async def _finalize_session(self, session: StreamingSession):
        """Finalize session: full transcription, metrics, and persistence."""
        logger.info(f"Finalizing session: {session.session_id}")
        
        if not session.audio_chunks:
            logger.warning(f"No audio data for session {session.session_id}")
            return
        
        try:
            # Combine all audio chunks
            full_audio = b''.join(session.audio_chunks)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(full_audio)
                tmp_path = tmp.name
            
            try:
                # Full transcription
                transcription = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: transcriber.transcribe(tmp_path, word_timestamps=True)
                )
                
                session.full_transcript = transcription.get("text", "")
                
                # Analyze speech metrics
                speech_metrics = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: analyze_speech(transcription)
                )
                
                # Analyze language metrics
                language_metrics = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: analyze_language(session.full_transcript)
                )
                
                # Persist to session store
                session_data = {
                    "session_id": session.session_id,
                    "started_at": session.started_at.isoformat(),
                    "ended_at": datetime.utcnow().isoformat(),
                    "transcription": {
                        "full_text": session.full_transcript,
                        "duration_seconds": transcription.get("duration_seconds", 0),
                        "confidence": transcription.get("confidence", 0),
                        "word_count": transcription.get("word_count", 0),
                        "segments": transcription.get("segments", [])
                    },
                    "partial_transcripts": session.partial_transcripts,
                    "speech_metrics": asdict(speech_metrics),
                    "language_metrics": asdict(language_metrics),
                    "metadata": {
                        "total_audio_bytes": session.total_audio_bytes,
                        "chunk_count": session.chunk_count
                    }
                }
                
                await session_store.save_session(session.session_id, session_data)
                logger.info(f"Session {session.session_id} finalized and persisted")
                
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except Exception as e:
            logger.error(f"Session finalization failed: {e}")
            import traceback
            logger.error(traceback.format_exc())


# Module-level instance
streaming_handler = SpeechStreamingHandler()