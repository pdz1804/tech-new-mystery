import asyncio
import json
import sys
sys.path.insert(0, '.')

from agent_core.config import Settings
from agent_core.server import AgentRuntime
import logging

logging.basicConfig(level=logging.DEBUG, format='%(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

async def test_streaming():
    settings = Settings()
    runtime = AgentRuntime(settings)
    
    # Test query that requires tool use
    user_message = "What are the latest quantum computing breakthroughs?"
    history = []
    context = {}
    
    agent_input = runtime.build_input(
        user_message=user_message,
        history=history,
        context=context,
    )
    
    print("\n=== AGENT STREAMING TEST ===\n")
    print(f"Query: {user_message}\n")
    print("Events received:")
    print("-" * 80)
    
    event_count = {}
    tokens = []
    
    async for event in runtime.graph.astream_events(agent_input, version="v2"):
        kind = event.get("event", "")
        name = event.get("name", "")
        
        event_count[kind] = event_count.get(kind, 0) + 1
        
        # Display event type
        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk:
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if content and isinstance(content, str):
                    tokens.append(content)
                    print(f"  on_chat_model_stream: '{content}' (token #{len(tokens)})")
        
        elif kind == "on_chat_model_end":
            result = event["data"].get("output")
            has_tool = bool(getattr(result, "tool_calls", None))
            content = result.content if hasattr(result, "content") else str(result)
            print(f"  on_chat_model_end: tool_calls={has_tool}, content_len={len(str(content))}")
        
        elif kind == "on_tool_start":
            tool_input = event["data"].get("input", {})
            print(f"  on_tool_start: {name} with args: {list(tool_input.keys()) if isinstance(tool_input, dict) else 'N/A'}")
        
        elif kind == "on_tool_end":
            output = event["data"].get("output", "")
            print(f"  on_tool_end: {name} (output_len={len(str(output))})")
        
        else:
            print(f"  {kind}: {name}")
    
    print("-" * 80)
    print(f"\n=== SUMMARY ===")
    print(f"Total tokens: {len(tokens)}")
    print(f"Token content: {''.join(tokens)[:200]}...")
    print(f"\nEvent counts: {dict(event_count)}")

if __name__ == "__main__":
    asyncio.run(test_streaming())
