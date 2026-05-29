"""AWS Bedrock AgentCore application server.

The @app.entrypoint is an async generator: every yielded dict becomes an SSE
event on the wire (handled automatically by BedrockAgentCoreApp / Starlette
StreamingResponse).

Event schema (mirrors what AgentCoreClient expects on the backend):
  {"type": "token",           "content": "<text chunk>"}
  {"type": "tool_invocation", "tool_name": "<name>", "tool_id": "<id>", "tool_args": {...}}
  {"type": "tool_result",     "tool_name": "<name>", "status": "completed"|"failed", "result_summary": "<...>"}
  {"type": "done"}
  {"type": "error",           "message": "<...>", "recoverable": true|false}
"""

from __future__ import annotations

import logging
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

app = BedrockAgentCoreApp(debug=settings.debug)
runtime = AgentRuntime(settings)
memory = AgentMemory(settings)


@app.entrypoint
async def agent_invocation(
    payload: dict,
    context: RequestContext,
) -> AsyncGenerator[dict, None]:
    """Stream a ReAct agent response as SSE events.

    Payload fields:
      prompt      — user message text (required)
      session_id  — conversation session identifier
      user_id     — caller user identifier (for memory scoping)
      context     — optional dict with recent_events from backend DynamoDB
    """
    user_message: str = payload.get("prompt", "").strip()
    session_id: str = context.session_id or payload.get("session_id", "default")
    user_id: str = payload.get("user_id", "anonymous")
    ctx: dict = payload.get("context", {})

    if not user_message:
        yield {"type": "error", "message": "Empty prompt", "recoverable": False}
        return

    logger.info("[AGENT] session=%s user=%s prompt_len=%d", session_id, user_id, len(user_message))

    # 1. Load long-term history from AWS AgentCore Memory
    history = await memory.get_last_k_turns(actor_id=user_id, session_id=session_id, k=5)

    # 2. Build LangGraph input (history + context + current message)
    agent_input = runtime.build_input(
        user_message=user_message,
        history=history,
        context=ctx,
    )

    # 3. Stream events from the ReAct agent
    assistant_response = ""
    error_occurred = False

    try:
        async for event in runtime.graph.astream_events(agent_input, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            # Token chunk from the LLM
            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content:
                    token = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                    assistant_response += token
                    yield {"type": "token", "content": token}

            # Tool about to be called
            elif kind == "on_tool_start":
                tool_input = event["data"].get("input", {})
                yield {
                    "type": "tool_invocation",
                    "tool_name": name,
                    "tool_id": event.get("run_id", ""),
                    "tool_args": tool_input if isinstance(tool_input, dict) else {"input": str(tool_input)},
                }

            # Tool finished
            elif kind == "on_tool_end":
                output = event["data"].get("output", "")
                summary = str(output)[:200] if output else ""
                yield {
                    "type": "tool_result",
                    "tool_name": name,
                    "status": "completed",
                    "result_summary": summary,
                }

    except Exception as exc:
        logger.error("[AGENT] Streaming error: %s", exc, exc_info=True)
        yield {
            "type": "error",
            "message": "Agent encountered an error processing your request",
            "recoverable": True,
        }
        error_occurred = True

    # 4. Persist turn to AWS AgentCore Memory (best-effort, non-blocking)
    if assistant_response and not error_occurred:
        await memory.save_turn(
            actor_id=user_id,
            session_id=session_id,
            user_message=user_message,
            assistant_message=assistant_response,
        )

    yield {"type": "done"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
