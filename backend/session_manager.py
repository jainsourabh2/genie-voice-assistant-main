# Session state management
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from logger import get_logger

logger = get_logger("session_manager")


@dataclass
class TranscriptEntry:
    """Single transcript entry"""
    role: str  # "user" or "model"
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_final: bool = False
    ttfb_ms: Optional[float] = None


@dataclass
class ToolCallEntry:
    """Single tool call entry"""
    id: str
    name: str
    args: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    response: Optional[Any] = None
    response_timestamp: Optional[datetime] = None
    is_processing: bool = True


@dataclass
class Session:
    """Voice chat session state"""
    session_id: str
    created_at: datetime = field(default_factory=datetime.now)
    transcripts: List[TranscriptEntry] = field(default_factory=list)
    tool_calls: List[ToolCallEntry] = field(default_factory=list)
    is_active: bool = True
    last_audio_time: Optional[float] = None
    config: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """Manages voice chat sessions"""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}
        logger.info("SessionManager initialized")

    def create_session(self, config: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new session"""
        session_id = str(uuid.uuid4())[:8]  # Short ID for readability
        session = Session(
            session_id=session_id,
            config=config or {}
        )
        self._sessions[session_id] = session
        logger.info(f"Created session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self._sessions.get(session_id)

    def end_session(self, session_id: str) -> bool:
        """End a session"""
        session = self._sessions.get(session_id)
        if session:
            session.is_active = False
            logger.info(f"Ended session: {session_id}")
            return True
        return False

    def add_transcript(
        self,
        session_id: str,
        role: str,
        text: str,
        is_final: bool = False,
        ttfb_ms: Optional[float] = None
    ) -> Optional[TranscriptEntry]:
        """Add transcript entry to session"""
        session = self._sessions.get(session_id)
        if not session:
            logger.warning(f"Session not found: {session_id}")
            return None

        entry = TranscriptEntry(
            role=role,
            text=text,
            is_final=is_final,
            ttfb_ms=ttfb_ms
        )
        session.transcripts.append(entry)
        logger.debug(f"Added transcript [{role}]: {text[:50]}...")
        return entry

    def add_tool_call(
        self,
        session_id: str,
        tool_id: str,
        name: str,
        args: Dict[str, Any]
    ) -> Optional[ToolCallEntry]:
        """Add tool call to session"""
        session = self._sessions.get(session_id)
        if not session:
            return None

        entry = ToolCallEntry(
            id=tool_id,
            name=name,
            args=args
        )
        session.tool_calls.append(entry)
        logger.info(f"Added tool call: {name}")
        return entry

    def update_tool_response(
        self,
        session_id: str,
        tool_id: str,
        response: Any
    ) -> bool:
        """Update tool call with response"""
        session = self._sessions.get(session_id)
        if not session:
            return False

        for tc in session.tool_calls:
            if tc.id == tool_id:
                tc.response = response
                tc.response_timestamp = datetime.now()
                tc.is_processing = False
                logger.info(f"Updated tool response for: {tc.name}")
                return True
        return False

    def update_last_audio_time(self, session_id: str, timestamp: float) -> None:
        """Update last audio receive time for activity detection"""
        session = self._sessions.get(session_id)
        if session:
            session.last_audio_time = timestamp

    def get_last_audio_time(self, session_id: str) -> Optional[float]:
        """Get last audio receive time"""
        session = self._sessions.get(session_id)
        return session.last_audio_time if session else None

    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session statistics"""
        session = self._sessions.get(session_id)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "created_at": session.created_at.isoformat(),
            "is_active": session.is_active,
            "transcript_count": len(session.transcripts),
            "tool_call_count": len(session.tool_calls),
            "config": session.config
        }

    def cleanup_inactive_sessions(self, max_age_hours: int = 24) -> int:
        """Remove old inactive sessions"""
        now = datetime.now()
        to_remove = []

        for sid, session in self._sessions.items():
            if not session.is_active:
                age = (now - session.created_at).total_seconds() / 3600
                if age > max_age_hours:
                    to_remove.append(sid)

        for sid in to_remove:
            del self._sessions[sid]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive sessions")

        return len(to_remove)
