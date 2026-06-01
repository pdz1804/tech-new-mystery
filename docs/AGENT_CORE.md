# Agent Core

`agent_core/` is the standalone AI runtime behind the chatbot. The backend owns users, sessions, message persistence, and SSE delivery to the browser. Agent Core owns the model call, tool execution, streaming events, and optional long-term conversational memory.

## Purpose

Agent Core turns a user message into an answer grounded in the Tech News Mystery article corpus. It can:

- answer questions about indexed technology news;
- search semantically across stored articles;
- browse a live URL when the user asks for current or page-specific information;
- run sandboxed code for calculations or lightweight analysis;
- stream tokens and tool events back to the backend;
- optionally save and retrieve recent turns through AWS Bedrock AgentCore Memory.

## Runtime Shape

```text
frontend /chatbot
  -> backend POST /v1/chat/sessions/{session_id}/stream
  -> backend validates auth + session ownership
  -> backend loads recent DynamoDB messages
  -> backend invokes Agent Core runtime
  -> LangGraph ReAct agent calls tools as needed
  -> Agent Core streams token/tool events
  -> backend forwards SSE to browser
  -> backend saves assistant message in DynamoDB
```

## Main Files

| File | Responsibility |
| --- | --- |
| `agent_core/server.py` | BedrockAgentCoreApp entrypoint, event streaming, memory load/save, diagnostics. |
| `agent_core/graph.py` | Builds the LangGraph ReAct agent with Claude via `ChatBedrockConverse`. |
| `agent_core/tools.py` | Registers LangChain tools exposed to the agent. |
| `agent_core/search.py` | Implements semantic article search with OpenAI embeddings and Qdrant. |
| `agent_core/memory.py` | Best-effort AWS Bedrock AgentCore Memory wrapper. |
| `agent_core/config.py` | Runtime settings, model names, secrets, tool timeouts, Qdrant/OpenAI config. |
| `agent_core/langfuse_observability.py` | Optional Langfuse tracing, masking, LangChain callbacks, and trace metadata. |

Backend integration lives in:

| File | Responsibility |
| --- | --- |
| `backend/app/integrations/agent_core_client.py` | Invokes Agent Core by AWS runtime ARN in production or HTTP locally. |
| `backend/app/api/v1/chat/router.py` | Owns session validation, SSE response, persistence, timeout handling, and cleanup. |

## LangChain And LangGraph Design

Agent Core uses LangChain for model/tool abstractions and LangGraph for agent orchestration.

The current graph is created with `langgraph.prebuilt.create_react_agent`. That means the model runs in a ReAct loop:

1. Read the system prompt, conversation messages, and user message.
2. Decide whether a tool is needed.
3. Emit a tool call when needed.
4. Receive the tool result.
5. Continue reasoning until it can produce the final answer.

The graph is intentionally small. We let LangGraph manage the agent loop instead of manually maintaining separate `route`, `search`, and `generate` nodes.

## Current ReAct Agent Shape

The current agent is built in `agent_core/graph.py` like this:

```python
llm = ChatBedrockConverse(
    model=settings.agent_model,
    region_name=settings.bedrock_region,
    temperature=0.2,
    max_tokens=2048,
    disable_streaming=False,
)

tools = get_tools(settings)
llm_with_prompt = llm.bind(system=SYSTEM_PROMPT)
graph = create_react_agent(llm_with_prompt, tools)
```

Conceptually, the compiled graph behaves like this:

```text
messages
  -> LLM reads system prompt + history + user message
  -> if no tool is needed:
       emit final assistant answer
  -> if a tool is needed:
       emit tool_call
       run selected LangChain tool
       append tool_result to messages
       call LLM again
       repeat until final answer
```

The graph's state is the LangGraph prebuilt message state. We do not define custom state keys for routing or intermediate scratchpads. The main input is:

```python
{
    "messages": [
        HumanMessage(content="previous user message"),
        AIMessage(content="previous assistant message"),
        HumanMessage(content="current user message"),
    ]
}
```

`AgentRuntime.build_input()` creates that list from:

- AgentCore Memory history, when available;
- otherwise backend-provided DynamoDB `recent_events`;
- the current user message.

The tools available to the graph are:

```text
semantic_search(query: str, top_k: int = 5)
browse_web(url: str, task: str)
execute_code(code: str, language: str = "python")
```

During execution, `server.py` listens to LangGraph `astream_events(version="v2")` and maps internal events into our public stream:

