"""LangGraph ReAct agent backed by AWS Bedrock Converse.

Uses langgraph.prebuilt.create_react_agent with astream_events for
real token-level streaming. Conversation history is passed explicitly
from AgentMemory (AWS Bedrock AgentCore Memory) and/or from the
DynamoDB-backed recent_events injected by the backend.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from agent_core.config import Settings
from agent_core.tools import get_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Tech News Mystery assistant — an expert analyst of technology news.

You have access to three tools:
1. **semantic_search** — searches a curated internal database of tech news articles.
2. **browse_web** — browses live web pages (including Google Search) for real-time information.
3. **execute_code** — runs Python in an AWS-managed sandbox for data analysis or calculations.

Decision rules — follow these in order:
1. For any question about news, events, people, companies, or trends: call semantic_search first.
2. If semantic_search returns "No matching articles found" or fewer than 2 relevant results:
   - Immediately call browse_web to search the web. Use DuckDuckGo HTML (not Google):
     https://html.duckduckgo.com/html/?q=<URL-encoded+query>
   - Extract the answer from the search results page.
3. For a specific URL the user provides: call browse_web directly on that URL.
4. For calculations or data processing: use execute_code.

Never tell the user you couldn't find information without first trying browse_web.
Always cite sources (article title, URL, or website name). Be concise and factual."""


class AgentRuntime:
    """Wrapper around the compiled LangGraph ReAct agent."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._graph = self._build()

    def _build(self):
        llm = ChatBedrockConverse(
            model=self.settings.agent_model,
            region_name=self.settings.bedrock_region,
            temperature=0.2,
            max_tokens=2048,
            # ChatBedrockConverse does not accept streaming=True. LangChain uses
            # .astream/.astream_events to select ConverseStream when streaming is
            # enabled; this makes that behavior explicit for tool-bound agents.
            disable_streaming=False,
        )
        self._llm = llm
        tools = get_tools(self.settings)
        # Bind system prompt to the LLM
        from langchain_core.messages import SystemMessage
        llm_with_prompt = llm.bind(
            system=SYSTEM_PROMPT
        )
        # Create ReAct agent with system-prompt-bound LLM
        graph = create_react_agent(llm_with_prompt, tools)
        logger.info(
            "[AGENT] ReAct graph built — model=%s tools=%s",
            self.settings.agent_model,
            [t.name for t in tools],
        )
        return graph

    @property
    def graph(self):
        return self._graph

    @property
    def streaming_diagnostics(self) -> dict[str, Any]:
        """Return the LLM streaming settings used by the running agent."""
        llm = getattr(self, "_llm", None)
        return {
            "model": self.settings.agent_model,
            "bedrock_region": self.settings.bedrock_region,
            "llm_class": type(llm).__name__ if llm is not None else None,
            "disable_streaming": getattr(llm, "disable_streaming", None),
            "require_true_streaming": self.settings.require_true_streaming,
        }

    def build_input(
        self,
        user_message: str,
        history: list[tuple[str, str]],
        context: dict[str, Any],
    ) -> dict:
        """Build LangGraph input from history + context + current message."""
        messages = []

        # History from AgentCore Memory (long-term, cross-session)
        for role, content in history[-8:]:
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        # recent_events from DynamoDB (short-term, current session) — used when
        # AgentCore Memory is disabled or history is empty
        if not history:
            for event in context.get("recent_events", [])[-6:]:
                role = event.get("role", "user")
                content = event.get("content", "")
                if content:
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_message))
        return {"messages": messages}
