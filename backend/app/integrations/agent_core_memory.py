"""Agent core memory integration for conversation context."""

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import uuid

from app.config import settings


@dataclass
class MemoryEvent:
    """Memory event structure."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    session_id: str
    event_id: str = None

    def __post_init__(self):
        """Generate event_id if not provided."""
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


class AgentCoreMemory:
    """Agent core memory service for SHORT_TERM conversation context."""

    def __init__(self):
        """Initialize agent core memory."""
        self.memory_type = "SHORT_TERM"
        self.retention_days = settings.agent_memory_retention_days
        self.ttl_seconds = self.retention_days * 86400  # Convert days to seconds
        # In-memory storage for session events (in production, this would be DynamoDB)
        self._memory_store: Dict[str, List[MemoryEvent]] = {}

    async def initialize_memory(
        self, session_id: str, user_id: str, recent_events: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Initialize memory for a session.

        Args:
            session_id: Unique session identifier
            user_id: User identifier
            recent_events: Optional list of recent events to load from DynamoDB

        Returns:
            Memory initialization result
        """
        if session_id not in self._memory_store:
            self._memory_store[session_id] = []

        # Load recent events if provided (from DynamoDB)
        if recent_events:
            for event_data in recent_events:
                event = MemoryEvent(
                    role=event_data.get("role"),
                    content=event_data.get("content"),
                    timestamp=event_data.get("timestamp"),
                    session_id=session_id,
                    event_id=event_data.get("event_id"),
                )
                self._memory_store[session_id].append(event)

        return {
            "status": "initialized",
            "session_id": session_id,
            "user_id": user_id,
            "memory_type": self.memory_type,
            "event_count": len(self._memory_store[session_id]),
            "retention_days": self.retention_days,
        }

    async def log_message(self, session_id: str, role: str, content: str, timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Log a message to memory.

        Args:
            session_id: Session identifier
            role: Message role ("user" or "assistant")
            content: Message content
            timestamp: Optional timestamp (defaults to current time)

        Returns:
            Logged event details
        """
        if role not in ("user", "assistant"):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'.")

        if not content or not isinstance(content, str):
            raise ValueError("Content must be a non-empty string.")

        if session_id not in self._memory_store:
            self._memory_store[session_id] = []

        if timestamp is None:
            timestamp = time.time()

        event = MemoryEvent(
            role=role,
            content=content,
            timestamp=timestamp,
            session_id=session_id,
        )

        self._memory_store[session_id].append(event)

        return {
            "status": "logged",
            "event_id": event.event_id,
            "role": role,
            "timestamp": timestamp,
            "session_id": session_id,
        }

    async def get_memory_context(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve current memory context for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of memory events sorted by timestamp
        """
        if session_id not in self._memory_store:
            return []

        events = self._memory_store[session_id]
        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        return [event.to_dict() for event in sorted_events]

    async def clear_old_memory(self, session_id: str) -> Dict[str, Any]:
        """
        Cleanup old memory entries for a session.

        Args:
            session_id: Session identifier

        Returns:
            Cleanup result
        """
        if session_id not in self._memory_store:
            return {"status": "cleared", "session_id": session_id, "removed_count": 0}

        current_time = time.time()
        expiry_time = current_time - self.ttl_seconds
        events = self._memory_store[session_id]

        # Filter out expired events
        before_count = len(events)
        self._memory_store[session_id] = [event for event in events if event.timestamp > expiry_time]
        after_count = len(self._memory_store[session_id])
        removed_count = before_count - after_count

        return {
            "status": "cleared",
            "session_id": session_id,
            "removed_count": removed_count,
            "remaining_count": after_count,
        }

    async def get_memory_events(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get memory events for a session with optional limit.

        Args:
            session_id: Session identifier
            limit: Optional limit on number of events to return

        Returns:
            List of memory events
        """
        events = await self.get_memory_context(session_id)

        if limit:
            return events[-limit:]  # Return last N events

        return events

    async def validate_event_structure(self, event: Dict[str, Any]) -> bool:
        """
        Validate memory event structure.

        Args:
            event: Event dictionary to validate

        Returns:
            True if valid, raises ValueError otherwise
        """
        required_fields = {"role", "content", "timestamp", "session_id"}

        if not isinstance(event, dict):
            raise ValueError("Event must be a dictionary")

        missing_fields = required_fields - set(event.keys())
        if missing_fields:
            raise ValueError(f"Event missing required fields: {missing_fields}")

        # Validate field types and values
        role = event.get("role")
        if role not in ("user", "assistant"):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'.")

        content = event.get("content")
        if not isinstance(content, str) or not content:
            raise ValueError("Content must be a non-empty string")

        timestamp = event.get("timestamp")
        if not isinstance(timestamp, (int, float)):
            raise ValueError("Timestamp must be a number")

        session_id = event.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError("Session ID must be a non-empty string")

        return True

    async def delete_session_memory(self, session_id: str) -> Dict[str, Any]:
        """
        Delete all memory for a session.

        Args:
            session_id: Session identifier

        Returns:
            Deletion result
        """
        if session_id in self._memory_store:
            count = len(self._memory_store[session_id])
            del self._memory_store[session_id]
            return {
                "status": "deleted",
                "session_id": session_id,
                "deleted_count": count,
            }

        return {
            "status": "deleted",
            "session_id": session_id,
            "deleted_count": 0,
        }

    async def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Get summary statistics for a session's memory.

        Args:
            session_id: Session identifier

        Returns:
            Memory summary
        """
        if session_id not in self._memory_store:
            return {
                "session_id": session_id,
                "total_events": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "retention_days": self.retention_days,
                "memory_type": self.memory_type,
            }

        events = self._memory_store[session_id]
        user_count = sum(1 for e in events if e.role == "user")
        assistant_count = sum(1 for e in events if e.role == "assistant")

        return {
            "session_id": session_id,
            "total_events": len(events),
            "user_messages": user_count,
            "assistant_messages": assistant_count,
            "retention_days": self.retention_days,
            "memory_type": self.memory_type,
        }


def get_agent_memory() -> AgentCoreMemory:
    """Create a fresh AgentCoreMemory instance for per-request isolation.

    This is used with FastAPI Depends to ensure each request gets its own
    memory instance, preventing state leakage between concurrent requests.

    Returns:
        AgentCoreMemory: Fresh instance for this request
    """
    return AgentCoreMemory()