| LangGraph event | Agent Core event |
| --- | --- |
| `on_chat_model_stream` | `token` |
| `on_chat_model_end` | fallback chunking for missing final text, if allowed |
| `on_tool_start` | `tool_invocation` |
| `on_tool_end` | `tool_result` |

Example for a news question:

```text
User: "What are the latest AI infrastructure stories?"
  -> LLM chooses semantic_search
  -> tool_invocation: semantic_search
  -> Qdrant returns article summaries
  -> tool_result: semantic_search completed
  -> LLM writes answer using returned titles/summaries
  -> token events stream to backend
  -> done
```

Example for a specific live URL:

```text
User: "Summarize https://example.com/report"
  -> LLM chooses browse_web
  -> tool_invocation: browse_web
  -> browser extracts page text
  -> tool_result: browse_web completed
  -> LLM summarizes the extracted content
  -> token events stream to backend
  -> done
```

## Model

The runtime uses AWS Bedrock through `langchain_aws.ChatBedrockConverse`.

Default model:

```text
us.anthropic.claude-haiku-4-5-20251001-v1:0
```

Important settings:

| Setting | Purpose |
| --- | --- |
| `AGENT_MODEL` | Bedrock model id used by the ReAct agent. |
| `BEDROCK_REGION` | Bedrock region for model calls. |
| `REQUIRE_TRUE_STREAMING` | When enabled, the runtime refuses to fake streaming if Bedrock does not emit real stream chunks. |
| `TOOL_TIMEOUT` | Timeout around async semantic search tool calls. |
| `MAX_SEARCH_RESULTS` | Maximum search results a tool can return. |

## Prompt

The main system prompt is in `agent_core/graph.py` as `SYSTEM_PROMPT`.

It frames the assistant as a technology news analyst and gives tool policy:

- use `semantic_search` first for questions about articles, trends, or recent news;
- use `browse_web` for live web pages, URLs, or real-time information;
- use `execute_code` for calculations, data processing, and code-based analysis;
- cite article titles and sources when possible;
- say when there is not enough information.

This keeps the assistant grounded in the app's article corpus by default, while still allowing external lookup or computation when the user asks for it.

## Tools

### `semantic_search`

Defined in `agent_core/tools.py`, implemented by `agent_core/search.py`.

Flow:

```text
query text
  -> OpenAI embedding
  -> Qdrant vector search
  -> compact article result summaries
  -> LLM context
```

Use cases:

- latest indexed stories about a company or technology;
- trend questions across the article corpus;
- finding related articles when exact keywords differ;
- grounding answers in stored article titles, summaries, slugs, sources, and scores.

Requirements:

- `OPENAI_API_KEY`
- Qdrant config: `QDRANT_URL`/`QDRANT_API_KEY` for cloud or `QDRANT_HOST`/`QDRANT_PORT` locally
- populated Qdrant article collection

### `browse_web`

Defined in `agent_core/tools.py`.

Uses AWS Bedrock AgentCore Browser through Playwright/CDP. The tool navigates to a URL, removes obvious page chrome, and returns readable page text.

If the managed browser session starts but Playwright cannot connect to the CDP
WebSocket, the tool records the browser id, region, URL, and sanitized error in
the tool result. It then attempts a direct HTTP fallback for public pages. That
fallback does not execute JavaScript, so it is useful for simple readable pages
but not for dynamic applications such as many weather sites.

Use cases:

- user gives a specific URL;
- user asks for live information outside the indexed article corpus;
- agent needs to verify page content that is not stored in Qdrant.

Requirements:

- AWS credentials in the runtime environment;
- `BROWSER_ID` from Terraform, or the default AWS browser identifier.

### `execute_code`

Defined in `agent_core/tools.py`.

Uses AWS Bedrock AgentCore Code Interpreter. It executes Python or JavaScript and returns output, errors, stdout, and stderr.

When code creates files and prints their paths, the tool attempts to download up
to five generated artifacts. Small images are returned as data URLs so the chat
UI can preview them in the tool details panel. Larger files are listed as
generated but not inlined.

Use cases:

- calculations;
- summarizing structured values;
- simple data processing;
- quick analysis over tool results.

Requirements:

- AWS credentials in the runtime environment;
- `CODE_INTERPRETER_ID` from Terraform, or the default AWS code interpreter identifier.

## Request Flow

