"""
Speech Streaming - Enhanced with per-question tracking
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

from fastapi import WebSocket, WebSocketDisconnect
import numpy as np

from services.speech_service.transcriber import transcriber
from services.speech_service.analyzer import speech_analyzer, analyze_speech, analyze_language
from services.speech_service.session_store import session_store

logger = logging.getLogger(__name__)


@dataclass
class QuestionSegment:
    """Tracks a single question-answer segment within a session."""
    question_id: str
    question_text: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    audio_chunks: List[bytes] = field(default_factory=list)
    partial_transcripts: List[str] = field(default_factory=list)
    final_transcript: str = ""
    transcription_result: Dict[str, Any] = field(default_factory=dict)
    chunk_count: int = 0


@dataclass
class StreamingSession:
    """Tracks state for a streaming transcription session with multiple questions."""
    session_id: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    current_question: Optional[QuestionSegment] = None
    completed_questions: List[QuestionSegment] = field(default_factory=list)
    total_audio_bytes: int = 0
    total_chunk_count: int = 0
    is_active: bool = True
    last_activity: datetime = field(default_factory=datetime.utcnow)


class SpeechStreamingHandler:
    """
    Handle real-time speech streaming via WebSocket with per-question tracking.
    """
    
    def __init__(self):
        self.active_sessions: Dict[str, StreamingSession] = {}
        # Disable partial transcription - only transcribe at end
        # This avoids issues with small audio chunks that can't be properly parsed
        self.enable_partial_transcription = False
        self.transcription_buffer_size = 20  # Only used if partial enabled
    
    async def _safe_send(self, websocket: WebSocket, data: dict) -> bool:
        """Safely send JSON data over WebSocket, handling closed connections."""
        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.debug(f"Failed to send WebSocket message: {e}")
            return False
        
    async def handle_connection(self, websocket: WebSocket, session_id: str):
        """Main WebSocket handler for speech streaming."""
        await websocket.accept()
        logger.info(f"WebSocket connected for session: {session_id}")
        
        # Initialize session
        session = StreamingSession(session_id=session_id)
        self.active_sessions[session_id] = session
        
        # Send acknowledgment
        await self._safe_send(websocket, {
            "type": "connected",
            "session_id": session_id,
            "message": "Ready to receive audio and question markers"
        })
        
        try:
            while True:
                data = await websocket.receive()
                
                if "bytes" in data:
                    await self._process_audio_chunk(websocket, session, data["bytes"])
                elif "text" in data:
                    await self._handle_control_message(websocket, session, data["text"])
                    
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session: {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error for session {session_id}: {e}")
            # Try to send error, but don't fail if connection is closed
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
            except:
                pass  # Connection already closed
        finally:
            # Finalize session
            await self._finalize_session(session)
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    async def _process_audio_chunk(
        self,
        websocket: WebSocket,
        session: StreamingSession,
        audio_bytes: bytes
    ):
        """Process incoming audio chunk."""
        if not session.current_question:
            logger.warning("Received audio but no question is active. Use 'start_question' first.")
            await self._safe_send(websocket, {
                "type": "warning",
                "message": "No active question. Use start_question control message first."
            })
            return
        
        # Add to current question
        session.current_question.audio_chunks.append(audio_bytes)
        session.current_question.chunk_count += 1
        session.total_audio_bytes += len(audio_bytes)
        session.total_chunk_count += 1
        session.last_activity = datetime.utcnow()
        
        # Only process partial transcription if enabled
        # (Disabled by default to avoid issues with small WebM chunks)
        if self.enable_partial_transcription:
            if session.current_question.chunk_count % self.transcription_buffer_size == 0:
                await self._run_incremental_transcription(websocket, session)
    
    async def _run_incremental_transcription(
        self,
        websocket: WebSocket,
        session: StreamingSession
    ):
        """Run transcription on buffered audio and emit partial result."""
        if not session.current_question or not session.current_question.audio_chunks:
            return
        
        try:
            # Combine recent chunks
            recent_chunks = session.current_question.audio_chunks[-self.transcription_buffer_size:]
            combined_audio = b''.join(recent_chunks)
            
            # Save to temp file for Whisper
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
                tmp.write(combined_audio)
                tmp_path = tmp.name
            
            try:
                # Run transcription
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: transcriber.transcribe(tmp_path, word_timestamps=False)
                )
                
                partial_text = result.get("text", "").strip()
                
                if partial_text:
                    # Store partial transcript
                    session.current_question.partial_transcripts.append(partial_text)
                    
                    # Send to client
                    await self._safe_send(websocket, {
                        "type": "partial_transcript",
                        "partial_transcript": partial_text,
                        "question_id": session.current_question.question_id,
                        "is_final": False,
                        "chunk_index": session.current_question.chunk_count
                    })
                    
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
                    
        except Exception as e:
            logger.error(f"Incremental transcription failed: {e}")
    
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
            
            if msg_type == "start_question":
                await self._start_question(websocket, session, data)
                
            elif msg_type == "end_question":
                await self._end_question(websocket, session)
                
            elif msg_type == "end_session":
                session.is_active = False
                await self._finalize_session(session)
                await self._safe_send(websocket, {
                    "type": "session_ended",
                    "session_id": session.session_id,
                    "total_questions": len(session.completed_questions)
                })
                
            elif msg_type == "ping":
                await self._safe_send(websocket, {"type": "pong"})
                
            elif msg_type == "get_status":
                await self._safe_send(websocket, {
                    "type": "status",
                    "session_id": session.session_id,
                    "total_chunks": session.total_chunk_count,
                    "total_bytes": session.total_audio_bytes,
                    "active_question": session.current_question.question_id if session.current_question else None,
                    "completed_questions": len(session.completed_questions)
                })
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid control message: {message}")
    
    async def _start_question(
        self,
        websocket: WebSocket,
        session: StreamingSession,
        data: Dict
    ):
        """Start a new question segment."""
        # End current question if exists
        if session.current_question:
            await self._end_question(websocket, session, silent=True)
        
        question_id = data.get("question_id", f"q_{len(session.completed_questions) + 1}")
        question_text = data.get("question_text", "")
        
        session.current_question = QuestionSegment(
            question_id=question_id,
            question_text=question_text,
            started_at=datetime.utcnow()
        )
        
        logger.info(f"Started question {question_id} in session {session.session_id}")
        
        await self._safe_send(websocket, {
            "type": "question_started",
            "question_id": question_id,
            "message": f"Ready to record answer for question {question_id}"
        })
    
    async def _end_question(
        self,
        websocket: WebSocket,
        session: StreamingSession,
        silent: bool = False
    ):
        """End current question and finalize its transcript."""
        if not session.current_question:
            return
        
        question = session.current_question
        question.ended_at = datetime.utcnow()
        
        logger.info(f"Ending question {question.question_id} in session {session.session_id}")
        logger.info(f"Audio chunks collected: {question.chunk_count}, total bytes: {sum(len(c) for c in question.audio_chunks)}")
        
        # Finalize transcript for this question
        if question.audio_chunks:
            try:
                # Combine all audio for this question
                full_audio = b''.join(question.audio_chunks)
                
                # Convert WebM to WAV using pydub for reliable transcription
                from pydub import AudioSegment
                import io
                
                logger.info(f"Converting {len(full_audio)} bytes of WebM to WAV...")
                
                # Load WebM data
                audio_segment = AudioSegment.from_file(
                    io.BytesIO(full_audio),
                    format="webm"
                )
                
                # Normalize audio to improve transcription quality
                audio_segment = audio_segment.normalize()
                
                # Convert to mono 16kHz (Whisper's native format)
                audio_segment = audio_segment.set_channels(1)
                audio_segment = audio_segment.set_frame_rate(16000)
                
                logger.info(f"Audio properties: {len(audio_segment)}ms, {audio_segment.frame_rate}Hz, {audio_segment.channels} channel(s)")
                
                # Export as WAV
                wav_buffer = io.BytesIO()
                audio_segment.export(wav_buffer, format="wav")
                wav_buffer.seek(0)
                
                # Save WAV to temp file for Whisper
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(wav_buffer.read())
                    tmp_path = tmp.name
                
                logger.info(f"WAV file created: {tmp_path}, size: {os.path.getsize(tmp_path)} bytes")
                
                try:
                    # Full transcription with language hint
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: transcriber.transcribe(
                            tmp_path,
                            language="en",
                            word_timestamps=True
                        )
                    )
                    
                    question.final_transcript = result.get("text", "").strip()
                    question.transcription_result = result
                    
                    logger.info(f"Transcription complete: {len(question.final_transcript)} chars, confidence: {result.get('confidence', 0)}")
                    
                    if not silent:
                        await self._safe_send(websocket, {
                            "type": "question_ended",
                            "question_id": question.question_id,
                            "final_transcript": question.final_transcript,
                            "word_count": len(question.final_transcript.split())
                        })
                    
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                        
            except Exception as e:
                logger.error(f"Failed to finalize question {question.question_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Store empty transcript on failure
                question.final_transcript = ""
                question.transcription_result = {
                    "text": "",
                    "duration_seconds": 0,
                    "confidence": 0,
                    "word_count": 0,
                    "segments": []
                }
        
        # Move to completed
        session.completed_questions.append(question)
        session.current_question = None
    
    async def _finalize_session(self, session: StreamingSession):
        """Finalize entire session with all questions."""
        logger.info(f"Finalizing session: {session.session_id}")
        
        # End current question if still active
        if session.current_question:
            session.current_question.ended_at = datetime.utcnow()
            
            # Quick finalize using pydub
            if session.current_question.audio_chunks:
                full_audio = b''.join(session.current_question.audio_chunks)
                try:
                    from pydub import AudioSegment
                    import io
                    
                    # Convert WebM to WAV
                    audio_segment = AudioSegment.from_file(
                        io.BytesIO(full_audio),
                        format="webm"
                    )
                    
                    wav_buffer = io.BytesIO()
                    audio_segment.export(wav_buffer, format="wav")
                    wav_buffer.seek(0)
                    
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                        tmp.write(wav_buffer.read())
                        tmp_path = tmp.name
                    
                    try:
                        result = await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: transcriber.transcribe(tmp_path, word_timestamps=True)
                        )
                        session.current_question.final_transcript = result.get("text", "")
                        session.current_question.transcription_result = result
                    finally:
                        os.remove(tmp_path)
                except Exception as e:
                    logger.error(f"Failed to finalize last question: {e}")
                    session.current_question.final_transcript = ""
                    session.current_question.transcription_result = {
                        "text": "",
                        "duration_seconds": 0,
                        "confidence": 0,
                        "word_count": 0,
                        "segments": []
                    }
            
            session.completed_questions.append(session.current_question)
        
        # Build session data with per-question breakdown
        questions_data = []
        
        for q in session.completed_questions:
            # Use stored transcription result or create empty one
            transcription = q.transcription_result or {
                "text": q.final_transcript,
                "duration_seconds": (q.ended_at - q.started_at).total_seconds() if q.ended_at else 0,
                "word_count": len(q.final_transcript.split()),
                "confidence": 0.0,
                "segments": []
            }
            
            # Analyze this question's answer
            try:
                speech_metrics = analyze_speech(transcription)
                language_metrics = analyze_language(q.final_transcript)
                
                questions_data.append({
                    "question_id": q.question_id,
                    "question_text": q.question_text,
                    "started_at": q.started_at.isoformat(),
                    "ended_at": q.ended_at.isoformat() if q.ended_at else None,
                    "transcript": q.final_transcript,
                    "speech_metrics": asdict(speech_metrics),
                    "language_metrics": asdict(language_metrics),
                    "chunk_count": q.chunk_count
                })
            except Exception as e:
                logger.error(f"Failed to analyze question {q.question_id}: {e}")
                # Add with empty metrics
                questions_data.append({
                    "question_id": q.question_id,
                    "question_text": q.question_text,
                    "started_at": q.started_at.isoformat(),
                    "ended_at": q.ended_at.isoformat() if q.ended_at else None,
                    "transcript": q.final_transcript,
                    "speech_metrics": None,
                    "language_metrics": None,
                    "chunk_count": q.chunk_count
                })
        
        # Aggregate full transcript
        full_transcript = " ".join(q.final_transcript for q in session.completed_questions)
        
        # Store in session store
        session_data = {
            "session_id": session.session_id,
            "started_at": session.started_at.isoformat(),
            "ended_at": datetime.utcnow().isoformat(),
            "questions": questions_data,
            "full_transcript": full_transcript,
            "total_questions": len(session.completed_questions),
            "metadata": {
                "total_audio_bytes": session.total_audio_bytes,
                "total_chunks": session.total_chunk_count
            }
        }
        
        await session_store.save_session(session.session_id, session_data)
        logger.info(f"Session {session.session_id} finalized with {len(questions_data)} questions")


# Module-level instance
streaming_handler = SpeechStreamingHandler()