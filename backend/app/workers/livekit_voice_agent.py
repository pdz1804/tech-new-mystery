"""LiveKit SIP transport adapter for the existing Tech News voice agent.

This module is not a second agent brain. It exists only because dialable phone
calls need a LiveKit Agents worker to own realtime SIP audio, turn detection,
barge-in, DTMF, and TTS playout. Committed turns are forwarded to the existing
backend voice-agent endpoint.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from livekit import agents, rtc
from livekit.agents import Agent, AgentSession, ChatContext, JobContext, ModelSettings, RoomInputOptions, RoomOutputOptions, TurnHandlingOptions
from livekit.plugins import silero
from livekit.plugins import elevenlabs

from app.config import settings
from app.integrations.livekit_voice_backend_client import LiveKitVoiceBackendClient

logger = logging.getLogger("tech_news_livekit_voice")
logging.basicConfig(level=logging.INFO)

BACKEND_DIR = Path(__file__).resolve().parents[3]
REPO_ROOT = BACKEND_DIR.parent

# LiveKit's worker CLI reads LIVEKIT_URL/API_KEY/API_SECRET from os.environ.
# Pydantic can read .env files for our app settings, but it does not export
# those values into os.environ, so load them explicitly before run_app().
load_dotenv(REPO_ROOT / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env", override=True)


class TechNewsVoiceTransportAgent(Agent):
    """LiveKit-facing shell for the existing voice agent."""

    def __init__(
        self,
        *,
        backend: LiveKitVoiceBackendClient,
        session_id: str | None,
        call_id: str,
        livekit_room: str,
    ) -> None:
        super().__init__(
            instructions=(
                "You are Tech News Mystery's phone voice transport. Keep any "
                "direct spoken fallback short and natural. The backend voice "
                "agent owns the actual answer."
            )
        )
        self._backend = backend
        self._session_id = session_id
        self._call_id = call_id
        self._livekit_room = livekit_room

    @property
    def session_id(self) -> str | None:
        return self._session_id

    async def llm_node(
        self,
        chat_ctx: ChatContext,
        tools: list[Any],
        model_settings: ModelSettings,
    ):
        """Generate speech by forwarding the caller text to the existing backend voice agent."""
        del tools, model_settings

        user_text = ""
        for item in reversed(chat_ctx.items):
            role = getattr(item, "role", None)
            text_content = getattr(item, "text_content", None)
            if role == "user" and isinstance(text_content, str) and text_content.strip():
                user_text = text_content.strip()
                break
            content = getattr(item, "content", None)
            if role == "user" and isinstance(content, list):
                text_parts = [part for part in content if isinstance(part, str)]
                if text_parts:
                    user_text = " ".join(text_parts).strip()
                    break

        if not user_text:
            logger.warning("LiveKit committed a user turn but no speakable text was found")
            yield "I did not catch that. Could you say it again?"
            return

        logger.info("Forwarding phone turn to backend voice agent: %s", user_text)
        try:
            result = await self._backend.send_voice_turn(
                session_id=self._session_id,
                content=user_text,
                call_id=self._call_id,
                livekit_room=self._livekit_room,
            )
        except Exception:
            logger.exception("Backend voice agent failed while handling phone turn")
            yield "I heard you, but I hit a backend issue while checking that. Please try again in a moment."
            return

        self._session_id = result.session_id
        logger.info("Backend voice agent returned %d characters", len(result.content))
        yield result.content


def _job_metadata(ctx: JobContext) -> dict[str, Any]:
    raw = getattr(ctx.job, "metadata", None) or "{}"
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _build_session() -> AgentSession:
    turn_detection = None
    if settings.livekit_turn_detector_enabled:
        if os.getenv("LIVEKIT_AGENT_ID") or os.getenv("LIVEKIT_INFERENCE_URL"):
            from livekit.plugins.turn_detector.multilingual import MultilingualModel

            turn_detection = MultilingualModel()
        else:
            logger.warning(
                "LIVEKIT_TURN_DETECTOR_ENABLED=true, but no LiveKit inference executor context "
                "was detected for this local worker. Falling back to Silero VAD endpointing."
            )
    interruption_mode = "adaptive" if turn_detection is not None else "vad"

    return AgentSession(
        stt=elevenlabs.STT(
            api_key=settings.elevenlabs_api_key,
            model_id=settings.elevenlabs_stt_model_id,
        ),
        vad=silero.VAD.load(),
        turn_handling=TurnHandlingOptions(
            turn_detection=turn_detection,
            interruption={
                "enabled": True,
                "mode": interruption_mode,
                "min_duration": 0.25,
                "min_words": 1,
                "resume_false_interruption": True,
                "false_interruption_timeout": 2.0,
            },
            user_turn_limit={
                "max_duration": 45.0,
                "max_words": 120,
            },
        ),
        tts=elevenlabs.TTS(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.elevenlabs_voice_id,
            model=settings.elevenlabs_tts_model_id,
        ),
        ivr_detection=False,
    )


async def entrypoint(ctx: JobContext) -> None:
    """Run one LiveKit voice-agent job for a web or SIP room."""

    metadata = _job_metadata(ctx)
    session_id = metadata.get("session_id")
    call_id = str(metadata.get("call_id") or ctx.room.name)
    backend = LiveKitVoiceBackendClient()
    session = _build_session()
    disconnected = asyncio.Event()
    active_response_task: asyncio.Task[None] | None = None
    turn_sequence = 0

    transport_agent = TechNewsVoiceTransportAgent(
        backend=backend,
        session_id=session_id if isinstance(session_id, str) else None,
        call_id=call_id,
        livekit_room=ctx.room.name,
    )

    async def answer_phone_turn(content: str, dtmf_digit: str | None = None) -> None:
        nonlocal session_id
        logger.info("Forwarding phone turn to backend voice agent: %s", content or f"DTMF {dtmf_digit}")
        result = await backend.send_voice_turn(
            session_id=session_id if isinstance(session_id, str) else None,
            content=content,
            call_id=call_id,
            livekit_room=ctx.room.name,
            dtmf_digit=dtmf_digit,
        )
        session_id = result.session_id
        logger.info("Backend voice agent returned %d characters", len(result.content))
        await session.say(result.content, allow_interruptions=True)

    async def interrupt_current_response(reason: str) -> None:
        nonlocal active_response_task

        current_task = asyncio.current_task()
        if active_response_task and active_response_task is not current_task and not active_response_task.done():
            logger.info("Cancelling active phone response because %s", reason)
            active_response_task.cancel()

        try:
            await session.interrupt(force=True)
        except Exception:
            logger.debug("No active speech to interrupt for %s", reason, exc_info=True)

    def schedule_phone_turn(content: str, dtmf_digit: str | None = None) -> None:
        nonlocal active_response_task, turn_sequence

        turn_sequence += 1
        turn_id = turn_sequence
        previous_response_task = active_response_task

        async def run_turn() -> None:
            try:
                if previous_response_task and not previous_response_task.done():
                    logger.info("Cancelling active phone response before turn %s", turn_id)
                    previous_response_task.cancel()
                await interrupt_current_response(f"new turn {turn_id}")
                await answer_phone_turn(content, dtmf_digit=dtmf_digit)
            except asyncio.CancelledError:
                logger.info("Phone response task cancelled for superseded turn %s", turn_id)
                raise
            except Exception:
                logger.exception("Failed to handle phone turn %s", turn_id)
                await session.say(
                    "I heard you, but I hit a backend issue while checking that. Please try again in a moment.",
                    allow_interruptions=True,
                )

        active_response_task = asyncio.create_task(run_turn())

    @session.on("user_state_changed")
    def on_user_state_changed(ev: Any) -> None:
        new_state = str(getattr(ev, "new_state", "") or getattr(ev, "state", "") or "")
        if new_state.lower() != "speaking":
            return

        async def handle_user_speech_started() -> None:
            await interrupt_current_response("caller started speaking")

        asyncio.create_task(handle_user_speech_started())

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(ev: Any) -> None:
        if not getattr(ev, "is_final", False):
            return

        transcript = str(getattr(ev, "transcript", "") or "").strip()
        if not transcript:
            return

        schedule_phone_turn(transcript)

    @ctx.room.on("sip_dtmf_received")
    def on_dtmf(dtmf: rtc.SipDTMF) -> None:
        logger.info("DTMF received from %s: %s", dtmf.participant.identity, dtmf.digit)

        async def handle_digit() -> None:
            try:
                await interrupt_current_response("DTMF input")
                schedule_phone_turn("", dtmf_digit=dtmf.digit)
            except Exception:
                logger.exception("Failed to handle DTMF input")
                await session.say("I had trouble reading that keypad input. Please try again.")

        asyncio.create_task(handle_digit())

    @ctx.room.on("disconnected")
    def on_room_disconnected(*_: Any) -> None:
        disconnected.set()

    try:
        await ctx.connect()
        await session.start(
            room=ctx.room,
            agent=transport_agent,
            room_input_options=RoomInputOptions(),
            room_output_options=RoomOutputOptions(transcription_enabled=False),
        )

        # The greeting is transport-owned because this worker intentionally
        # does not configure a LiveKit LLM; substantive answers are generated
        # by the existing backend voice agent through TechNewsVoiceTransportAgent.
        await session.say(
            "Hi, you're speaking with Tech News Mystery. What tech news topic would you like to discuss?",
            allow_interruptions=True,
        )
        await disconnected.wait()
    finally:
        await backend.close()


if __name__ == "__main__":
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            agent_name=settings.livekit_agent_name,
        )
    )
