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
    return json.dumps(payload, ensure_ascii=False)


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


# ---------------------------------------------------------------------------
# Code Interpreter helpers
# ---------------------------------------------------------------------------

def _drain_code_stream(response: dict) -> dict:
    """Drain the botocore EventStream and return the last result dict."""
    result: dict = {}
    stream = response.get("stream")
    if stream is None:
        logger.warning("[CODE] No 'stream' key in invoke response: %s", list(response.keys()))
        return result
    try:
        for event in stream:
            if isinstance(event, dict) and "result" in event:
                result = event["result"]
    except Exception as exc:
        logger.error("[CODE] Error draining code interpreter stream: %s", exc, exc_info=True)
    return result


def _parse_code_result(result: dict) -> tuple[str, bool, int]:
    """Return (output_text, is_error, exit_code) from a code interpreter result dict."""
    if not result:
        return "(no output)", False, 0

    is_error = result.get("isError", False)
    structured = result.get("structuredContent") or {}
    stdout = structured.get("stdout", "")
    stderr = structured.get("stderr", "")
    exit_code = structured.get("exitCode", 0)

    # Fall back to content array if structuredContent absent
    if not stdout:
        content_list = result.get("content") or []
        stdout = " ".join(
            item.get("text", "")
            for item in content_list
            if isinstance(item, dict) and item.get("type") == "text"
        )

    output = stdout or ""
    if stderr:
        output += f"\nStderr:\n{stderr}"
    if is_error and not output.strip():
        output = f"Execution failed (exit {exit_code})"

    return output.strip() or "(no output)", is_error, exit_code


def _read_artifact(interp, path: str) -> dict | None:
    """Download a generated file from the code interpreter sandbox."""
    try:
        response = interp.invoke("readFiles", {"paths": [path]})
        result = _drain_code_stream(response)
        files = result.get("files") or result.get("content") or []
        if not files:
            # Some SDK versions return the file list at top level
            files = result if isinstance(result, list) else []
        for file_item in files:
            if not isinstance(file_item, dict):
                continue
            raw_bytes = file_item.get("bytes")
            raw_text = file_item.get("text")
            if raw_bytes is None and raw_text is None:
                continue
            if isinstance(raw_bytes, (bytes, bytearray)):
                data = bytes(raw_bytes)
            elif isinstance(raw_text, str):
                data = raw_text.encode("utf-8")
            else:
                continue
            mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
            name = path.rsplit("/", 1)[-1]
            if len(data) > 200_000:
                return {"name": name, "path": path, "mime_type": mime, "too_large": True}
            return {
                "name": name,
                "path": path,
                "mime_type": mime,
                "data_url": f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}",
            }
    except Exception as exc:
        logger.debug("[CODE] Could not read artifact %s: %s", path, exc)
    return None


_ARTIFACT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
                         ".csv", ".json", ".txt", ".html", ".pdf"}


