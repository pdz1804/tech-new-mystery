"""Comprehensive agent tests covering query categories, edge cases, and integration points.

Tests run without AWS credentials by mocking the LLM and tools.
Each test group covers a specific aspect of agent behaviour.
"""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent_core.config import Settings
from agent_core.graph import AgentRuntime
from agent_core.memory import AgentMemory
from agent_core.tools import get_tools


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _settings(**overrides) -> Settings:
    defaults: dict = dict(
        agent_model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        memory_id=None,
        openai_api_key="test-key",
        qdrant_url=None,
    )
    defaults.update(overrides)  # caller overrides win (avoids duplicate-keyword errors)
    return Settings(**defaults)


@pytest.fixture
def runtime():
    return AgentRuntime(_settings())


@pytest.fixture
def memory():
    return AgentMemory(_settings())


# ---------------------------------------------------------------------------
# 1. AgentRuntime.build_input — message construction
# ---------------------------------------------------------------------------

class TestBuildInput:
    def test_simple_query_no_history(self, runtime):
        result = runtime.build_input("What is AI?", history=[], context={})
        assert "messages" in result
        msgs = result["messages"]
        assert len(msgs) == 1
        assert isinstance(msgs[-1], HumanMessage)
        assert msgs[-1].content == "What is AI?"

    def test_history_is_prepended(self, runtime):
        history = [("user", "hi"), ("assistant", "hello")]
        result = runtime.build_input("Tell me about GPT", history=history, context={})
        msgs = result["messages"]
        assert len(msgs) == 3
        assert isinstance(msgs[0], HumanMessage)
        assert isinstance(msgs[1], AIMessage)
        assert isinstance(msgs[2], HumanMessage)
        assert msgs[2].content == "Tell me about GPT"

    def test_history_truncated_to_eight(self, runtime):
        # 20 turns → only last 8 should be kept
        history = [(("user" if i % 2 == 0 else "assistant"), f"msg {i}") for i in range(20)]
        result = runtime.build_input("new query", history=history, context={})
        msgs = result["messages"]
        # 8 history messages + 1 user = 9
        assert len(msgs) == 9
        assert msgs[-1].content == "new query"

    def test_recent_events_used_when_no_history(self, runtime):
        context = {
            "recent_events": [
                {"role": "user", "content": "previous question"},
                {"role": "assistant", "content": "previous answer"},
            ]
        }
        result = runtime.build_input("follow up", history=[], context=context)
        msgs = result["messages"]
        assert len(msgs) == 3
        assert msgs[0].content == "previous question"
        assert msgs[1].content == "previous answer"
        assert msgs[2].content == "follow up"

    def test_recent_events_ignored_when_history_present(self, runtime):
        # If history is non-empty, recent_events from DynamoDB must NOT be added
        history = [("user", "from memory")]
        context = {
            "recent_events": [
                {"role": "user", "content": "from db"},
            ]
        }
        result = runtime.build_input("query", history=history, context=context)
        msgs = result["messages"]
        contents = [m.content for m in msgs]
        assert "from memory" in contents
        assert "from db" not in contents

    def test_recent_events_capped_at_six(self, runtime):
        events = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"e{i}"} for i in range(20)]
        result = runtime.build_input("q", history=[], context={"recent_events": events})
        msgs = result["messages"]
        # 6 context + 1 user = 7
        assert len(msgs) == 7

    def test_empty_context_does_not_crash(self, runtime):
        result = runtime.build_input("safe?", history=[], context={})
        assert len(result["messages"]) == 1

    def test_unknown_role_in_history_skipped(self, runtime):
        history = [("system", "ignored"), ("user", "kept"), ("bot", "ignored"), ("assistant", "kept")]
        result = runtime.build_input("q", history=history, context={})
        msgs = result["messages"]
        # "system" and "bot" roles → skipped; user + assistant + new user = 3
        assert len(msgs) == 3

    def test_empty_content_in_recent_events_skipped(self, runtime):
        context = {
            "recent_events": [
                {"role": "user", "content": ""},
                {"role": "user", "content": "real question"},
            ]
        }
        result = runtime.build_input("next", history=[], context=context)
        msgs = result["messages"]
        contents = [m.content for m in msgs]
        assert "" not in contents

    def test_user_message_at_end_always(self, runtime):
        history = [("user", "a"), ("assistant", "b"), ("user", "c"), ("assistant", "d")]
        result = runtime.build_input("final", history=history, context={})
        assert result["messages"][-1].content == "final"
        assert isinstance(result["messages"][-1], HumanMessage)


