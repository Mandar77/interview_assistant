"""
Session Store - Persist session data for speech analysis
Location: backend/services/speech_service/session_store.py

Note: This implementation uses in-memory storage with file backup.
For production, replace with PostgreSQL/Supabase integration.
"""

import json
import logging
import os
import asyncio
from typing import Dict, Optional, List, Any
from datetime import datetime
from pathlib import Path
import aiofiles

logger = logging.getLogger(__name__)

# Storage directory for session data
STORAGE_DIR = Path("data/sessions")


class SessionStore:
    """
    Store and retrieve session data for speech analysis.
    
    Provides:
    - In-memory cache for fast access
    - File-based persistence for durability
    - Session-scoped data aggregation
    
    For production: Replace with PostgreSQL/Supabase
    """
    
    def __init__(self, storage_dir: Path = STORAGE_DIR):
        self.storage_dir = storage_dir
        self.cache: Dict[str, Dict] = {}
        self._ensure_storage_dir()
    
    def _ensure_storage_dir(self):
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_path(self, session_id: str) -> Path:
        """Get file path for a session."""
        return self.storage_dir / f"{session_id}.json"
    
    async def save_session(self, session_id: str, data: Dict[str, Any]) -> bool:
        """
        Save session data.
        
        Args:
            session_id: Unique session identifier
            data: Session data to persist
            
        Returns:
            True if successful
        """
        try:
            # Add metadata
            data["_updated_at"] = datetime.utcnow().isoformat()
            
            # Update cache
            self.cache[session_id] = data
            
            # Persist to file
            file_path = self._get_session_path(session_id)
            async with aiofiles.open(file_path, 'w') as f:
                await f.write(json.dumps(data, indent=2, default=str))
            
            logger.info(f"Session {session_id} saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve session data.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data or None if not found
        """
        # Check cache first
        if session_id in self.cache:
            return self.cache[session_id]
        
        # Load from file
        file_path = self._get_session_path(session_id)
        if not file_path.exists():
            return None
        
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                data = json.loads(content)
                self.cache[session_id] = data
                return data
                
        except Exception as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return None
    
    async def update_session(
        self,
        session_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update specific fields in a session.
        
        Args:
            session_id: Session identifier
            updates: Fields to update
            
        Returns:
            True if successful
        """
        existing = await self.get_session(session_id)
        if not existing:
            existing = {"session_id": session_id}
        
        # Merge updates
        existing.update(updates)
        
        return await self.save_session(session_id, existing)
    
    async def append_to_session(
        self,
        session_id: str,
        field: str,
        value: Any
    ) -> bool:
        """
        Append a value to a list field in session.
        
        Args:
            session_id: Session identifier
            field: Field name (must be a list)
            value: Value to append
            
        Returns:
            True if successful
        """
        existing = await self.get_session(session_id) or {"session_id": session_id}
        
        if field not in existing:
            existing[field] = []
        
        if not isinstance(existing[field], list):
            logger.error(f"Field {field} is not a list")
            return False
        
        existing[field].append(value)
        return await self.save_session(session_id, existing)
    
    async def get_session_transcript(self, session_id: str) -> Optional[str]:
        """Get full transcript for a session."""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        transcription = session.get("transcription", {})
        return transcription.get("full_text", "")
    
    async def get_session_metrics(self, session_id: str) -> Optional[Dict]:
        """Get speech and language metrics for a session."""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        return {
            "speech_metrics": session.get("speech_metrics"),
            "language_metrics": session.get("language_metrics")
        }
    
    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all sessions with basic info.
        
        Args:
            limit: Maximum sessions to return
            offset: Pagination offset
            
        Returns:
            List of session summaries
        """
        sessions = []
        
        try:
            files = sorted(
                self.storage_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            for file_path in files[offset:offset + limit]:
                try:
                    async with aiofiles.open(file_path, 'r') as f:
                        content = await f.read()
                        data = json.loads(content)
                        sessions.append({
                            "session_id": data.get("session_id"),
                            "started_at": data.get("started_at"),
                            "ended_at": data.get("ended_at"),
                            "word_count": data.get("transcription", {}).get("word_count", 0),
                            "duration_seconds": data.get("transcription", {}).get("duration_seconds", 0)
                        })
                except Exception as e:
                    logger.warning(f"Failed to read session file {file_path}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
        
        return sessions
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        try:
            # Remove from cache
            if session_id in self.cache:
                del self.cache[session_id]
            
            # Remove file
            file_path = self._get_session_path(session_id)
            if file_path.exists():
                os.remove(file_path)
            
            logger.info(f"Session {session_id} deleted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def get_session_for_evaluation(self, session_id: str) -> Optional[Dict]:
        """
        Get session data formatted for the evaluation service.
        
        Returns data structure expected by /api/v1/evaluation/evaluate
        """
        session = await self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session_id,
            "transcript": session.get("transcription", {}).get("full_text", ""),
            "speech_metrics": session.get("speech_metrics"),
            "language_metrics": session.get("language_metrics"),
            "duration_seconds": session.get("transcription", {}).get("duration_seconds", 0),
            "segments": session.get("transcription", {}).get("segments", [])
        }


# Module-level instance
session_store = SessionStore()


# Convenience functions
async def save_session(session_id: str, data: Dict) -> bool:
    return await session_store.save_session(session_id, data)


async def get_session(session_id: str) -> Optional[Dict]:
    return await session_store.get_session(session_id)


async def get_session_for_evaluation(session_id: str) -> Optional[Dict]:
    return await session_store.get_session_for_evaluation(session_id)