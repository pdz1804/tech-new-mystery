"""Chat repository for DynamoDB operations."""

import asyncio
import uuid
import time
from typing import Optional, List, Dict, Any
from pynamodb.exceptions import DoesNotExist

from app.models.chat import ConversationSessionModel, ConversationMessageModel
from app.config import settings


class ChatRepository:
    """Repository for chat operations."""

    def __init__(self):
        """Initialize chat repository."""
        self.session_ttl_days = 90
        self.ttl_seconds = self.session_ttl_days * 86400

    async def create_session(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new chat session.

        Args:
            user_id: User ID
            title: Session title
            description: Optional session description

        Returns:
            Created session dict
        """
        session_id = str(uuid.uuid4())
        now = time.time()
        expires_at = now + self.ttl_seconds

        def _save_session():
            session = ConversationSessionModel(
                user_id=user_id,
                session_id=session_id,
                title=title,
                description=description,
                created_at=now,
                updated_at=now,
                last_message_at=now,
                message_count=0,
                is_active=True,
                expires_at=expires_at,
            )
            session.save()

        await asyncio.to_thread(_save_session)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "message_count": 0,
            "created_at": now,
            "updated_at": now,
            "last_message_at": now,
        }

    async def get_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID (verify ownership).

        Args:
            user_id: User ID (to verify ownership)
            session_id: Session ID

        Returns:
            Session dict or None if not found
        """
        def _get_session():
            try:
                return ConversationSessionModel.get(user_id, session_id)
            except DoesNotExist:
                return None

        session = await asyncio.to_thread(_get_session)
        if not session:
            return None

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "title": session.title,
            "description": session.description,
            "message_count": session.message_count,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "last_message_at": session.last_message_at,
        }

    async def list_sessions(
        self,
        user_id: str,
        limit: int = 20,
        last_key: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """List user's sessions ordered by recency (most recent first).

        Args:
            user_id: User ID
            limit: Max items per page
            last_key: Pagination key for next page

        Returns:
            Tuple of (sessions list, next_page_key or None)
        """
        def _query_sessions():
            try:
                # Query using the user_last_message_index (sorted by last_message_at DESC)
                query_iter = ConversationSessionModel.user_last_message_index.query(
                    user_id,
                    scan_index_forward=False,  # Descending order (most recent first)
                    limit=limit,
                )
                return list(query_iter)
            except Exception:
                # If index query fails, fall back to main table query
                try:
                    return list(ConversationSessionModel.query(user_id, limit=limit))
                except Exception:
                    return []

        sessions_list = await asyncio.to_thread(_query_sessions)

        sessions = []
        for session in sessions_list:
            sessions.append(
                {
                    "session_id": session.session_id,
                    "user_id": session.user_id,
                    "title": session.title,
                    "description": session.description,
                    "message_count": session.message_count,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "last_message_at": session.last_message_at,
                }
            )

        # Sort by last_message_at descending (for fallback query)
        sessions.sort(key=lambda x: x["last_message_at"], reverse=True)
        return sessions[:limit], None

    async def create_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        token_count: Optional[int] = None,
        model_used: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new message in a session.

        Args:
            session_id: Session ID
            user_id: User ID
            role: "user" or "assistant"
            content: Message content
            token_count: Optional token count
            model_used: Optional model identifier

        Returns:
            Created message dict
        """
        message_id = str(uuid.uuid4())
        now = time.time()
        expires_at = now + self.ttl_seconds

        def _save_message():
            message = ConversationMessageModel(
                session_id=session_id,
                message_id=message_id,
                user_id=user_id,
                role=role,
                content=content,
                timestamp=now,
                token_count=token_count,
                model_used=model_used,
                expires_at=expires_at,
            )
            message.save()

            # Update session's last_message_at and increment message_count
            try:
                session = ConversationSessionModel.get(user_id, session_id)
                session.last_message_at = now
                session.updated_at = now
                session.message_count = session.message_count + 1
                session.save()
            except DoesNotExist:
                pass

        await asyncio.to_thread(_save_message)

        return {
            "message_id": message_id,
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": now,
            "token_count": token_count,
            "model_used": model_used,
        }

    async def get_messages(
        self,
        session_id: str,
        limit: int = 20,
        last_key: Optional[str] = None,
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """Get messages from a session with pagination.

        Args:
            session_id: Session ID
            limit: Max items per page
            last_key: Pagination key for next page

        Returns:
            Tuple of (messages list, next_page_key or None)
        """
        def _query_messages():
            try:
                # Query using session_timestamp_index (sorted by timestamp ASC for chronological order)
                query_iter = ConversationMessageModel.session_timestamp_index.query(
                    session_id,
                    scan_index_forward=True,  # Ascending order (chronological)
                    limit=limit,
                )
                return list(query_iter)
            except Exception:
                # Fall back to main table query
                try:
                    return list(ConversationMessageModel.query(session_id, limit=limit))
                except Exception:
                    return []

        messages_list = await asyncio.to_thread(_query_messages)

        messages = []
        for message in messages_list:
            messages.append(
                {
                    "message_id": message.message_id,
                    "session_id": message.session_id,
                    "user_id": message.user_id,
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp,
                    "token_count": message.token_count,
                    "model_used": message.model_used,
                }
            )

        return messages, None
