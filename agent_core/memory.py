"""AWS Bedrock AgentCore Memory integration.

Uses bedrock_agentcore.memory.client.MemoryClient directly.
Saves conversation turns and retrieves recent history per session.

Falls back silently when MEMORY_ID is not configured (local dev).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from agent_core.config import Settings

logger = logging.getLogger(__name__)


class AgentMemory:
    """Async wrapper around MemoryClient for conversation persistence."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

        if settings.memory_id:
            try:
                from bedrock_agentcore.memory.client import MemoryClient
                self._client = MemoryClient(region_name=settings.aws_region)
                logger.info("[MEMORY] MemoryClient ready — memory_id=%s", settings.memory_id)
            except Exception as exc:
                logger.warning("[MEMORY] Could not init MemoryClient: %s", exc)
        else:
            logger.info("[MEMORY] No MEMORY_ID configured — memory persistence disabled")

    @property
    def enabled(self) -> bool:
        return self._client is not None and bool(self._settings.memory_id)

    async def get_last_k_turns(
        self,
        actor_id: str,
        session_id: str,
        k: int = 5,
    ) -> list[tuple[str, str]]:
        """Return last k (role, content) pairs from AgentCore Memory."""
        if not self.enabled:
            return []
        try:
            turns = await asyncio.to_thread(
                self._client.get_last_k_turns,
                memory_id=self._settings.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                k=k,
            )
            messages: list[tuple[str, str]] = []
            for turn in turns:
                for msg in turn:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if content:
                        messages.append((role, content))
            return messages
        except Exception as exc:
            logger.warning("[MEMORY] get_last_k_turns failed: %s", exc)
            return []

    async def save_turn(
        self,
        actor_id: str,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Persist a user/assistant exchange to AgentCore Memory."""
        if not self.enabled:
            return
        try:
            from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole

            await asyncio.to_thread(
                self._client.save_conversation,
                memory_id=self._settings.memory_id,
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    (MessageRole.USER, user_message),
                    (MessageRole.ASSISTANT, assistant_message),
                ],
            )
            logger.debug("[MEMORY] Saved turn for session %s", session_id)
        except Exception as exc:
            logger.warning("[MEMORY] save_turn failed (non-fatal): %s", exc)
