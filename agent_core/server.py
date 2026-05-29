"""Bedrock Agent Core App surface for the Agent Core runtime."""

from __future__ import annotations

import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent_core.config import settings
from agent_core.graph import AgentRuntime

logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()
runtime = AgentRuntime(settings)


@app.entrypoint
async def agent_invocation(payload, context):
    """Invoke the LangGraph agent.

    Payload structure:
    {
        "prompt": "user query",
        "session_id": "session identifier",
        "context": {optional context data}
    }
    """
    try:
        prompt = payload.get("prompt", "")
        session_id = payload.get("session_id", "default_session")
        context_data = payload.get("context", {})

        # Build message for the graph
        msg = {
            "messages": [{"role": "user", "content": prompt}],
            "user_message": prompt,
            "session_id": session_id,
            "context": context_data
        }

        # Invoke the agent runtime
        result = await runtime.graph.ainvoke(msg)

        # Extract response from agent output
        response_msg = result.get('messages', [{}])[-1]
        response_text = response_msg.get('content', 'No response generated')

        return {
            "response": response_text,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Agent invocation error: {e}", exc_info=True)
        return {
            "response": f"Error processing request: {str(e)}",
            "status": "error"
        }


if __name__ == "__main__":
    app.run()

