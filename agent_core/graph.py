"""LangGraph-powered agent workflow."""

from __future__ import annotations

import asyncio
import json
from typing import Any, TypedDict, Annotated

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import HumanMessage, SystemMessage, BaseMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from agent_core.config import Settings
from agent_core.search import SemanticSearchTool, format_search_results


class AgentState(TypedDict, total=False):
    """State carried through the LangGraph workflow."""

    session_id: str
    user_id: str | None
    user_message: str
    context: dict[str, Any]
    should_search: bool
    search_results: list[dict[str, Any]]
    messages: Annotated[list[BaseMessage], add_messages]
    answer: str


class AgentRuntime:
    """Runtime that routes requests through LangGraph."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.search_tool = SemanticSearchTool(settings)
        self.llm = ChatBedrockConverse(
            model=settings.agent_model,
            region_name=settings.bedrock_region,
            temperature=0.2,
        )
        self.tools = [
            StructuredTool.from_function(
                coroutine=self.search_tool.execute,
                name=self.search_tool.name,
                description=self.search_tool.description,
            )
        ]
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("route", self._route)
        workflow.add_node("search", self._search)
        workflow.add_node("generate", self._generate)
        
        workflow.set_entry_point("route")
        workflow.add_conditional_edges(
            "route",
            lambda state: "search" if state.get("should_search") else "generate",
            {"search": "search", "generate": "generate"},
        )
        workflow.add_edge("search", "generate")
        workflow.add_edge("generate", END)
        return workflow.compile()

    async def _route(self, state: AgentState) -> dict:
        user_message = state.get("user_message", "")
        # Extract from messages if not provided explicitly
        if not user_message and state.get("messages"):
            last_msg = state["messages"][-1]
            user_message = getattr(last_msg, "content", "") if hasattr(last_msg, "content") else str(last_msg.get("content", ""))
            
        message = str(user_message).lower()
        search_terms = (
            "article",
            "news",
            "recent",
            "latest",
            "source",
            "trend",
            "search",
            "find",
            "about",
        )
        return {"should_search": any(term in message for term in search_terms), "user_message": user_message}

    async def _search(self, state: AgentState) -> dict:
        results = await asyncio.wait_for(
            self.search_tool.execute(
                query=state.get("user_message", ""),
                top_k=min(5, self.settings.max_search_results),
                min_score=0.0,
            ),
            timeout=self.settings.tool_timeout,
        )
        return {"search_results": results}

    async def _generate(self, state: AgentState) -> dict:
        context = state.get("context") or {}
        search_context = format_search_results(state.get("search_results", []))
        messages = [
            SystemMessage(
                content=(
                    "You are the Tech News Mystery agent. Use provided article search "
                    "context when present. Be concise, cite article titles or slugs from "
                    "the context when making factual claims, and say when the index does "
                    "not contain enough evidence."
                )
            ),
            HumanMessage(
                content=(
                    f"Session: {state.get('session_id')}\n"
                    f"User context: {json.dumps(context, default=str)}\n\n"
                    f"Search context:\n{search_context}\n\n"
                    f"User question: {state.get('user_message', '')}"
                )
            ),
        ]

        response = await self.llm.ainvoke(messages)
        return {"answer": str(response.content), "messages": [response]}
