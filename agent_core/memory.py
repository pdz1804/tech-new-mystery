"""AWS Bedrock AgentCore Memory integration.

Uses MemorySessionManager for conversational event storage.
Falls back gracefully when MEMORY_ID is not configured (local dev without AWS Memory resource).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from agent_core.config import Settings

logger = logging.getLogger(__name__)


class AgentMemory:
    """Thin async wrapper around MemorySessionManager.

    When settings.memory_id is None (local dev / no Memory resource provisioned),
    all operations are no-ops so the rest of the agent continues working.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._manager = None

        if settings.memory_id:
            try:
                from bedrock_agentcore.memory.session import MemorySessionManager

                self._manager = MemorySessionManager(
                    memory_id=settings.memory_id,
                    region_name=settings.aws_region,
                )
                logger.info("[MEMORY] MemorySessionManager ready — memory_id=%s", settings.memory_id)
            except Exception as exc:
                logger.warning("[MEMORY] Could not init MemorySessionManager: %s", exc)
        else:
            logger.info("[MEMORY] No MEMORY_ID configured — memory persistence disabled")

    @property
    def enabled(self) -> bool:
        return self._manager is not None

    # ------------------------------------------------------------------
    # Retrieve conversation history
    # ------------------------------------------------------------------

    async def get_last_k_turns(
        self,
        actor_id: str,
        session_id: str,
        k: int = 5,
    ) -> list[tuple[str, str]]:
        """Return last k (user, assistant) message pairs from AWS memory.

        Returns:
            List of (role, content) tuples in chronological order.
        """
        if not self._manager:
            return []

        try:
            turns = await asyncio.to_thread(
                self._manager.get_last_k_turns,
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

    # ------------------------------------------------------------------
    # Save conversation turn
    # ------------------------------------------------------------------

    async def save_turn(
        self,
        actor_id: str,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Persist a user/assistant exchange to AWS AgentCore Memory."""
        if not self._manager:
            return

        try:
            from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole

            await asyncio.to_thread(
                self._manager.add_turns,
                actor_id=actor_id,
                session_id=session_id,
                messages=[
                    ConversationalMessage(user_message, MessageRole.USER),
                    ConversationalMessage(assistant_message, MessageRole.ASSISTANT),
                ],
            )
            logger.debug("[MEMORY] Saved turn for session %s", session_id)
        except Exception as exc:
            logger.warning("[MEMORY] save_turn failed (non-fatal): %s", exc)
