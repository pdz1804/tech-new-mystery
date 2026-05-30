"""AWS Bedrock AgentCore application server.

Deployed as a container to aws_bedrockagentcore_agent_runtime.
Backend invokes it via:
  boto3.client('bedrock-agentcore').invoke_agent_runtime(
      agentRuntimeArn=..., runtimeSessionId=..., payload=...
  )

The @app.entrypoint is an async generator — each yielded dict becomes a
Server-Sent Event automatically by BedrockAgentCoreApp.

Event schema (matches AgentCoreClient in backend):
  {"type": "token",           "content": "<text>"}
  {"type": "tool_invocation", "tool_name": "...", "tool_id": "...", "tool_args": {...}}
  {"type": "tool_result",     "tool_name": "...", "status": "completed|failed", "result_summary": "..."}
  {"type": "done"}
  {"type": "error",           "message": "...", "recoverable": bool}

Memory (AWS Bedrock AgentCore Memory):
  - AgentMemory.get_last_k_turns() loads recent history before the agent call
  - AgentMemory.save_turn() persists the exchange after streaming completes
  - Both are no-ops when MEMORY_ID env var is absent (local dev)
"""

from __future__ import annotations

import logging
import os
from typing import AsyncGenerator

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext

from agent_core.config import settings
from agent_core.graph import AgentRuntime
from agent_core.memory import AgentMemory

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def _extract_text(content) -> str:
    """Extract visible text from LangChain/Bedrock content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and (item.get("type") in (None, "text")) and item.get("text")
        )
    return ""


async def _emit_text_chunks(text: str) -> AsyncGenerator[dict, None]:
    """Emit visible text in small chunks when LangChain only exposes model-end text."""
    import asyncio
    import re

    words = re.findall(r"\S+|\s+", text)
    chunk = ""

    for index, word in enumerate(words):
        chunk += word
        should_flush = (
            len(chunk.split()) >= 8
            or "\n" in word
            or index == len(words) - 1
        )
        if not should_flush:
            continue

        if chunk:
            yield {"type": "token", "content": chunk}
            chunk = ""

        if index < len(words) - 1:
            await asyncio.sleep(0.04)


# ---------------------------------------------------------------------------
# Load secrets from Secrets Manager (production only)
# Terraform injects APP_SECRET_ARN as an environment variable.
# ---------------------------------------------------------------------------

def _load_secrets_from_aws() -> None:
    secret_arn = os.environ.get("APP_SECRET_ARN")
    if not secret_arn:
        return
    try:
        import boto3
        import json
        client = boto3.client("secretsmanager", region_name=settings.aws_region)
        secret = json.loads(
            client.get_secret_value(SecretId=secret_arn)["SecretString"]
        )
        for key in ("OPENAI_API_KEY", "QDRANT_URL", "QDRANT_API_KEY"):
            if key in secret and not os.environ.get(key):
                os.environ[key] = secret[key]
        logger.info("[INIT] Secrets loaded from Secrets Manager")
    except Exception as exc:
        logger.warning("[INIT] Could not load secrets: %s", exc)


_load_secrets_from_aws()

# ---------------------------------------------------------------------------
# Initialize agent and memory
# ---------------------------------------------------------------------------

memory = AgentMemory(settings)
runtime = AgentRuntime(settings)

# ---------------------------------------------------------------------------
# BedrockAgentCoreApp entrypoint
# ---------------------------------------------------------------------------

app = BedrockAgentCoreApp(debug=settings.debug)


@app.entrypoint
async def agent_invocation(
    payload: dict,
    context: RequestContext,
) -> AsyncGenerator[dict, None]:
    """Stream ReAct agent response as SSE events."""
    user_message: str = payload.get("prompt", "").strip()
    session_id: str = context.session_id or payload.get("session_id", "default")
    user_id: str = payload.get("user_id", "anonymous")
    ctx: dict = payload.get("context", {})

    if not user_message:
        yield {"type": "error", "message": "Empty prompt", "recoverable": False}
        return

    logger.info("[AGENT] session=%s user=%s len=%d", session_id, user_id, len(user_message))

    # 1. Load conversation history from AgentCore Memory
    history = await memory.get_last_k_turns(
        actor_id=user_id, session_id=session_id, k=5
    )

    # 2. Build agent input (history + DynamoDB context + current message)
    agent_input = runtime.build_input(
        user_message=user_message,
        history=history,
        context=ctx,
    )

    assistant_response = ""
    error_occurred = False
    stream_chunk_events = 0
    stream_text_events = 0
    fallback_blocked = False

    yield {
        "type": "stream_diagnostic",
        "phase": "start",
        "real_streaming_required": settings.require_true_streaming,
        **runtime.streaming_diagnostics,
    }

    try:
        async for event in runtime.graph.astream_events(agent_input, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_chat_model_stream":
                # Real token-level streaming from Bedrock's ConverseStream API
                stream_chunk_events += 1
                chunk = event["data"].get("chunk")
                if chunk:
                    token = _extract_text(chunk.content)
                    if token:
                        stream_text_events += 1
                        assistant_response += token
                        logger.warning(f"[AGENT] Token event #{stream_text_events}: len={len(token)}")
                        yield {"type": "token", "content": token}

            elif kind == "on_chat_model_end":
                result = event["data"].get("output")
                output_text = ""
                has_tool_call = False
                if result:
                    has_tool_call = bool(getattr(result, "tool_calls", None))
                    content = result.content if hasattr(result, "content") else str(result)
                    if isinstance(content, str):
                        output_text = content
                    elif isinstance(content, list):
                        output_text = "".join(
                            item.get("text", "") if isinstance(item, dict) else str(item)
                            for item in content
                            if not (isinstance(item, dict) and item.get("type") == "tool_use")
                        )
                    else:
                        output_text = str(content)

                logger.warning(f"[AGENT] on_chat_model_end: has_tool_call={has_tool_call}, output_len={len(output_text)}, stream_text_events={stream_text_events}")

                # Tool-only turns often end without visible text. The final
                # answer should arrive in a later model call after tool_result.
                if has_tool_call or not output_text.strip():
                    logger.warning(f"[AGENT] Skipping on_chat_model_end: has_tool_call={has_tool_call}, empty_output={not output_text.strip()}")
                    continue

                # If LangGraph exposes a later model-end final answer after
                # streamed pre-tool text, forward the missing suffix instead of
                # dropping it. This is the post-tool answer path.
                missing_text = output_text
                if assistant_response and output_text.startswith(assistant_response):
                    missing_text = output_text[len(assistant_response):]
                elif assistant_response and output_text in assistant_response:
                    missing_text = ""

                if not missing_text.strip():
                    continue

                if settings.require_true_streaming and stream_text_events == 0:
                    fallback_blocked = True
                    logger.error(
                        "[AGENT] Real streaming required but no on_chat_model_stream text chunks were emitted. "
                        "stream_chunk_events=%d model=%s diagnostics=%s",
                        stream_chunk_events,
                        settings.agent_model,
                        runtime.streaming_diagnostics,
                    )
                    yield {
                        "type": "error",
                        "error_code": "TRUE_STREAMING_REQUIRED",
                        "message": (
                            "Real Bedrock ConverseStream was required, but LangGraph "
                            "finished with on_chat_model_end before emitting text chunks."
                        ),
                        "recoverable": False,
                        "stream_chunk_events": stream_chunk_events,
                        "stream_text_events": stream_text_events,
                        "diagnostics": runtime.streaming_diagnostics,
                    }
                    error_occurred = True
                    continue

                if stream_text_events > 0:
                    logger.warning(
                        "[AGENT] Forwarding post-tool model-end text because LangGraph did not emit "
                        "stream chunks for this final answer turn. chars=%d",
                        len(missing_text),
                    )

                async for token_event in _emit_text_chunks(missing_text):
                    assistant_response += token_event["content"]
                    yield token_event

            elif kind == "on_tool_start":
                tool_input = event["data"].get("input", {})
                yield {
                    "type": "tool_invocation",
                    "tool_name": name,
                    "tool_id": event.get("run_id", ""),
                    "tool_args": tool_input if isinstance(tool_input, dict) else {"input": str(tool_input)},
                }

            elif kind == "on_tool_end":
                output = event["data"].get("output", "")
                yield {
                    "type": "tool_result",
                    "tool_name": name,
                    "tool_id": event.get("run_id", ""),
                    "status": "completed",
                    "result_summary": str(output)[:200] if output else "",
                }

    except Exception as exc:
        logger.error("[AGENT] Streaming error: %s", exc, exc_info=True)
        yield {"type": "error", "message": "Agent error processing request", "recoverable": True}
        error_occurred = True

    if settings.require_true_streaming and not assistant_response and not error_occurred:
        fallback_blocked = True
        error_occurred = True
        logger.error(
            "[AGENT] Real streaming required but the graph completed without streamed text. "
            "stream_chunk_events=%d model=%s diagnostics=%s",
            stream_chunk_events,
            settings.agent_model,
            runtime.streaming_diagnostics,
        )
        yield {
            "type": "error",
            "error_code": "TRUE_STREAMING_REQUIRED",
            "message": "Real Bedrock ConverseStream was required, but no text chunks were emitted.",
            "recoverable": False,
            "stream_chunk_events": stream_chunk_events,
            "stream_text_events": stream_text_events,
            "diagnostics": runtime.streaming_diagnostics,
        }

    # 3. Persist turn to AgentCore Memory (best-effort)
    if assistant_response and not error_occurred:
        await memory.save_turn(
            actor_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_message=assistant_response,
        )

    yield {
        "type": "stream_diagnostic",
        "phase": "complete",
        "real_streaming_used": stream_text_events > 0,
        "fallback_blocked": fallback_blocked,
        "stream_chunk_events": stream_chunk_events,
        "stream_text_events": stream_text_events,
    }

    yield {"type": "done"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
