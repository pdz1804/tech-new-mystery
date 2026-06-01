"""Langfuse tracing helpers for the Agent Core runtime.

The module is optional by design: local tests and development still work when
the Langfuse SDK or credentials are absent.
"""

from __future__ import annotations

from contextlib import contextmanager
import logging
import os
import re
from typing import Any

from agent_core.config import Settings

logger = logging.getLogger(__name__)

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"pk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"data:[\w/+.-]+;base64,[A-Za-z0-9+/=]{100,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)(['\"\s:=]+)[^,'\"\s}]+"),
]


def mask_langfuse_data(data: Any, **_: Any) -> Any:
    """Redact common secrets before they are sent to Langfuse."""
    if isinstance(data, str):
        masked = data
        for pattern in SECRET_PATTERNS:
            if pattern.groups >= 2:
                masked = pattern.sub(r"\1\2[REDACTED]", masked)
            else:
                masked = pattern.sub("[REDACTED]", masked)
        return masked
    if isinstance(data, list):
        return [mask_langfuse_data(item) for item in data]
    if isinstance(data, dict):
        return {
            key: (
                "[REDACTED]"
                if any(term in key.lower() for term in ("key", "secret", "token", "password"))
                else mask_langfuse_data(value)
            )
            for key, value in data.items()
        }
    return data


def _compact_metadata(value: Any) -> str:
    """Keep propagated metadata compatible with Langfuse limits."""
    text = str(value)
    return text[:200]


class LangfuseObserver:
    """Small adapter around Langfuse SDK and LangChain callback handler."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = bool(
            settings.langfuse_enabled
            and settings.langfuse_secret_key
            and settings.langfuse_public_key
        )
        self._client = None
        self._handler_cls = None
        self._propagate_attributes = None

        if not self.enabled:
            return

        try:
            os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key or "")
            os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key or "")
            os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_base_url)
            os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_base_url)
            from langfuse import Langfuse, propagate_attributes
            from langfuse.langchain import CallbackHandler

            self._client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_base_url,
                mask=mask_langfuse_data,
            )
            self._handler_cls = CallbackHandler
            self._propagate_attributes = propagate_attributes
            logger.info("[LANGFUSE] Agent Core tracing enabled")
        except Exception as exc:
            self.enabled = False
            logger.warning("[LANGFUSE] Tracing disabled: %s", exc)

    def _metadata(self, metadata: dict[str, Any]) -> dict[str, str]:
        base = {
            "service": "agent_core",
            "environment": self.settings.langfuse_environment or self.settings.environment,
            "agent_model": self.settings.agent_model,
            "bedrock_region": self.settings.bedrock_region,
            "runtime": "bedrock_agentcore",
            "graph": "langgraph_react",
        }
        if self.settings.langfuse_release:
            base["release"] = self.settings.langfuse_release
        base.update(metadata)
        return {
            re.sub(r"[^A-Za-z0-9_]", "_", key): _compact_metadata(value)
            for key, value in base.items()
            if value is not None
        }

    @contextmanager
    def trace_context(
        self,
        *,
        session_id: str,
        user_id: str,
        input_text: str,
        metadata: dict[str, Any],
    ):
        """Create a root trace span and propagate session/user metadata."""
        if not self.enabled or not self._client or not self._propagate_attributes:
            yield None
            return

        propagated_metadata = self._metadata(metadata)
        with self._client.start_as_current_observation(
            as_type="span",
            name="agent_core.invoke",
            input=input_text if self.settings.langfuse_trace_content else None,
            metadata=propagated_metadata,
        ) as span:
            with self._propagate_attributes(
                session_id=session_id,
                user_id=user_id,
                metadata=propagated_metadata,
                tags=["agent-core", "langgraph", "react-agent"],
            ):
                yield span

    def langgraph_config(
        self,
        *,
        session_id: str,
        user_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Return LangGraph config that attaches Langfuse's LangChain callback."""
        if not self.enabled or not self._handler_cls:
            return None
        try:
            handler = self._handler_cls()
        except Exception as exc:
            logger.warning("[LANGFUSE] Could not create callback handler: %s", exc)
            return None

        return {
            "callbacks": [handler],
            "run_name": "tech-news-agent-react",
            "metadata": self._metadata(
                {
                    **metadata,
                    "session_id": session_id,
                    "user_id": user_id,
                }
            ),
            "tags": ["agent-core", "langgraph", "react-agent"],
        }

    def update_trace(self, *, output: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        """Best-effort update of the current Langfuse observation."""
        if not self.enabled or not self._client:
            return
        try:
            self._client.update_current_span(
                output=output if self.settings.langfuse_trace_content else None,
                metadata=self._metadata(metadata or {}),
            )
        except Exception as exc:
            logger.debug("[LANGFUSE] update_current_span failed: %s", exc)

    def flush(self) -> None:
        """Flush queued Langfuse events."""
        if not self.enabled or not self._client:
            return
        try:
            self._client.flush()
        except Exception as exc:
            logger.debug("[LANGFUSE] flush failed: %s", exc)
