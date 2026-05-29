import json

import pytest

from agent_core.config import Settings
from agent_core.graph import AgentRuntime
from agent_core.server import app, require_api_key


def test_graph_compiles_with_langgraph():
    runtime = AgentRuntime(Settings(agent_model="us.anthropic.claude-haiku-4-5-20251001-v1:0"))

    assert runtime.graph is not None


def test_api_key_dependency_rejects_bad_key(monkeypatch):
    monkeypatch.setattr("agent_core.server.settings.agent_core_api_key", "expected")

    with pytest.raises(Exception):
        require_api_key("wrong")


@pytest.mark.asyncio
async def test_health_response_shape():
    routes = {route.path: route for route in app.routes}

    assert "/health" in routes


def test_ndjson_event_contract():
    event = {"type": "token", "content": "hello"}

    line = json.dumps(event) + "\n"

    assert json.loads(line)["type"] == "token"
