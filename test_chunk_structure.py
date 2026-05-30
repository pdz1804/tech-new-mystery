"""Debug: Check chunk.content structure"""
import asyncio
import sys
sys.path.insert(0, '.')

from agent_core.config import Settings
from agent_core.server import AgentRuntime
import logging

logging.basicConfig(level=logging.WARNING)

async def test():
    settings = Settings()
    runtime = AgentRuntime(settings)
    
    agent_input = runtime.build_input(
        user_message="What is 2+2?",
        history=[],
        context={},
    )
    
    token_count = 0
    async for event in runtime.graph.astream_events(agent_input, version="v2"):
        if event.get("event") == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, 'content'):
                token_count += 1
                if token_count <= 3:  # Only show first 3 tokens
                    print(f"Token #{token_count}:")
                    print(f"  chunk type: {type(chunk)}")
                    print(f"  chunk.content type: {type(chunk.content)}")
                    print(f"  chunk.content value: {chunk.content}")
                    print()

asyncio.run(test())