1. The frontend sends a chat message to the backend stream endpoint.
2. The backend validates JWT auth and session ownership.
3. The backend loads recent session messages from DynamoDB.
4. The backend saves the user message before invoking the agent.
5. `AgentCoreClient` invokes Agent Core:
   - production path: `bedrock-agentcore.invoke_agent_runtime`;
   - local path: HTTP `POST /invocations`.
6. `server.py` loads recent AgentCore Memory turns if memory is configured.
7. `graph.py` builds LangGraph input:
   - prefer AgentCore Memory history when available;
   - otherwise use DynamoDB `recent_events` from the backend;
   - append the current user message.
8. LangGraph runs the ReAct agent.
9. Agent Core emits events:
   - `token`
   - `tool_invocation`
   - `tool_result`
   - `stream_diagnostic`
   - `error`
   - `done`
10. The backend forwards user-facing events as SSE.
11. The backend saves the final assistant message to DynamoDB.
12. Agent Core saves the turn to AgentCore Memory as a best-effort operation.

## Streaming Events

Agent Core emits dictionaries. The backend converts the relevant ones to browser SSE frames.

| Event | Meaning |
| --- | --- |
| `token` | Visible assistant text chunk. |
| `tool_invocation` | Agent started a tool call. |
| `tool_result` | Tool finished and returned a result. |
| `stream_diagnostic` | Internal streaming diagnostics, not forwarded to the frontend. |
| `error` | Recoverable or fatal agent error. |
| `done` | Agent runtime completed. The backend suppresses internal `done` and sends its own final `done` after persistence. |

The runtime prefers true Bedrock ConverseStream token events. If LangGraph only exposes model-end text after a tool result, `server.py` forwards the missing suffix in small chunks so the browser still paints progressively. If strict true streaming is required and no stream chunks arrive, Agent Core emits a `TRUE_STREAMING_REQUIRED` error.

## Langfuse Observability

Agent Core supports optional Langfuse tracing for debugging non-deterministic
agent behavior.

Configuration:

```text
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_ENABLED=true
LANGFUSE_TRACE_CONTENT=true
```

Production wiring:

- Terraform injects non-secret runtime flags into the AgentCore runtime environment:
  `LANGFUSE_ENABLED`, `LANGFUSE_BASE_URL`, `LANGFUSE_ENVIRONMENT`,
  `LANGFUSE_RELEASE`, and `LANGFUSE_TRACE_CONTENT`.
- `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY` should live in the app
  Secrets Manager JSON secret referenced by `APP_SECRET_ARN`.
- `agent_core/config.py` loads the Langfuse keys from that secret before the
  observer starts, so traces are enabled without exposing credentials in
  Terraform state.

What is traced:

- a root `agent_core.invoke` span for every agent request;
- LangGraph/LangChain callbacks for model calls, tool calls, and nested agent observations;
- `session_id` propagated from the chat session;
- `user_id` propagated from the authenticated backend user;
- metadata such as model id, Bedrock region, memory status, graph type, configured tool resources, and stream counts;
- agent graph visualization through Langfuse's LangGraph/LangChain observations;
- token and cost tracking when Langfuse can infer usage from the model or when provider usage is available.

Masking:

- API keys, tokens, passwords, AWS access key patterns, and large base64 data URLs are redacted before sending traces.
- Set `LANGFUSE_TRACE_CONTENT=false` when you want metadata/tool timing without recording message content.

Why this helps:

- failed browser CDP handshakes show up as tool errors with region/browser metadata;
- semantic search queries and result summaries can be inspected inside the same trace;
- code interpreter errors and generated artifacts are visible as tool observations;
- multi-turn chat can be grouped by session for debugging.

## Browser Automation Troubleshooting

AgentCore Browser has two layers:

1. Browser session management: start, get, and stop sessions.
2. Automation stream access: enable/update the stream and connect Playwright
   over CDP.

If sessions are created but Playwright returns `403 Forbidden` while connecting
to `/automation`, check IAM for:

```text
bedrock-agentcore:UpdateBrowserStream
bedrock-agentcore:ConnectBrowserAutomationStream
```

Those are separate from `StartBrowserSession` and `GetBrowserSession`. Terraform
grants them to the AgentCore runtime role and the backend invoke role.

## Memory

There are two memory layers:

| Layer | Owner | Purpose |
| --- | --- | --- |
| DynamoDB chat history | Backend | Durable session/message store for the product UI. |
| AgentCore Memory | Agent Core | Optional recent-turn memory available directly to the runtime. |

