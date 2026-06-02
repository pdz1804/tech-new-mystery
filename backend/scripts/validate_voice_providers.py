"""Validate configured voice-provider connectivity without printing secrets."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
import uuid

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings


async def main() -> None:
    results: dict[str, object] = {}

    async with httpx.AsyncClient(timeout=20) as client:
        stt_response = await client.post(
            "https://api.elevenlabs.io/v1/single-use-token/realtime_scribe",
            headers={"xi-api-key": settings.elevenlabs_api_key or ""},
        )
        stt_json = (
            stt_response.json()
            if stt_response.status_code == 200
            and stt_response.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        results["elevenlabs_stt_token_status"] = stt_response.status_code
        results["elevenlabs_stt_token_has_token"] = bool(stt_json.get("token"))

        tts_response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}/stream",
            params={"output_format": settings.elevenlabs_tts_output_format},
            headers={
                "xi-api-key": settings.elevenlabs_api_key or "",
                "Content-Type": "application/json",
            },
            json={
                "text": "Voice test.",
                "model_id": settings.elevenlabs_tts_model_id,
            },
        )
        results["elevenlabs_tts_status"] = tts_response.status_code
        results["elevenlabs_tts_audio_bytes"] = (
            len(tts_response.content) if tts_response.status_code == 200 else 0
        )

        if settings.langsmith_tracing and settings.langsmith_api_key:
            run_id = str(uuid.uuid4())
            trace_response = await client.post(
                f"{settings.langsmith_endpoint.rstrip('/')}/runs",
                headers={
                    "x-api-key": settings.langsmith_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "id": run_id,
                    "name": "voice.validation.check",
                    "run_type": "chain",
                    "inputs": {"check": "voice_provider_connectivity"},
                    "outputs": {"status": "ok"},
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": datetime.now(timezone.utc).isoformat(),
                    "session_name": settings.langsmith_project,
                    "extra": {
                        "metadata": {
                            "voice_stack": "livekit-elevenlabs-langchain",
                            "validation": True,
                        }
                    },
                },
            )
            results["langsmith_run_status"] = trace_response.status_code
        else:
            results["langsmith_run_status"] = "disabled"

        if settings.livekit_url:
            livekit_http_url = (
                settings.livekit_url.replace("wss://", "https://").replace("ws://", "http://")
            )
            livekit_response = await client.get(livekit_http_url)
            results["livekit_http_status"] = livekit_response.status_code
        else:
            results["livekit_http_status"] = "missing_url"

    print(results)


if __name__ == "__main__":
    asyncio.run(main())
