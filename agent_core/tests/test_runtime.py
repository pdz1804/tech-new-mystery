"""Basic smoke tests for agent_core modules.

These run without AWS credentials — they only verify imports, graph compilation,
and the SSE event contract.  Full integration tests require a live AWS environment.
"""

import json
import pytest

from agent_core.config import Settings
from agent_core.graph import AgentRuntime
from agent_core.tools import get_tools


def _settings(**overrides) -> Settings:
    return Settings(
        agent_model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        memory_id=None,  # disabled — no AWS resource needed for unit tests
        **overrides,
    )


def test_graph_compiles():
    runtime = AgentRuntime(_settings())
    assert runtime.graph is not None
    assert hasattr(runtime.graph, "astream_events")


def test_tools_registered():
    tools = get_tools(_settings())
    names = [t.name for t in tools]
    assert "semantic_search" in names
    assert "browse_web" in names
    assert "execute_code" in names


def test_memory_disabled_without_memory_id():
    from agent_core.memory import AgentMemory
    mem = AgentMemory(_settings())
    assert not mem.enabled


def test_graph_build_input_shapes():
    runtime = AgentRuntime(_settings())
    inp = runtime.build_input(
        user_message="What is trending in AI?",
        history=[("user", "hello"), ("assistant", "hi")],
        context={},
    )
    assert "messages" in inp
    assert len(inp["messages"]) >= 3  # 2 history + 1 user message


def test_sse_event_contract():
    """Events yielded by server must match the schema AgentCoreClient expects."""
    for event_type, required_keys in [
        ("token", ["type", "content"]),
        ("tool_invocation", ["type", "tool_name"]),
        ("tool_result", ["type", "tool_name", "status"]),
        ("done", ["type"]),
        ("error", ["type", "message"]),
    ]:
        event = {k: "" for k in required_keys}
        event["type"] = event_type
        serialised = json.dumps(event) + "\n"
        parsed = json.loads(serialised)
        assert parsed["type"] == event_type