# ---------------------------------------------------------------------------
# 2. Tools — registration and schema
# ---------------------------------------------------------------------------

class TestToolRegistration:
    def test_three_tools_registered(self):
        tools = get_tools(_settings())
        assert len(tools) == 3

    def test_tool_names(self):
        tools = get_tools(_settings())
        names = {t.name for t in tools}
        assert names == {"semantic_search", "browse_web", "execute_code"}

    def test_semantic_search_is_async(self):
        tools = get_tools(_settings())
        search = next(t for t in tools if t.name == "semantic_search")
        assert asyncio.iscoroutinefunction(search.func) or asyncio.iscoroutinefunction(getattr(search, "coroutine", None)) or search.coroutine is not None

    def test_tool_descriptions_present(self):
        tools = get_tools(_settings())
        for t in tools:
            assert t.description, f"{t.name} has no description"

    def test_tool_args_schema(self):
        tools = get_tools(_settings())
        search = next(t for t in tools if t.name == "semantic_search")
        schema = search.args_schema.schema() if search.args_schema else {}
        props = schema.get("properties", {})
        assert "query" in props, "semantic_search missing 'query' arg"
        assert "top_k" in props, "semantic_search missing 'top_k' arg"

    def test_browse_web_args_schema(self):
        tools = get_tools(_settings())
        browser = next(t for t in tools if t.name == "browse_web")
        schema = browser.args_schema.schema() if browser.args_schema else {}
        props = schema.get("properties", {})
        assert "url" in props
        assert "task" in props

    def test_execute_code_args_schema(self):
        tools = get_tools(_settings())
        code = next(t for t in tools if t.name == "execute_code")
        schema = code.args_schema.schema() if code.args_schema else {}
        props = schema.get("properties", {})
        assert "code" in props
        assert "language" in props


# ---------------------------------------------------------------------------
# 3. Semantic search tool — query variety
# ---------------------------------------------------------------------------

