"""LangGraph ReAct agent backed by AWS Bedrock Converse.

Uses langgraph.prebuilt.create_react_agent which provides:
  - Automatic tool-calling loop (ReAct pattern)
  - Compatible with astream_events() for token-level streaming
  - Works with any ChatModel that supports tool calling
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langgraph.prebuilt import create_react_agent

from agent_core.config import Settings
from agent_core.tools import get_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Tech News Mystery assistant — an expert analyst of technology news.

You have access to three tools:
1. **semantic_search** — searches a curated database of tech news articles. Always try this first for tech-related questions.
2. **browse_web** — browses live web pages via an AWS-managed browser for real-time information.
3. **execute_code** — runs Python or JavaScript in an AWS-managed sandbox for computations and analysis.

Guidelines:
- For questions about articles, tech trends, or recent news: use semantic_search first.
- For real-time information or URLs: use browse_web.
- For calculations, data processing, or code examples: use execute_code.
- Cite article titles and sources when referencing search results.
- Be concise and factual. Say when you don't have enough information.
- You can use multiple tools in a single response if needed."""


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
        )
        tools = get_tools(self.settings)
        graph = create_react_agent(llm, tools, state_modifier=SYSTEM_PROMPT)
        logger.info("[AGENT] ReAct graph built — model=%s tools=%s",
                    self.settings.agent_model, [t.name for t in tools])
        return graph

    @property
    def graph(self):
        return self._graph

    def build_input(
        self,
        user_message: str,
        history: list[tuple[str, str]],
        context: dict[str, Any],
    ) -> dict:
        """Construct the LangGraph input dict from current message and history."""
        messages: list[BaseMessage] = []

        # Add recent conversation history from AWS memory / DynamoDB context
        for role, content in history[-8:]:
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

        # Inject recent_events from request context (DynamoDB-backed short-term memory)
        recent_events = context.get("recent_events", [])
        if recent_events and not history:
            for event in recent_events[-6:]:
                role = event.get("role", "user")
                content = event.get("content", "")
                if content:
                    if role == "user":
                        messages.append(HumanMessage(content=content))
                    elif role == "assistant":
                        messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_message))
        return {"messages": messages}