Current behavior:

- backend always stores chat sessions and messages in DynamoDB;
- backend sends recent session messages as `recent_events`;
- Agent Core loads up to 5 recent turns from AgentCore Memory when `MEMORY_ID` is configured;
- if AgentCore Memory is unavailable, the runtime silently falls back to backend-provided `recent_events`;
- Agent Core saves each successful turn to memory as best effort;
- memory failures do not fail the user request.

This gives local development a simple path while production can use AWS-managed memory.

## Current Scope

The agent can support:

- answering questions about indexed tech news articles;
- summarizing and comparing recent article themes;
- finding articles by semantic meaning;
- citing article titles and slugs returned by Qdrant;
- browsing specific live web pages when browser tooling is configured;
- running small calculations or analysis snippets when code interpreter is configured;
- streaming long answers and tool status to the UI;
- preserving chat sessions through backend DynamoDB.

The agent should not be treated as:

- a general-purpose autonomous web crawler;
- a replacement for the backend clustering worker;
- a guaranteed real-time news feed unless browsing is configured and explicitly used;
- a source of private user data outside the current authenticated chat context;
- a durable long-term memory system when `MEMORY_ID` is not configured.

## Local Development

Start Agent Core locally:

```powershell
cd agent_core
pip install -r requirements.txt
uvicorn agent_core.server:app --host 0.0.0.0 --port 8080 --reload
```

Backend should point to it with:

```text
AGENT_CORE_BASE_URL=http://localhost:8080
```

Production uses `AGENT_CORE_RUNTIME_ARN` and calls AWS Bedrock AgentCore Runtime through boto3.

### Local Docker Test Path

The repo includes a local Docker Compose service:

```powershell
cd infra
docker compose build agent-core
docker compose up agent-core -d
docker compose logs -f agent-core
```

Health check:

```powershell
curl.exe http://localhost:8080/ping
```

Direct invocation test:

```powershell
$body = '{"prompt":"Use semantic_search to find AI infrastructure articles and summarize three results.","session_id":"local-agent-test","user_id":"local-dev","context":{"recent_events":[]}}'
curl.exe -N http://localhost:8080/invocations -H "Content-Type: application/json" -d $body
```

Browser tool smoke test:

```powershell
$body = '{"prompt":"Use browse_web to summarize https://example.com in two bullets.","session_id":"local-browser-test","user_id":"local-dev","context":{"recent_events":[]}}'
curl.exe -N http://localhost:8080/invocations -H "Content-Type: application/json" -d $body
```

Code artifact smoke test:

```powershell
$body = '{"prompt":"Use execute_code to create a simple matplotlib line chart, save it to /tmp/agent_test_plot.png, print the path, and explain the chart.","session_id":"local-code-test","user_id":"local-dev","context":{"recent_events":[]}}'
curl.exe -N http://localhost:8080/invocations -H "Content-Type: application/json" -d $body
```

Local Docker environment notes:

- `infra/docker-compose.yml` loads Agent Core env vars from the root `.env`.
- If keys live only in `backend/.env`, the `agent-core` container will not see them.
- Rebuild the image after changing `agent_core/requirements.txt`; mounted source code updates live, installed packages do not.
- AWS credentials are mounted from `~/.aws` into the container.
- Managed Browser and Code Interpreter tools still call AWS AgentCore resources; local Docker only runs our runtime process.

For backend-to-Agent-Core local testing:

```text
AGENT_CORE_RUNTIME_ARN=
AGENT_CORE_BASE_URL=http://localhost:8080
```

If the backend also runs inside Docker Compose, use the service DNS name instead:

```text
AGENT_CORE_BASE_URL=http://agent-core:8080
```

## Operational Notes

- Keep heavy article processing in backend workers, not Agent Core.
- Keep the system prompt short and operational. Tool descriptions already tell the model when each tool is useful.
- Prefer adding focused tools with clear argument schemas over broad tools that can do anything.
- Treat browser and code interpreter tools as optional production capabilities; semantic search is the core product tool.
- Do not log secrets, raw API keys, or full private user context.
- Use `stream_diagnostic` events for troubleshooting streaming behavior without exposing diagnostics in the UI.

## Tests

Agent Core tests live under `agent_core/tests/`.

Useful commands:

```powershell
cd agent_core
pytest
```

Backend streaming and client behavior are covered from the backend side:

```powershell
cd backend
pytest tests
```
