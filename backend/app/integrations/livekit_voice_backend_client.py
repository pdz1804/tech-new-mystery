"""Client for LiveKit SIP transport calls into the existing voice agent."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass(frozen=True)
class VoiceTurnResult:
    """Voice turn response returned by the backend SIP bridge."""

    session_id: str
    content: str


class LiveKitVoiceBackendClient:
    """Thin async client around the existing backend voice-agent endpoint.

    This is intentionally only a transport bridge. The actual voice-agent logic
    remains the existing `/chat/voice/sip/message` backend path, which reuses
    Agent Core, LangGraph, persistence, and voice telemetry.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.voice_backend_base_url.rstrip("/"),
            timeout=httpx.Timeout(settings.agent_core_timeout + settings.elevenlabs_timeout),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def send_voice_turn(
        self,
        *,
        session_id: str | None,
        content: str,
        call_id: str | None = None,
        livekit_room: str | None = None,
        dtmf_digit: str | None = None,
    ) -> VoiceTurnResult:
        """Send a committed phone turn to the existing backend voice agent."""

        headers: dict[str, str] = {}
        if settings.voice_worker_service_token:
            headers["X-Voice-Worker-Token"] = settings.voice_worker_service_token

        text = content.strip()
        if dtmf_digit:
            text = f"Caller pressed {dtmf_digit}."

        response = await self._client.post(
            "/chat/voice/sip/message",
            headers=headers,
            json={
                "session_id": session_id,
                "content": text,
                "call_id": call_id,
                "livekit_room": livekit_room,
                "dtmf_digit": dtmf_digit,
            },
        )
        response.raise_for_status()

        payload = response.json()
        data = payload.get("data") or {}
        answer = data.get("content")
        returned_session_id = data.get("session_id")

        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Backend voice endpoint returned no speakable content")
        if not isinstance(returned_session_id, str) or not returned_session_id:
            raise RuntimeError("Backend voice endpoint returned no session_id")

        return VoiceTurnResult(session_id=returned_session_id, content=answer.strip())

