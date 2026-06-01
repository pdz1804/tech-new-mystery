"""LangChain tools backed by AWS Bedrock AgentCore managed services.

Tools:
  semantic_search   — Qdrant vector search over the article corpus
  browse_web        — AWS Bedrock AgentCore Browser (Playwright/CDP)
  execute_code      — AWS Bedrock AgentCore Code Interpreter
"""

from __future__ import annotations

import asyncio
import base64
from html.parser import HTMLParser
import json
import logging
import mimetypes
import re
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from typing import Optional

from langchain_core.tools import tool

from agent_core.config import Settings
from agent_core.search import SemanticSearchTool, format_search_results

logger = logging.getLogger(__name__)


class _ReadableTextParser(HTMLParser):
    """Small HTML-to-text parser used when managed browser CDP is unavailable."""

    def __init__(self) -> None:
        super().__init__()
        self._skip = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "nav", "footer", "header", "aside"}:
            self._skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "nav", "footer", "header", "aside"}:
            self._skip = False

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self.parts.append(data.strip())

    @property
    def text(self) -> str:
        return re.sub(r"\s+", " ", " ".join(self.parts)).strip()


def _json_result(**payload) -> str:
    """Return compact JSON so tools, UI, and Langfuse can parse results."""
    return json.dumps(payload, ensure_ascii=True)


