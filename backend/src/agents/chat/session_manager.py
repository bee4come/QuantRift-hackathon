"""
Session Manager for multi-turn conversations

Manages conversation state, context, and session lifecycle.
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChatSession:
    """
    Chat session state for multi-turn conversations

    Tracks:
    - Conversation history
    - Context data (e.g., recent match list for later reference)
    - Session metadata (creation time, last activity)
    """

    session_id: str
    puuid: str
    game_name: str
    tag_line: str
    region: str = "na1"

    # Conversation history
    history: List[Dict[str, str]] = field(default_factory=list)

    # Context storage for multi-turn references
    context: Dict[str, Any] = field(default_factory=dict)

    # Session metadata
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str):
        """
        Add message to conversation history

        Args:
            role: "user" or "assistant"
            content: Message content
        """
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        self.last_activity = time.time()

    def get_history(self, last_n: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Get conversation history

        Args:
            last_n: If specified, return only last N messages

        Returns:
            List of message dicts with role, content, timestamp
        """
        if last_n:
            return self.history[-last_n:]
        return self.history

    def set_context(self, key: str, value: Any):
        """
        Store context data for later reference

        Examples:
        - session.set_context("recent_matches", match_list)
        - session.set_context("last_champion_id", 157)

        Args:
            key: Context key
            value: Any JSON-serializable value
        """
        self.context[key] = value
        self.last_activity = time.time()

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Retrieve context data

        Args:
            key: Context key
            default: Default value if key not found

        Returns:
            Context value or default
        """
        return self.context.get(key, default)

    def clear_context(self, key: Optional[str] = None):
        """
        Clear context data

        Args:
            key: If specified, clear only this key. Otherwise clear all context.
        """
        if key:
            self.context.pop(key, None)
        else:
            self.context.clear()
        self.last_activity = time.time()

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """
        Check if session has expired due to inactivity

        Args:
            timeout_minutes: Expiration timeout in minutes (default: 30)

        Returns:
            True if session expired, False otherwise
        """
        elapsed_seconds = time.time() - self.last_activity
        return elapsed_seconds > (timeout_minutes * 60)

    def get_age_minutes(self) -> float:
        """Get session age in minutes"""
        elapsed_seconds = time.time() - self.created_at
        return elapsed_seconds / 60

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize session to dictionary

        Returns:
            Session data as dict
        """
        return {
            "session_id": self.session_id,
            "puuid": self.puuid,
            "game_name": self.game_name,
            "tag_line": self.tag_line,
            "region": self.region,
            "history": self.history,
            "context": self.context,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "age_minutes": self.get_age_minutes()
        }


class SessionManager:
    """
    Global session manager for all chat sessions

    Responsibilities:
    - Create and retrieve sessions
    - Session lifecycle management
    - Automatic cleanup of expired sessions
    """

    def __init__(self):
        """Initialize session manager"""
        self._sessions: Dict[str, ChatSession] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup every 5 minutes

    def get_or_create_session(
        self,
        session_id: str,
        puuid: str,
        game_name: str,
        tag_line: str,
        region: str = "na1"
    ) -> ChatSession:
        """
        Get existing session or create new one

        Args:
            session_id: Unique session identifier
            puuid: Player PUUID
            game_name: Player game name
            tag_line: Player tag line
            region: Player region (default: na1)

        Returns:
            ChatSession object
        """
        # Auto-cleanup if needed
        self._auto_cleanup()

        # Check if session exists and is not expired
        if session_id in self._sessions:
            session = self._sessions[session_id]
            if not session.is_expired():
                # Update last activity
                session.last_activity = time.time()
                return session
            else:
                # Session expired, remove it
                print(f"🗑️ Session {session_id[:8]}... expired, creating new one")
                del self._sessions[session_id]

        # Create new session
        session = ChatSession(
            session_id=session_id,
            puuid=puuid,
            game_name=game_name,
            tag_line=tag_line,
            region=region
        )
        self._sessions[session_id] = session

        print(f"✨ New chat session created: {session_id[:8]}... for {game_name}#{tag_line}")

        return session

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Get existing session by ID

        Args:
            session_id: Session identifier

        Returns:
            ChatSession or None if not found/expired
        """
        session = self._sessions.get(session_id)
        if session and not session.is_expired():
            return session
        return None

    def delete_session(self, session_id: str) -> bool:
        """
        Delete session by ID

        Args:
            session_id: Session identifier

        Returns:
            True if session was deleted, False if not found
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            print(f"🗑️ Session {session_id[:8]}... deleted")
            return True
        return False

    def cleanup_expired_sessions(self, timeout_minutes: int = 30) -> int:
        """
        Remove all expired sessions

        Args:
            timeout_minutes: Expiration timeout in minutes

        Returns:
            Number of sessions removed
        """
        expired_ids = [
            sid for sid, session in self._sessions.items()
            if session.is_expired(timeout_minutes)
        ]

        for sid in expired_ids:
            del self._sessions[sid]

        if expired_ids:
            print(f"🗑️ Cleaned up {len(expired_ids)} expired sessions")

        self._last_cleanup = time.time()
        return len(expired_ids)

    def _auto_cleanup(self):
        """Automatically cleanup expired sessions if interval passed"""
        elapsed = time.time() - self._last_cleanup
        if elapsed > self._cleanup_interval:
            self.cleanup_expired_sessions()

    def get_active_session_count(self) -> int:
        """Get count of active (non-expired) sessions"""
        return len([
            s for s in self._sessions.values()
            if not s.is_expired()
        ])

    def get_all_sessions(self) -> List[ChatSession]:
        """Get all active sessions"""
        return [
            s for s in self._sessions.values()
            if not s.is_expired()
        ]

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about all sessions

        Returns:
            Dict with total sessions, active sessions, average age, etc.
        """
        active_sessions = self.get_all_sessions()

        if not active_sessions:
            return {
                "total_sessions": 0,
                "active_sessions": 0,
                "avg_age_minutes": 0,
                "avg_messages_per_session": 0
            }

        total_messages = sum(len(s.history) for s in active_sessions)
        total_age = sum(s.get_age_minutes() for s in active_sessions)

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len(active_sessions),
            "avg_age_minutes": total_age / len(active_sessions),
            "avg_messages_per_session": total_messages / len(active_sessions),
            "total_messages": total_messages
        }


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get global session manager instance (singleton)

    Returns:
        SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
