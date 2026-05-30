"""Chat service for conversation management."""

import asyncio
import uuid
from pynamodb.exceptions import DoesNotExist

from app.models.chat import ConversationSessionModel, ConversationMessageModel
from app.utils.time import now_timestamp


# TTL: 90 days in seconds
CHAT_TTL_SECONDS = 90 * 24 * 60 * 60


class ChatService:
    """Chat service for managing conversation sessions and messages."""

    async def create_session(self, user_id: str, title: str, description: str | None = None) -> dict:
        """Create a new conversation session.

        Args:
            user_id: User ID who owns the session
            title: Session title
            description: Optional session description

        Returns:
            Created session data dict
        """
        now = now_timestamp()
        session_id = str(uuid.uuid4())
        expires_at = now + CHAT_TTL_SECONDS

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

        def _save():
            session.save()

        await asyncio.to_thread(_save)

        return {
            "session_id": session_id,
            "user_id": user_id,
            "title": title,
            "description": description,
            "created_at": now,
            "updated_at": now,
            "last_message_at": now,
            "message_count": 0,
            "is_active": True,
        }

    async def get_session(self, session_id: str, user_id: str) -> dict | None:
        """Get a conversation session by ID.

        Args:
            session_id: Session ID to retrieve
            user_id: User ID for access control

        Returns:
            Session data dict or None if not found or user doesn't have access
        """
        def _get():
            try:
                return ConversationSessionModel.get(user_id, session_id)
            except DoesNotExist:
                return None

        session = await asyncio.to_thread(_get)

        if not session:
            return None

        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "title": session.title,
            "description": session.description,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "last_message_at": session.last_message_at,
            "message_count": session.message_count,
            "is_active": session.is_active,
        }

    async def list_sessions(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "recency",
    ) -> dict:
        """List conversation sessions for a user with pagination.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            page_size: Items per page
            sort_by: Sort field ('recency' = last_message_at desc)

        Returns:
            Dict with sessions list, total count, and pagination info
        """
        def _query():
            # Query using user_last_message_index for sorting by last_message_at
            if sort_by == "recency":
                # Query descending by last_message_at
                query = ConversationSessionModel.user_last_message_index.query(
                    user_id,
                    scan_index_forward=False,  # Descending order
                )
            else:
                # Default: regular query (ascending by session_id)
                query = ConversationSessionModel.query(user_id)

            items = []
            for item in query:
                if item.is_active:  # Only include active sessions
                    items.append(item)

            return items

        all_sessions = await asyncio.to_thread(_query)

        # Manual pagination
        total = len(all_sessions)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        sessions = all_sessions[start_idx:end_idx]

        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "user_id": s.user_id,
                    "title": s.title,
                    "description": s.description,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                    "last_message_at": s.last_message_at,
                    "message_count": s.message_count,
                    "is_active": s.is_active,
                }
                for s in sessions
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": end_idx < total,
            "has_prev": page > 1,
        }

    async def add_message(
        self,
        session_id: str,
        user_id: str,
        role: str,
        content: str,
        token_count: int | None = None,
        model_used: str | None = None,
    ) -> dict:
        """Add a message to a conversation session.

        Args:
            session_id: Session ID
            user_id: User ID for access control
            role: Message role ('user' or 'assistant')
            content: Message content
            token_count: Optional token count for LLM responses
            model_used: Optional model name for LLM responses

        Returns:
            Created message data dict
        """
        # Verify session ownership
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError(f"Session {session_id} not found or access denied")

        now = now_timestamp()
        message_id = str(uuid.uuid4())
        expires_at = now + CHAT_TTL_SECONDS

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

        def _save_message():
            message.save()

        await asyncio.to_thread(_save_message)

        # Update session's last_message_at and message_count
        await self._update_session_metadata(session_id, user_id)

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
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Get messages from a conversation session with pagination.

        Args:
            session_id: Session ID
            user_id: User ID for access control
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Dict with messages list and pagination info
        """
        # Verify session ownership
        session = await self.get_session(session_id, user_id)
        if not session:
            raise ValueError(f"Session {session_id} not found or access denied")

        def _query():
            # Query messages by session_timestamp_index, ascending order (oldest first)
            query = ConversationMessageModel.session_timestamp_index.query(
                session_id,
                scan_index_forward=True,  # Ascending: oldest first
            )
            items = []
            for item in query:
                items.append(item)
            return items

        all_messages = await asyncio.to_thread(_query)

        # Manual pagination
        total = len(all_messages)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        messages = all_messages[start_idx:end_idx]

        return {
            "messages": [
                {
                    "message_id": m.message_id,
                    "session_id": m.session_id,
                    "user_id": m.user_id,
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp,
                    "token_count": m.token_count,
                    "model_used": m.model_used,
                }
                for m in messages
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_next": end_idx < total,
            "has_prev": page > 1,
        }

    async def archive_session(self, session_id: str, user_id: str) -> bool:
        """Archive (deactivate) a conversation session.

        Args:
            session_id: Session ID to archive
            user_id: User ID for access control

        Returns:
            True if archived successfully, False if not found/access denied
        """
        def _get_and_update():
            try:
                session = ConversationSessionModel.get(user_id, session_id)
                session.is_active = False
                session.updated_at = now_timestamp()
                session.save()
                return True
            except DoesNotExist:
                return False

        return await asyncio.to_thread(_get_and_update)

    async def restore_session(self, session_id: str, user_id: str) -> dict | None:
        """Restore (reactivate) an archived conversation session."""
        now = now_timestamp()

        def _restore():
            try:
                session = ConversationSessionModel.get(user_id, session_id)
                session.is_active = True
                session.updated_at = now
                session.save()
                return session
            except DoesNotExist:
                return None

        restored = await asyncio.to_thread(_restore)
        if not restored:
            return None
        return {
            "session_id": restored.session_id,
            "user_id": restored.user_id,
            "title": restored.title,
            "description": restored.description,
            "created_at": restored.created_at,
            "updated_at": restored.updated_at,
            "last_message_at": restored.last_message_at,
            "message_count": restored.message_count,
            "is_active": restored.is_active,
        }

    async def rename_session(self, session_id: str, user_id: str, title: str) -> dict | None:
        """Rename a conversation session."""
        now = now_timestamp()

        def _rename():
            try:
                session = ConversationSessionModel.get(user_id, session_id)
                session.title = title
                session.updated_at = now
                session.save()
                return session
            except DoesNotExist:
                return None

        renamed = await asyncio.to_thread(_rename)
        if not renamed:
            return None
        return {
            "session_id": renamed.session_id,
            "user_id": renamed.user_id,
            "title": renamed.title,
            "description": renamed.description,
            "created_at": renamed.created_at,
            "updated_at": renamed.updated_at,
            "last_message_at": renamed.last_message_at,
            "message_count": renamed.message_count,
            "is_active": renamed.is_active,
        }

    async def delete_session(self, session_id: str, user_id: str) -> bool:
        """Hard delete a session and all its messages."""
        # Validate ownership
        session = await self.get_session(session_id, user_id)
        if not session:
            return False

        def _delete():
            # Delete messages first
            for item in ConversationMessageModel.session_timestamp_index.query(session_id):
                item.delete()
            # Delete session
            try:
                s = ConversationSessionModel.get(user_id, session_id)
                s.delete()
                return True
            except DoesNotExist:
                return False

        return await asyncio.to_thread(_delete)

    async def _update_session_metadata(self, session_id: str, user_id: str) -> None:
        """Update session's last_message_at and message_count.

        Args:
            session_id: Session ID
            user_id: User ID
        """
        def _update():
            try:
                session = ConversationSessionModel.get(user_id, session_id)
                session.last_message_at = now_timestamp()
                session.message_count = (session.message_count or 0) + 1
                session.updated_at = now_timestamp()
                session.save()
            except DoesNotExist:
                pass

        await asyncio.to_thread(_update)