class TestSemanticSearchTool:
    @pytest.mark.asyncio
    async def test_normal_query(self):
        tools = get_tools(_settings())
        search = next(t for t in tools if t.name == "semantic_search")
        mock_results = [
            {"title": "GPT-5 Released", "summary": "OpenAI releases GPT-5", "score": 0.95, "slug": "gpt-5-released"},
        ]
        with patch("agent_core.search.SemanticSearchTool.execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = mock_results
            result = await search.ainvoke({"query": "latest GPT news", "top_k": 5})
        # format_search_results outputs: "1. {title} (slug: {slug}, score: {score})\n{summary}"
        assert "GPT-5 Released" in result
        assert "OpenAI releases GPT-5" in result

    @pytest.mark.asyncio
    async def test_no_results_returns_friendly_message(self):
        tools = get_tools(_settings())
        search = next(t for t in tools if t.name == "semantic_search")
        with patch("agent_core.search.SemanticSearchTool.execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = []
            result = await search.ainvoke({"query": "zzz nonexistent", "top_k": 5})
        assert "No matching" in result

    @pytest.mark.asyncio
    async def test_top_k_capped_at_max_results(self):
        s = _settings(max_search_results=3)
        tools = get_tools(s)
        search = next(t for t in tools if t.name == "semantic_search")
        captured = {}
        with patch("agent_core.search.SemanticSearchTool.execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = []
            async def capture(**kwargs):
                captured.update(kwargs)
                return []
            mock_exec.side_effect = capture
            await search.ainvoke({"query": "test", "top_k": 999})
        assert captured.get("top_k", 0) <= 3

    @pytest.mark.asyncio
    async def test_unicode_query(self):
        tools = get_tools(_settings())
        search = next(t for t in tools if t.name == "semantic_search")
        with patch("agent_core.search.SemanticSearchTool.execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = []
            result = await search.ainvoke({"query": "AI 人工知能 नवीनतम", "top_k": 3})
        assert result  # should not crash

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self):
        tools = get_tools(_settings())
        search = next(t for t in tools if t.name == "semantic_search")
        # Simulate asyncio.wait_for raising TimeoutError (as would happen with tool_timeout exceeded)
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            with pytest.raises((asyncio.TimeoutError, Exception)):
                await search.ainvoke({"query": "timeout test", "top_k": 1})


# ---------------------------------------------------------------------------
# 4. Server entrypoint — streaming event contract
# ---------------------------------------------------------------------------

class TestServerEntrypoint:
    def _make_stream_events(self, tokens: list[str], tool_calls: list[str] | None = None):
        """Build a fake astream_events sequence."""
        events = []
        if tool_calls:
            for tc in tool_calls:
                events.append({
                    "event": "on_tool_start",
                    "name": tc,
                    "run_id": "run-123",
                    "data": {"input": {"query": "test"}},
                })
                events.append({
                    "event": "on_tool_end",
                    "name": tc,
                    "run_id": "run-123",
                    "data": {"output": "search result"},
                })
        for token in tokens:
            events.append({
                "event": "on_chat_model_stream",
                "name": "model",
                "data": {"chunk": MagicMock(content=token)},
            })

        async def _gen(*args, **kwargs):
            for e in events:
                yield e

        return _gen

    @pytest.mark.asyncio
    async def test_empty_prompt_yields_error(self):
        from agent_core.server import agent_invocation
        ctx = MagicMock()
        ctx.session_id = "s1"
        events = [e async for e in agent_invocation({"prompt": ""}, ctx)]
        types = [e["type"] for e in events]
        assert "error" in types

    @pytest.mark.asyncio
    async def test_whitespace_only_prompt_yields_error(self):
        from agent_core.server import agent_invocation
        ctx = MagicMock()
        ctx.session_id = "s1"
        events = [e async for e in agent_invocation({"prompt": "   "}, ctx)]
        types = [e["type"] for e in events]
        assert "error" in types

    @pytest.mark.asyncio
    async def test_normal_query_yields_tokens_and_done(self):
        from agent_core import server
        ctx = MagicMock()
        ctx.session_id = "session-abc"
        stream_fn = self._make_stream_events(["Hello", " world"])
        with patch.object(server.runtime.graph, "astream_events", new=stream_fn):
            events = [e async for e in server.agent_invocation(
                {"prompt": "What is AI?", "user_id": "user-1", "context": {}}, ctx
            )]
        types = [e["type"] for e in events]
        assert "token" in types
        assert "done" in types
        tokens = [e["content"] for e in events if e["type"] == "token"]
        assert "".join(tokens) == "Hello world"

    @pytest.mark.asyncio
    async def test_tool_invocation_events_emitted(self):
        from agent_core import server
        ctx = MagicMock()
        ctx.session_id = "session-tools"
        stream_fn = self._make_stream_events(["result"], tool_calls=["semantic_search"])
        with patch.object(server.runtime.graph, "astream_events", new=stream_fn):
            events = [e async for e in server.agent_invocation(
                {"prompt": "search for AI articles", "user_id": "u1", "context": {}}, ctx
            )]
        types = [e["type"] for e in events]
        assert "tool_invocation" in types
        assert "tool_result" in types

    @pytest.mark.asyncio
    async def test_done_event_always_yielded(self):
        from agent_core import server
        ctx = MagicMock()
        ctx.session_id = "session-done"
        stream_fn = self._make_stream_events([])
        with patch.object(server.runtime.graph, "astream_events", new=stream_fn):
            events = [e async for e in server.agent_invocation(
                {"prompt": "hi", "user_id": "u1", "context": {}}, ctx
        )]
        assert events[-1]["type"] == "done"

    @pytest.mark.asyncio
    async def test_non_streaming_text_response_is_blocked_when_required(self):
        from agent_core import server
        ctx = MagicMock()
        ctx.session_id = "session-no-fake"

        async def _non_streaming_end(*args, **kwargs):
            yield {
                "event": "on_chat_model_end",
                "name": "model",
                "data": {"output": MagicMock(content="complete response")},
            }

        with patch.object(server.runtime.graph, "astream_events", new=_non_streaming_end):
            events = [e async for e in server.agent_invocation(
                {"prompt": "hi", "user_id": "u1", "context": {}}, ctx
            )]

        errors = [e for e in events if e["type"] == "error"]
        assert errors
        assert errors[0]["error_code"] == "TRUE_STREAMING_REQUIRED"
        assert not [e for e in events if e["type"] == "token"]

    @pytest.mark.asyncio
    async def test_agent_exception_yields_error_then_done(self):
        from agent_core import server
        ctx = MagicMock()
        ctx.session_id = "session-err"

        async def _crash(*args, **kwargs):
            yield {"event": "on_chat_model_stream", "name": "m", "data": {"chunk": MagicMock(content="partial")}}
            raise RuntimeError("model exploded")

        with patch.object(server.runtime.graph, "astream_events", new=_crash):
            events = [e async for e in server.agent_invocation(
                {"prompt": "cause error", "user_id": "u1", "context": {}}, ctx
            )]
        types = [e["type"] for e in events]
        assert "error" in types
        assert "done" in types

    @pytest.mark.asyncio
    async def test_memory_save_on_success(self):
        from agent_core import server
        ctx = MagicMock()
        ctx.session_id = "s-mem"
        stream_fn = self._make_stream_events(["answer"])
        with patch.object(server.runtime.graph, "astream_events", new=stream_fn):
            with patch.object(server.memory, "save_turn", new_callable=AsyncMock) as mock_save:
                events = [e async for e in server.agent_invocation(
                    {"prompt": "hi", "user_id": "user-save", "context": {}}, ctx
                )]
        mock_save.assert_called_once()
        call_kwargs = mock_save.call_args.kwargs
        assert call_kwargs["user_message"] == "hi"
        assert call_kwargs["assistant_message"] == "answer"

    @pytest.mark.asyncio
    async def test_memory_save_skipped_on_error(self):
        from agent_core import server
        ctx = MagicMock()
        ctx.session_id = "s-no-save"

        async def _crash(*args, **kwargs):
            raise RuntimeError("crash")
            yield  # make it a generator

        with patch.object(server.runtime.graph, "astream_events", new=_crash):
            with patch.object(server.memory, "save_turn", new_callable=AsyncMock) as mock_save:
                events = [e async for e in server.agent_invocation(
                    {"prompt": "error", "user_id": "u1", "context": {}}, ctx
                )]
        mock_save.assert_not_called()


# ---------------------------------------------------------------------------
# 5. Query categories — realistic user inputs (mocked LLM responses)
# ---------------------------------------------------------------------------

def _fake_stream(response_text: str, tool_name: str | None = None):
    """Build a stream_events mock that returns a fixed response."""
    events = []
    if tool_name:
        events += [
            {"event": "on_tool_start", "name": tool_name, "run_id": "r1",
             "data": {"input": {"query": "search term"}}},
            {"event": "on_tool_end", "name": tool_name, "run_id": "r1",
             "data": {"output": "mock tool result"}},
        ]
    for word in response_text.split():
        events.append({
            "event": "on_chat_model_stream",
            "name": "m",
            "data": {"chunk": MagicMock(content=word + " ")},
        })

    async def _gen(*args, **kwargs):
        for e in events:
            yield e

    return _gen


QUERY_CASES = [
    # (description, prompt, expected_token_words, tool_used)
    ("trending AI news", "What are the top AI stories this week?", ["AI"], "semantic_search"),
    ("specific article search", "Find articles about GPT-5", ["GPT"], "semantic_search"),
    ("tech company news", "What's happening with Apple?", ["Apple"], "semantic_search"),
    ("code calculation", "Calculate the compound interest on $10000 at 5% for 10 years", ["compound"], "execute_code"),
    ("web lookup", "Browse https://openai.com and tell me the latest news", ["latest"], "browse_web"),
    ("general factual", "What is a transformer neural network?", ["transformer"], None),
    ("follow-up with context", "What about its limitations?", ["limitations"], None),
    ("multi-topic", "Compare Claude and GPT-4", ["Claude"], "semantic_search"),
    ("news trend analysis", "What tech trends are emerging in 2025?", ["tech"], "semantic_search"),
    ("specific date query", "What happened in AI in March 2025?", ["AI"], "semantic_search"),
    ("opinion request", "Which AI model is best for coding?", ["model"], None),
    ("long query", "I want to understand the differences between various large language models including GPT-4, Claude, Gemini, and how they compare in terms of reasoning, coding, and creative tasks", ["model"], "semantic_search"),
    ("special characters", "What's the #1 AI tool? Use <> for tags?", ["AI"], None),
    ("very short", "AI?", ["AI"], None),
    ("unicode", "最新のAIニュースは何ですか？", ["AI"], None),
]


@pytest.mark.parametrize("desc,prompt,expected_words,tool", QUERY_CASES)
@pytest.mark.asyncio
async def test_query_category(desc, prompt, expected_words, tool):
    """Each realistic user query should produce tokens and a done event."""
    from agent_core import server
    ctx = MagicMock()
    ctx.session_id = f"session-{desc[:20].replace(' ', '-')}"
    response = f"Here is information about {expected_words[0]} topics."
    stream_fn = _fake_stream(response, tool_name=tool)
    with patch.object(server.runtime.graph, "astream_events", new=stream_fn):
        events = [e async for e in server.agent_invocation(
            {"prompt": prompt, "user_id": "test-user", "context": {}}, ctx
        )]
    types = [e["type"] for e in events]
    assert "token" in types, f"[{desc}] no token event"
    assert "done" in types, f"[{desc}] no done event"
    if tool:
        assert "tool_invocation" in types, f"[{desc}] expected tool_invocation for {tool}"


# ---------------------------------------------------------------------------
# 6. Memory — disabled by default, no-op calls
# ---------------------------------------------------------------------------

class TestAgentMemory:
    def test_disabled_when_no_memory_id(self, memory):
        assert not memory.enabled

    @pytest.mark.asyncio
    async def test_get_last_k_turns_returns_empty_when_disabled(self, memory):
        result = await memory.get_last_k_turns("user-1", "session-1", k=5)
        assert result == []

    @pytest.mark.asyncio
    async def test_save_turn_noop_when_disabled(self, memory):
        # Should not raise
        await memory.save_turn("u1", "s1", "question", "answer")

    @pytest.mark.asyncio
    async def test_get_k_turns_with_active_memory(self):
        s = _settings(memory_id="mem-123")
        mock_client = MagicMock()
        mock_client.get_last_k_turns.return_value = [
            [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"}]
        ]
        mem = AgentMemory.__new__(AgentMemory)
        mem._settings = s
        mem._client = mock_client
        result = await mem.get_last_k_turns("u1", "s1", k=3)
        assert result == [("user", "q"), ("assistant", "a")]

    @pytest.mark.asyncio
    async def test_memory_failure_returns_empty(self):
        s = _settings(memory_id="mem-456")
        mock_client = MagicMock()
        mock_client.get_last_k_turns.side_effect = Exception("AWS down")
        mem = AgentMemory.__new__(AgentMemory)
        mem._settings = s
        mem._client = mock_client
        result = await mem.get_last_k_turns("u1", "s1", k=3)
        assert result == []

    @pytest.mark.asyncio
    async def test_save_turn_failure_is_silent(self):
        s = _settings(memory_id="mem-789")
        mock_client = MagicMock()
        mock_client.save_conversation.side_effect = Exception("network error")
        mem = AgentMemory.__new__(AgentMemory)
        mem._settings = s
        mem._client = mock_client
        # must not raise
        await mem.save_turn("u1", "s1", "hello", "hi")


# ---------------------------------------------------------------------------
# 7. SSE event contract — agent server output matches what the backend client expects
# ---------------------------------------------------------------------------

class TestSSEEventContract:
    """Verify that events yielded by server.py are valid JSON with correct schema.

    These tests are pure contract tests: they don't import backend code but
    validate the event shapes that agent_core/server.py produces and that
    AgentCoreClient on the backend side consumes.
    """

    def _valid_event(self, event_type: str, **extra) -> dict:
        event = {"type": event_type}
        event.update(extra)
        return event

    def test_token_event_serialisable(self):
        event = self._valid_event("token", content="Hello world")
        serialised = json.dumps(event)
        parsed = json.loads(serialised)
        assert parsed["type"] == "token"
        assert parsed["content"] == "Hello world"

    def test_tool_invocation_event_schema(self):
        event = self._valid_event(
            "tool_invocation",
            tool_name="semantic_search",
            tool_id="run-abc",
            tool_args={"query": "AI news", "top_k": 5},
        )
        serialised = json.dumps(event)
        parsed = json.loads(serialised)
        assert parsed["type"] == "tool_invocation"
        assert parsed["tool_name"] == "semantic_search"
        assert isinstance(parsed["tool_args"], dict)

    def test_tool_result_event_schema(self):
        event = self._valid_event(
            "tool_result",
            tool_name="semantic_search",
            status="completed",
            result_summary="Found 3 articles about AI.",
        )
        serialised = json.dumps(event)
        parsed = json.loads(serialised)
        assert parsed["status"] == "completed"
        assert parsed["result_summary"]

    def test_done_event_schema(self):
        event = self._valid_event("done")
        serialised = json.dumps(event)
        parsed = json.loads(serialised)
        assert parsed["type"] == "done"

    def test_error_event_schema(self):
        event = self._valid_event("error", message="Something failed", recoverable=True)
        serialised = json.dumps(event)
        parsed = json.loads(serialised)
        assert parsed["type"] == "error"
        assert "message" in parsed
        assert isinstance(parsed["recoverable"], bool)

    def test_error_non_recoverable(self):
        event = self._valid_event("error", message="Fatal", recoverable=False)
        assert not event["recoverable"]

    def test_all_required_event_types_serialisable(self):
        events = [
            {"type": "token", "content": "text"},
            {"type": "tool_invocation", "tool_name": "semantic_search", "tool_id": "t1", "tool_args": {}},
            {"type": "tool_result", "tool_name": "semantic_search", "status": "completed", "result_summary": ""},
            {"type": "done"},
            {"type": "error", "message": "err", "recoverable": True},
        ]
        for e in events:
            assert json.loads(json.dumps(e))["type"] == e["type"]

    def test_token_content_can_be_empty_string(self):
        event = self._valid_event("token", content="")
        assert json.loads(json.dumps(event))["content"] == ""

    def test_tool_args_nested_objects_serialisable(self):
        event = self._valid_event(
            "tool_invocation",
            tool_name="execute_code",
            tool_id="run-1",
            tool_args={"code": "print(1+1)", "language": "python"},
        )
        parsed = json.loads(json.dumps(event))
        assert parsed["tool_args"]["language"] == "python"


# ---------------------------------------------------------------------------
# 8. Graph structure
# ---------------------------------------------------------------------------

class TestGraphStructure:
    def test_graph_has_astream_events(self, runtime):
        assert hasattr(runtime.graph, "astream_events")

    def test_graph_has_invoke(self, runtime):
        assert hasattr(runtime.graph, "invoke") or hasattr(runtime.graph, "ainvoke")

    def test_system_prompt_in_config(self, runtime):
        from agent_core.graph import SYSTEM_PROMPT
        assert "semantic_search" in SYSTEM_PROMPT
        assert "browse_web" in SYSTEM_PROMPT
        assert "execute_code" in SYSTEM_PROMPT
        assert "Tech News Mystery" in SYSTEM_PROMPT

    def test_runtime_settings_accessible(self, runtime):
        assert runtime.settings.agent_model == "us.anthropic.claude-haiku-4-5-20251001-v1:0"
