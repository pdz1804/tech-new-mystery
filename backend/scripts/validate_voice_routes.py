"""Validate voice FastAPI routes in-process without printing secrets."""

from __future__ import annotations

from pathlib import Path
import sys

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.chat.auth import get_chat_auth_user
from app.main import app


def _test_user() -> dict[str, str]:
    return {"sub": "voice-route-test-user"}


async def main() -> None:
    app.dependency_overrides[get_chat_auth_user] = _test_user

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        livekit = await client.post(
            "/v1/chat/voice/livekit-session",
            json={"session_id": "voice-route-test-session"},
        )
        livekit_json = livekit.json() if livekit.headers.get("content-type", "").startswith("application/json") else {}
        livekit_data = livekit_json.get("data") or {}

        stt = await client.post("/v1/chat/voice/stt-token")
        stt_json = stt.json() if stt.headers.get("content-type", "").startswith("application/json") else {}
        stt_data = stt_json.get("data") or {}

        tts = await client.post("/v1/chat/voice/speech", json={"text": "Voice route test."})

        event = await client.post(
            "/v1/chat/voice/events",
            json={
                "session_id": "voice-route-test-session",
                "phase": "route_validation",
                "provider": "elevenlabs",
                "transport": "livekit",
                "livekit_room": livekit_data.get("room"),
                "transcript_chars": 16,
                "output_chars": 17,
                "latency_ms": 1,
            },
        )
        event_json = event.json() if event.headers.get("content-type", "").startswith("application/json") else {}
        event_data = event_json.get("data") or {}

    app.dependency_overrides.clear()

    print(
        {
            "livekit_status": livekit.status_code,
            "livekit_has_room": bool(livekit_data.get("room")),
            "livekit_has_token": bool(livekit_data.get("participant_token")),
            "stt_status": stt.status_code,
            "stt_has_token": bool(stt_data.get("token")),
            "tts_status": tts.status_code,
            "tts_audio_bytes": len(tts.content) if tts.status_code == 200 else 0,
            "event_status": event.status_code,
            "event_tracing_enabled": event_data.get("tracing_enabled"),
        }
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