def _list_artifacts(interp) -> list[str]:
    """List files in the sandbox and return paths that look like artifacts."""
    try:
        response = interp.invoke("listFiles", {"directoryPath": ""})
        result = _drain_code_stream(response)
        # Different SDK versions use different keys
        entries = result.get("files") or result.get("content") or []
        if not entries and isinstance(result, list):
            entries = result
        paths: list[str] = []
        for entry in entries:
            if isinstance(entry, dict):
                p = entry.get("path") or entry.get("name") or ""
            elif isinstance(entry, str):
                p = entry
            else:
                continue
            if any(p.lower().endswith(ext) for ext in _ARTIFACT_EXTENSIONS):
                paths.append(p)
        return paths
    except Exception as exc:
        logger.debug("[CODE] listFiles failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Semantic search (Qdrant)
# ---------------------------------------------------------------------------

def _make_search_tool(settings: Settings):
    searcher = SemanticSearchTool(settings)

    @tool
    async def semantic_search(query: str, top_k: int = 5) -> str:
        """Search the internal tech-news article database using semantic similarity.

        Always call this first for questions about news, people, companies, events,
        or trends. If the result is "No matching articles found", you MUST follow up
        with browse_web to search the web — do not stop or say you couldn't find it.

        Args:
            query: The natural-language search query (e.g. "FPT AI strategy 2025").
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

        Use this tool to:
        - Fetch live web pages for real-time information.
        - Search the web when semantic_search returns no results — use a Google
          Search URL: https://www.google.com/search?q=<URL-encoded+query>
        - Verify or expand on specific URLs provided by the user.

        Args:
            url: The full URL to navigate to (must include https://). For web
                 searches use DuckDuckGo HTML (NOT Google — it blocks bots):
                 https://html.duckduckgo.com/html/?q=your+search+terms
            task: A description of what information to extract from the page.
        """
        browser_identifier = settings.browser_id or settings.browser_identifier
        safe_url = _safe_url(url)

        try:
            from bedrock_agentcore.tools.browser_client import browser_session
            from playwright.sync_api import sync_playwright

            logger.info(
                "[BROWSER] Starting session region=%s identifier=%s url=%s",
                settings.aws_region,
                browser_identifier,
                safe_url,
            )

            # Use browser_session context manager — handles start/stop/readiness
            with browser_session(settings.aws_region, identifier=browser_identifier) as client:
                ws_url, headers = client.generate_ws_headers()
                logger.info("[BROWSER] Got WebSocket URL, connecting via CDP")

                with sync_playwright() as pw:
                    browser = pw.chromium.connect_over_cdp(
                        ws_url,
                        headers=headers,
                        timeout=settings.browser_timeout * 1000,
                    )
                    try:
                        context = browser.contexts[0] if browser.contexts else browser.new_context()
                        page = context.pages[0] if context.pages else context.new_page()

                        page.goto(url, timeout=settings.browser_timeout * 1000, wait_until="domcontentloaded")

                        # Allow JS-heavy pages extra time to render content
                        try:
                            page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:
                            pass

                        title = page.title()
                        body_text = page.evaluate("""() => {
                            const clone = document.body.cloneNode(true);
                            clone.querySelectorAll('script,style,nav,footer,header,aside').forEach(e => e.remove());
                            return clone.innerText;
                        }""")
                    finally:
                        browser.close()

            content = body_text.strip()[:6000]
            logger.info("[BROWSER] Extracted %d chars from %s title=%r", len(content), safe_url, title)
            return _json_result(
                status="completed",
                mode="agentcore_browser",
                url=safe_url,
                task=task,
                title=title,
                summary=f"Title: {title}\n\nContent:\n{content}",
            )

        except ImportError:
            return _json_result(
                status="failed",
                mode="agentcore_browser",
                url=safe_url,
                error="Browser tool unavailable: playwright or bedrock-agentcore not installed",
            )
        except TypeError as exc:
            # browser_session may not accept identifier kwarg in older SDK versions
            logger.warning("[BROWSER] browser_session TypeError (%s) — falling back to BrowserClient", exc)
            return _browse_via_browser_client(settings, url, safe_url, task, browser_identifier)
        except Exception as exc:
            logger.error("[BROWSER] CDP browsing failed url=%s error=%s", safe_url, exc, exc_info=True)
            try:
                content = _fallback_fetch_url(url, timeout=min(settings.browser_timeout, 20))
                return _json_result(
                    status="completed",
                    mode="http_fallback",
                    url=safe_url,
                    task=task,
                    warning="AgentCore Browser failed; used HTTP fallback without JavaScript rendering.",
                    browser_error=type(exc).__name__,
                    summary=content,
                )
            except Exception as fallback_exc:
                return _json_result(
                    status="failed",
                    mode="agentcore_browser",
                    url=safe_url,
                    task=task,
                    error_type=type(exc).__name__,
                    error=str(exc)[:500],
                    fallback_error=str(fallback_exc)[:200],
                )

    return browse_web


def _browse_via_browser_client(settings: Settings, url: str, safe_url: str, task: str, browser_identifier: str) -> str:
    """Fallback using BrowserClient directly when browser_session doesn't accept identifier."""
    try:
        from bedrock_agentcore.tools.browser_client import BrowserClient
        from playwright.sync_api import sync_playwright

        browser_client = BrowserClient(settings.aws_region)
        browser_client.start(
            identifier=browser_identifier,
            name="tech-news-agent-browser",
            viewport={"width": 1365, "height": 900},
            session_timeout_seconds=900,
        )
        try:
            # Wait for READY (up to 30s)
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                try:
                    session = browser_client.get_session()
                    if session.get("status") == "READY":
                        break
                except Exception:
                    pass
                time.sleep(1)

            ws_url, headers = browser_client.generate_ws_headers()
            with sync_playwright() as pw:
                browser = pw.chromium.connect_over_cdp(
                    ws_url,
                    headers=headers,
                    timeout=settings.browser_timeout * 1000,
                )
                try:
                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                    page = context.pages[0] if context.pages else context.new_page()
                    page.goto(url, timeout=settings.browser_timeout * 1000, wait_until="domcontentloaded")
                    try:
                        page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        pass
                    title = page.title()
                    body_text = page.evaluate("""() => {
                        const clone = document.body.cloneNode(true);
                        clone.querySelectorAll('script,style,nav,footer,header,aside').forEach(e => e.remove());
                        return clone.innerText;
                    }""")
                finally:
                    browser.close()
        finally:
            try:
                browser_client.stop()
            except Exception:
                pass

        content = body_text.strip()[:6000]
        return _json_result(
            status="completed",
            mode="agentcore_browser_client",
            url=safe_url,
            task=task,
            title=title,
            summary=f"Title: {title}\n\nContent:\n{content}",
        )
    except Exception as exc:
        logger.error("[BROWSER] BrowserClient fallback failed: %s", exc, exc_info=True)
        try:
            content = _fallback_fetch_url(url, timeout=20)
            return _json_result(
                status="completed",
                mode="http_fallback",
                url=safe_url,
                task=task,
                warning="All browser methods failed; used HTTP fallback.",
                error_type=type(exc).__name__,
                summary=content,
            )
        except Exception as fallback_exc:
            return _json_result(
                status="failed",
                url=safe_url,
                task=task,
                error_type=type(exc).__name__,
                error=str(exc)[:500],
                fallback_error=str(fallback_exc)[:200],
            )


# ---------------------------------------------------------------------------
# Code Interpreter (AWS Bedrock AgentCore Code Interpreter)
# ---------------------------------------------------------------------------

def _make_code_interpreter_tool(settings: Settings):
    @tool
    def execute_code(code: str, language: str = "python") -> str:
        """Execute code in an AWS-managed sandbox and return the output.

        Use this tool for calculations, data analysis, processing results,
        generating charts, or any computation that requires code execution.
        Save charts and outputs to files (e.g. plt.savefig('/tmp/chart.png'))
        so the UI can render downloadable/viewable artifacts.

        Args:
            code: The code to execute.
            language: Programming language — 'python' (default) or 'javascript'.
        """
        identifier = settings.code_interpreter_id or settings.code_interpreter_identifier
        logger.info("[CODE] Executing %s code (%d chars) identifier=%s", language, len(code), identifier)

        try:
            from bedrock_agentcore.tools.code_interpreter_client import code_session

            with code_session(region=settings.aws_region, identifier=identifier) as interp:
                # Execute the code
                exec_response = interp.invoke("executeCode", {
                    "code": code,
                    "language": language,
                    "clearContext": False,
                })
                exec_result = _drain_code_stream(exec_response)
                output_text, is_error, exit_code = _parse_code_result(exec_result)

                logger.info(
                    "[CODE] Execution done: is_error=%s exit_code=%d output_len=%d",
                    is_error, exit_code, len(output_text),
                )

                # List files and download image/data artifacts
                artifact_paths = _list_artifacts(interp)
                logger.info("[CODE] Found %d artifact(s): %s", len(artifact_paths), artifact_paths)

                artifacts: list[dict] = []
                for path in artifact_paths[:5]:
                    artifact = _read_artifact(interp, path)
                    if artifact:
                        artifacts.append(artifact)
                        logger.info("[CODE] Collected artifact: %s (%s)", artifact["name"], artifact.get("mime_type"))

            return _json_result(
                status="failed" if is_error else "completed",
                language=language,
                exit_code=exit_code,
                summary=output_text,
                artifacts=artifacts,
            )

        except Exception as exc:
            logger.error("[CODE] Execution error: %s", exc, exc_info=True)
            return _json_result(
                status="failed",
                language=language,
                error_type=type(exc).__name__,
                summary=f"Code execution failed ({type(exc).__name__}): {exc}",
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
        # Code Interpreter is intentionally parked for now. Keep the
        # implementation above so it can be restored quickly when needed.
        # _make_code_interpreter_tool(settings),
    ]
