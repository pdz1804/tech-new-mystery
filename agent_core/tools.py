"""LangChain tools backed by AWS Bedrock AgentCore managed services.

Tools:
  semantic_search   — Qdrant vector search over the article corpus
  browse_web        — AWS Bedrock AgentCore Browser (Playwright/CDP)
  execute_code      — AWS Bedrock AgentCore Code Interpreter
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from langchain_core.tools import tool

from agent_core.config import Settings
from agent_core.search import SemanticSearchTool, format_search_results

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Semantic search (Qdrant)
# ---------------------------------------------------------------------------

def _make_search_tool(settings: Settings):
    searcher = SemanticSearchTool(settings)

    @tool
    async def semantic_search(query: str, top_k: int = 5) -> str:
        """Search the tech-news article database for articles relevant to the query.

        Use this tool whenever the user asks about news, articles, recent events,
        trends, or any topic that may be covered in the article corpus.

        Args:
            query: The natural-language search query.
            top_k: Maximum number of articles to return (default 5, max 10).
        """
        top_k = min(top_k, settings.max_search_results)
        results = await asyncio.wait_for(
            searcher.execute(query=query, top_k=top_k, min_score=0.0),
            timeout=settings.tool_timeout,
        )
        return format_search_results(results) or "No matching articles found."

    return semantic_search


# ---------------------------------------------------------------------------
# Browser (AWS Bedrock AgentCore Browser via Playwright CDP)
# ---------------------------------------------------------------------------

def _make_browser_tool(settings: Settings):
    @tool
    def browse_web(url: str, task: str) -> str:
        """Navigate to a URL using an AWS-managed browser and extract content.

        Use this tool to fetch live web pages, check current events, or verify
        information from the internet.

        Args:
            url: The full URL to navigate to (must include https://).
            task: A description of what information to extract from the page.
        """
        try:
            from bedrock_agentcore.tools.browser_client import browser_session
            from playwright.sync_api import sync_playwright

            logger.info("[BROWSER] Starting session for %s", url)
            with browser_session(region=settings.aws_region) as browser:
                ws_url, headers = browser.generate_ws_headers()
                logger.debug("[BROWSER] CDP endpoint: %s", ws_url)

                with sync_playwright() as pw:
                    chrome = pw.chromium.connect_over_cdp(
                        ws_url,
                        headers=headers,
                        timeout=settings.browser_timeout * 1000,
                    )
                    page = chrome.new_page()
                    page.goto(url, timeout=settings.browser_timeout * 1000, wait_until="domcontentloaded")
                    title = page.title()
                    # Extract readable text (strip scripts/styles)
                    body_text = page.evaluate("""() => {
                        const clone = document.body.cloneNode(true);
                        clone.querySelectorAll('script,style,nav,footer,header,aside').forEach(e => e.remove());
                        return clone.innerText;
                    }""")
                    chrome.close()

            # Trim to reasonable length
            content = body_text.strip()[:6000]
            return f"Title: {title}\n\nContent:\n{content}"

        except ImportError:
            return "[Browser tool unavailable: playwright not installed]"
        except Exception as exc:
            logger.error("[BROWSER] Error browsing %s: %s", url, exc)
            return f"[Browser error: {exc}]"

    return browse_web


# ---------------------------------------------------------------------------
# Code Interpreter (AWS Bedrock AgentCore Code Interpreter)
# ---------------------------------------------------------------------------

def _make_code_interpreter_tool(settings: Settings):
    @tool
    def execute_code(code: str, language: str = "python") -> str:
        """Execute code in an AWS-managed sandbox and return the output.

        Use this tool for calculations, data analysis, processing results,
        generating charts, or any computation that requires code execution.

        Args:
            code: The code to execute.
            language: Programming language — 'python' (default) or 'javascript'.
        """
        try:
            from bedrock_agentcore.tools.code_interpreter_client import code_session

            logger.info("[CODE] Executing %s code (%d chars)", language, len(code))
            with code_session(region=settings.aws_region) as interp:
                result = interp.execute_code(
                    code=code,
                    language=language,
                    clear_context=False,
                )

            output_parts = []
            if result.get("output"):
                output_parts.append(result["output"])
            if result.get("error"):
                output_parts.append(f"Error: {result['error']}")
            if result.get("stdout"):
                output_parts.append(result["stdout"])
            if result.get("stderr"):
                output_parts.append(f"Stderr: {result['stderr']}")

            return "\n".join(output_parts).strip() or "(no output)"

        except Exception as exc:
            logger.error("[CODE] Execution error: %s", exc)
            return f"[Code execution error: {exc}]"

    return execute_code


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_tools(settings: Settings) -> list:
    """Return the list of LangChain tools for the ReAct agent."""
    return [
        _make_search_tool(settings),
        _make_browser_tool(settings),
        _make_code_interpreter_tool(settings),
    ]