def _safe_url(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _fallback_fetch_url(url: str, timeout: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(1_000_000)
        content_type = response.headers.get("content-type", "")
    text = raw.decode("utf-8", errors="ignore")
    if "html" not in content_type.lower():
        return text[:6000]
    parser = _ReadableTextParser()
    parser.feed(text)
    return parser.text[:6000]


def _browser_session_summary(client) -> dict:
    """Return sanitized AgentCore Browser session metadata."""
    try:
        session = client.get_session()
    except Exception as exc:
        return {"session_error": f"{type(exc).__name__}: {exc}"}

    streams = session.get("streams") or {}
    automation = streams.get("automationStream") or {}
    live_view = streams.get("liveViewStream") or {}
    return {
        "session_id": session.get("sessionId"),
        "browser_identifier": session.get("browserIdentifier"),
        "status": session.get("status"),
        "automation_stream_status": automation.get("streamStatus"),
        "has_automation_endpoint": bool(automation.get("streamEndpoint")),
        "has_live_view_endpoint": bool(live_view.get("streamEndpoint")),
    }


def _wait_for_browser_ready(client, timeout_seconds: int = 30) -> dict:
    """Poll AgentCore Browser until the session reports READY."""
    deadline = time.monotonic() + timeout_seconds
    last_summary = _browser_session_summary(client)

    while time.monotonic() < deadline:
        last_summary = _browser_session_summary(client)
        if last_summary.get("status") == "READY":
            return last_summary
        if last_summary.get("status") == "TERMINATED":
            raise RuntimeError(f"Browser session terminated before use: {last_summary}")
        time.sleep(1)

    raise TimeoutError(f"Browser session did not become READY: {last_summary}")


def _summarize_code_result(result: dict) -> tuple[str, list[str]]:
    """Extract readable code output and candidate artifact paths."""
    output_parts = []
    artifact_paths: list[str] = []

    def visit(value):
        if isinstance(value, dict):
            for key, item in value.items():
                lowered = str(key).lower()
                if lowered in {"output", "stdout", "stderr", "error", "text"} and item:
                    output_parts.append(f"{key}: {item}")
                if lowered in {"path", "file", "filename"} and isinstance(item, str):
                    artifact_paths.append(item)
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, str):
            for match in re.findall(r"(?:(?:/tmp|output|outputs|mnt/data)[/\w.-]+|[\w.-]+\.(?:png|jpg|jpeg|gif|webp|svg|csv|json|txt|html))", value):
                artifact_paths.append(match)

    visit(result)
    summary = "\n".join(str(part) for part in output_parts if str(part).strip())
    return summary.strip() or str(result)[:4000], list(dict.fromkeys(artifact_paths))


def _artifact_to_data_url(interpreter, path: str) -> dict | None:
    """Download a small generated file and convert it to a chat-viewable artifact."""
    try:
        content = interpreter.download_file(path)
    except Exception as exc:
        logger.debug("[CODE] Could not download artifact %s: %s", path, exc)
        return None

    mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if isinstance(content, str):
        raw = content.encode("utf-8")
    else:
        raw = content
    if len(raw) > 200_000:
        return {
            "name": path.rsplit("/", 1)[-1],
            "path": path,
            "mime_type": mime_type,
            "too_large": True,
        }

    return {
        "name": path.rsplit("/", 1)[-1],
        "path": path,
        "mime_type": mime_type,
        "data_url": f"data:{mime_type};base64,{base64.b64encode(raw).decode('ascii')}",
    }


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
        browser_identifier = settings.browser_id or settings.browser_identifier
        safe_url = _safe_url(url)
        try:
            from bedrock_agentcore.tools.browser_client import BrowserClient
            from playwright.sync_api import sync_playwright

            logger.info(
                "[BROWSER] Starting session region=%s identifier=%s url=%s",
                settings.aws_region,
                browser_identifier,
                safe_url,
            )
            browser_client = BrowserClient(settings.aws_region)
            try:
                browser_client.start(
                    identifier=browser_identifier,
                    name="tech-news-agent-browser",
                    viewport={"width": 1365, "height": 900},
                    session_timeout_seconds=900,
                )
                session_summary = _wait_for_browser_ready(browser_client)

                try:
                    browser_client.update_stream("ENABLED")
                except Exception as exc:
                    logger.warning("[BROWSER] Could not force automation stream enabled: %s", exc)

                chrome = None
                last_connect_error: Exception | None = None
                with sync_playwright() as pw:
                    for attempt in range(1, 4):
                        ws_url, headers = browser_client.generate_ws_headers()
                        logger.debug(
                            "[BROWSER] Connecting CDP attempt=%d host=%s session=%s",
                            attempt,
                            urlparse(ws_url).netloc,
                            session_summary.get("session_id"),
                        )
                        try:
                            chrome = pw.chromium.connect_over_cdp(
                                ws_url,
                                headers=headers,
                                timeout=settings.browser_timeout * 1000,
                            )
                            break
                        except Exception as exc:
                            last_connect_error = exc
                            session_summary = _browser_session_summary(browser_client)
                            logger.warning(
                                "[BROWSER] CDP connect attempt=%d failed session=%s status=%s stream=%s error=%s",
                                attempt,
                                session_summary.get("session_id"),
                                session_summary.get("status"),
                                session_summary.get("automation_stream_status"),
                                exc,
                            )
                            time.sleep(1.5 * attempt)

                    if chrome is None:
                        raise RuntimeError(f"CDP connection failed after retries: {last_connect_error}")

                    try:
                        context = chrome.contexts[0] if chrome.contexts else chrome.new_context()
                        page = context.pages[0] if context.pages else context.new_page()
                        page.goto(url, timeout=settings.browser_timeout * 1000, wait_until="domcontentloaded")
                        title = page.title()
                        # Extract readable text (strip scripts/styles).
                        body_text = page.evaluate("""() => {
                            const clone = document.body.cloneNode(true);
                            clone.querySelectorAll('script,style,nav,footer,header,aside').forEach(e => e.remove());
                            return clone.innerText;
                        }""")
                    finally:
                        chrome.close()
            finally:
                try:
                    browser_client.stop()
                except Exception as exc:
                    logger.warning("[BROWSER] Could not stop AgentCore browser session: %s", exc)

            # Trim to reasonable length
            content = body_text.strip()[:6000]
            return _json_result(
                status="completed",
                mode="agentcore_browser",
                url=safe_url,
                task=task,
                title=title,
                session=session_summary,
                summary=f"Title: {title}\n\nContent:\n{content}",
            )

        except ImportError:
            return _json_result(
                status="failed",
                mode="agentcore_browser",
                url=safe_url,
                error="Browser tool unavailable: playwright not installed",
            )
        except Exception as exc:
            logger.error(
                "[BROWSER] CDP browsing failed region=%s identifier=%s url=%s error=%s",
                settings.aws_region,
                browser_identifier,
                safe_url,
                exc,
            )
            try:
                content = _fallback_fetch_url(url, timeout=min(settings.browser_timeout, 20))
                return _json_result(
                    status="completed",
                    mode="http_fallback",
                    url=safe_url,
                    task=task,
                    warning=(
                        "Managed AgentCore Browser CDP connection failed; "
                        "used direct HTTP fallback without JavaScript rendering."
                    ),
                    browser_error=type(exc).__name__,
                    summary=content,
                )
            except Exception as fallback_exc:
                return _json_result(
                    status="failed",
                    mode="agentcore_browser",
                    url=safe_url,
                    task=task,
                    region=settings.aws_region,
                    browser_identifier=browser_identifier,
                    error_type=type(exc).__name__,
                    error=str(exc).split("wss://", 1)[0].strip(),
                    fallback_error=str(fallback_exc),
                )

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
        For charts/images, save files to /tmp with a clear extension and print
        the file path so the UI can render downloadable/viewable artifacts.

        Args:
            code: The code to execute.
            language: Programming language — 'python' (default) or 'javascript'.
        """
        try:
            from bedrock_agentcore.tools.code_interpreter_client import code_session

            logger.info("[CODE] Executing %s code (%d chars)", language, len(code))
            with code_session(
                region=settings.aws_region,
                identifier=settings.code_interpreter_id or settings.code_interpreter_identifier,
            ) as interp:
                result = interp.execute_code(
                    code=code,
                    language=language,
                    clear_context=False,
                )

                try:
                    files_result = interp.invoke("listFiles", {})
                    result["files"] = files_result
                except Exception as exc:
                    logger.debug("[CODE] listFiles failed: %s", exc)

                summary, artifact_paths = _summarize_code_result(result)
                artifacts = []
                for path in artifact_paths[:5]:
                    artifact = _artifact_to_data_url(interp, path)
                    if artifact:
                        artifacts.append(artifact)

            return _json_result(
                status="completed",
                language=language,
                summary=summary or "(no output)",
                artifacts=artifacts,
            )

        except Exception as exc:
            logger.error("[CODE] Execution error: %s", exc)
            return _json_result(
                status="failed",
                language=language,
                error_type=type(exc).__name__,
                summary=f"Code execution error: {exc}",
            )

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
