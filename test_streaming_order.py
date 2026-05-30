"""Test to show the EXACT order of events from Agent Core."""
import asyncio
import json
import sys
sys.path.insert(0, '.')

from agent_core.config import Settings
from agent_core.server import AgentRuntime
import logging

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

async def test():
    settings = Settings()
    runtime = AgentRuntime(settings)
    
    # Simple query requiring tool use
    agent_input = runtime.build_input(
        user_message="What are the latest AI breakthroughs?",
        history=[],
        context={},
    )
    
    print("\n" + "="*100)
    print("STREAMING EVENT ORDER TEST")
    print("="*100 + "\n")
    
    event_timeline = []
    
    async for event in runtime.graph.astream_events(agent_input, version="v2"):
        kind = event.get("event", "")
        name = event.get("name", "")
        
        # Track different event types
        if kind == "on_chat_model_stream":
            chunk = event["data"].get("chunk")
            if chunk and hasattr(chunk, 'content'):
                text = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                if text:
                    event_timeline.append(("TOKEN", f"'{text[:20]}...'"))
        
        elif kind == "on_chat_model_end":
            result = event["data"].get("output", {})
            has_tools = bool(getattr(result, "tool_calls", None))
            event_timeline.append(("CHAT_MODEL_END", f"tools={has_tools}"))
        
        elif kind == "on_tool_start":
            event_timeline.append(("TOOL_START", name))
        
        elif kind == "on_tool_end":
            event_timeline.append(("TOOL_END", name))
        
        elif kind == "on_chain_end" and name in ("agent", "LangGraph"):
            event_timeline.append(("AGENT_END", ""))
    
    # Print timeline
    for i, (event_type, detail) in enumerate(event_timeline, 1):
        print(f"{i:3d}. {event_type:20s} {detail}")
    
    print("\n" + "="*100)
    print("KEY OBSERVATIONS:")
    print("="*100)
    
    # Analyze
    token_groups = []
    current_group = []
    for event_type, detail in event_timeline:
        if event_type == "TOKEN":
            current_group.append(detail)
        else:
            if current_group:
                token_groups.append(len(current_group))
                current_group = []
    if current_group:
        token_groups.append(len(current_group))
    
    print(f"\nToken groups detected: {token_groups}")
    if len(token_groups) >= 2:
        print(f"  ✓ Group 1 (initial response): {token_groups[0]} tokens")
        print(f"  ✓ Group 2 (after tool): {token_groups[1]} tokens") 
    
    # Check order
    has_tool_start = any(e[0] == "TOOL_START" for e in event_timeline)
    has_tool_end = any(e[0] == "TOOL_END" for e in event_timeline)
    
    if has_tool_start and has_tool_end:
        tool_start_idx = next(i for i, (e, _) in enumerate(event_timeline) if e == "TOOL_START")
        tool_end_idx = next(i for i, (e, _) in enumerate(event_timeline) if e == "TOOL_END")
        tokens_after_tool = sum(1 for i in range(tool_end_idx, len(event_timeline)) if event_timeline[i][0] == "TOKEN")
        
        print(f"\n  Tool execution: positions {tool_start_idx}-{tool_end_idx}")
        print(f"  Tokens AFTER tool execution: {tokens_after_tool}")
        
        if tokens_after_tool > 0:
            print(f"  ✓ GOOD: Agent makes second call with final answer tokens")
        else:
            print(f"  ✗ PROBLEM: No tokens after tool - agent might not be making final answer call!")

asyncio.run(test())
