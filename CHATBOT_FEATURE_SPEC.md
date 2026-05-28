# Chatbot Feature Specification

**Version:** 1.0  
**Date:** May 28, 2026  
**Status:** Ready for Implementation  

---

## Executive Summary

The Chatbot Feature enables users to have intelligent conversations with an AI agent that can search articles, provide analysis, and answer questions about news topics. This is powered by **AWS Agent Core Runtime** — a separate microservice that orchestrates multi-step reasoning, tool invocation, and conversational context management — invoked by the FastAPI backend via API calls.

**What:** AI-powered conversational agent with semantic article search and built-in reasoning tools  
**Why:** Enable users to ask complex questions, get personalized insights, and discover articles through natural dialogue  
**How:** Frontend chatbot → FastAPI backend → AWS Agent Core Runtime API → Tool execution (web search, code interpreter, semantic search) → DynamoDB session storage  

**Key Difference:** Agent Core Runtime is a separate managed service (not Lambda), handling memory, tool orchestration, and streaming responses independently.

---

## Agent Framework: LangChain + LangGraph

The chatbot uses **LangChain** and **LangGraph** as the core agent frameworks powering the AI logic within AWS Agent Core Runtime.

### What is LangChain?

**LangChain** is a framework for building applications powered by language models. It provides:

- **Tool Definitions:** Simple way to define tools (functions) that agents can invoke
- **Agent Core:** Abstractions for building agents that decide when to use tools
- **LLM Integration:** Seamless integration with Claude Haiku via Bedrock
- **Message Parsing:** Handle input/output formatting for agent-LLM interactions
- **Tool Binding:** Connect tools to agents and manage invocation logic

**In this project:** LangChain defines the three tools (Web Search, Code Interpreter, Semantic Search) and handles the agent's decision logic for tool selection and invocation.

### What is LangGraph?

**LangGraph** is a library for building **stateful, multi-step agentic workflows** using directed graphs. It provides:

- **State Graphs:** Define agent state schema (what data persists across steps)
- **Nodes:** Represent steps in the workflow (e.g., agent reasoning node, tool execution node)
- **Edges:** Define transitions between nodes (e.g., when to invoke tools, when to respond)
- **Conditional Logic:** Route execution based on agent decisions (use tool vs. respond directly)
- **Cycles:** Support agentic loops for multi-step reasoning (think → act → think → respond)

**In this project:** LangGraph orchestrates the agent workflow—handling the state transitions between user input, agent reasoning, tool invocation, and response generation.

### How LangChain + LangGraph Work Together

```
User Message
    ↓
┌─────────────────────────────────────┐
│ LangGraph: Agent Workflow            │
│                                     │
│ START                               │
│   ↓                                 │
│ [Agent Node]                        │
│   - Uses LangChain agent logic      │
│   - Reasons about user query        │
│   - Decides if tools are needed     │
│   ↓                                 │
│ [Conditional Edge]                  │
│   - Route to tools? Or respond?     │
│   ↓                ↓                 │
│ [Tool Node]   [END]                 │
│   - Invokes tools via LangChain     │
│   - Web Search                      │
│   - Code Interpreter                │
│   - Semantic Search (Qdrant)        │
│   ↓                                 │
│ [Back to Agent]                     │
│   - Process tool results            │
│   - Continue reasoning              │
│   ↓                                 │
│ [Final Response]                    │
│   - Synthesize answer from tools    │
│   - Return to user                  │
│                                     │
└─────────────────────────────────────┘
    ↓
FastAPI Backend → Streams to Frontend
```

### System Architecture with Agent Frameworks

```
┌──────────────────────────────────────────────────────────────┐
│ Frontend (React)                                              │
│ - Chatbot UI (Apple design + liquid glass)                    │
│ - Session management                                          │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ POST /api/v1/chat/message
                     │ { user_message, session_id }
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ FastAPI Backend (Port 8000)                                   │
│ - Validates auth & session                                    │
│ - Calls Agent Core Runtime API                                │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ HTTP API call
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ AWS Agent Core Runtime (ECS/Managed)                          │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ LangGraph Workflow (State Graph)                        │  │
│ │                                                         │  │
│ │ START                                                   │  │
│ │   ↓                                                     │  │
│ │ ┌───────────────────────────────────────────────────┐  │  │
│ │ │ Agent Node (LangChain Agent)                      │  │  │
│ │ │ - Receives user message                           │  │  │
│ │ │ - Calls Claude Haiku via Bedrock                  │  │  │
│ │ │ - Reasons about available tools                   │  │  │
│ │ │ - Decides: invoke tools or respond?               │  │  │
│ │ └───────────────────────────────────────────────────┘  │  │
│ │   ↓                                                     │  │
│ │ ┌───────────────────────────────────────────────────┐  │  │
│ │ │ Conditional Edge (tools_condition)                │  │  │
│ │ │ - Route: "tools" or "end"?                        │  │  │
│ │ └───────────────────────────────────────────────────┘  │  │
│ │   ↓                        ↓                            │  │
│ │ ┌──────────────────┐  [END]                            │  │
│ │ │ Tool Node        │                                   │  │
│ │ │ (LangChain tools)│                                   │  │
│ │ │                  │                                   │  │
│ │ │ ┌──────────────┐ │                                   │  │
│ │ │ │ Browser Tool │ │                                   │  │
│ │ │ │ (AWS)        │ │                                   │  │
│ │ │ └──────────────┘ │                                   │  │
│ │ │                  │                                   │  │
│ │ │ ┌──────────────┐ │                                   │  │
│ │ │ │Code Interp.  │ │                                   │  │
│ │ │ │ (Container)  │ │                                   │  │
│ │ │ └──────────────┘ │                                   │  │
│ │ │                  │                                   │  │
│ │ │ ┌──────────────┐ │                                   │  │
│ │ │ │Semantic Srch │ │                                   │  │
│ │ │ │ (Qdrant)     │ │                                   │  │
│ │ │ └──────────────┘ │                                   │  │
│ │ │                  │                                   │  │
│ │ │ Execute & gather │                                   │  │
│ │ │ tool results     │                                   │  │
│ │ └──────────────────┘                                   │  │
│ │   ↓                                                     │  │
│ │ ┌───────────────────────────────────────────────────┐  │  │
│ │ │ Loop Back to Agent Node                           │  │  │
│ │ │ - Provide tool results to Claude Haiku            │  │  │
│ │ │ - Continue multi-step reasoning                   │  │  │
│ │ │ - Decide: more tools or final response?           │  │  │
│ │ └───────────────────────────────────────────────────┘  │  │
│ │   ↓                                                     │  │
│ │ [Final Response] → Stream to FastAPI                   │  │
│ │                                                         │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ Uses:                                                         │
│ - Claude Haiku via Bedrock for reasoning                     │
│ - Agent Core Memory for session context                      │
│ - Browser Tool (containerized within AgentCore)              │
│ - Code Interpreter (containerized within AgentCore)          │
│ - Qdrant for semantic search                                 │
└──────────────────────────────────────────────────────────────┘
                     │
                     │ Stream response tokens
                     │ + tool invocations
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ FastAPI Backend                                               │
│ - Streams events (tokens, tool calls) via SSE                │
│ - Persists messages to DynamoDB                              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ Server-Sent Events
                     │ (streaming tokens)
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ Frontend (React)                                              │
│ - Renders tokens in real-time                                │
│ - Shows tool invocations to user                             │
│ - Updates chat UI dynamically                                │
└──────────────────────────────────────────────────────────────┘
```

### LangChain: Building the Agent

**LangChain provides:**

1. **Tool Definitions** — Define what tools the agent can use:
```python
from langchain.tools import Tool

web_search_tool = Tool(
    name="web_search",
    func=aws_browser_search,  # Uses AWS Browser Tool for search
    description="Search the public web for current information"
)

code_interpreter_tool = Tool(
    name="code_interpreter",
    func=aws_code_interpreter,  # AWS Code Interpreter (containerized within AgentCore)
    description="Execute Python code for analysis"
)

semantic_search_tool = Tool(
    name="semantic_search",
    func=qdrant_semantic_search,  # Qdrant vector search
    description="Search articles semantically by meaning"
)

tools = [web_search_tool, code_interpreter_tool, semantic_search_tool]
```

2. **Agent Creation** — Build an agent that selects tools:
```python
from langchain.agents import create_react_agent
from langchain.llms.bedrock import BedrockLLM

# Create LLM (Claude Haiku via Bedrock)
llm = BedrockLLM(
    model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
    region_name="us-east-1"
)

# Create agent using ReAct (Reasoning + Acting)
agent = create_react_agent(
    llm=llm,
    tools=tools,
    prompt=custom_prompt  # Optional: customize agent behavior
)
```

3. **Tool Binding** — Connect tools to agent:
```python
# Bind tools to LLM so it knows how to call them
agent_with_tools = llm.bind_tools(tools)

# LLM now understands tool signatures and can decide when to use them
```

4. **Message Handling** — Process input/output:
```python
from langchain.schema import HumanMessage, AIMessage, ToolMessage

# Format user query
user_message = HumanMessage(content="What are the latest AI breakthroughs?")

# Agent processes and may invoke tools
response = agent.invoke({"input": user_message})

# Response contains agent reasoning + tool calls
```

### LangGraph: Orchestrating the Workflow

**LangGraph defines the execution graph:**

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from typing import TypedDict, Annotated
import operator

# 1. Define Agent State (what data flows through the graph)
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]  # Accumulate messages
    user_id: str
    session_id: str
    next_action: str  # "tools" or "end"

# 2. Define Agent Node (reasoning step)
def agent_node(state: AgentState):
    """Agent reasons about user query and decides on tools"""
    messages = state["messages"]
    
    # Call Claude Haiku to reason
    response = llm.invoke(messages)
    
    # Check if agent wants to use tools
    if response.tool_calls:
        state["next_action"] = "tools"
    else:
        state["next_action"] = "end"
    
    return {"messages": [response]}

# 3. Define Tool Node (execution step)
def tool_node(state: AgentState):
    """Execute selected tools"""
    last_message = state["messages"][-1]
    
    # Extract tool calls from agent response
    tool_calls = last_message.tool_calls
    
    # Execute each tool and gather results
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_input = tool_call["args"]
        
        # Find and execute tool
        tool = next(t for t in tools if t.name == tool_name)
        result = tool.func(**tool_input)
        
        results.append(ToolMessage(
            tool_call_id=tool_call["id"],
            name=tool_name,
            content=result
        ))
    
    return {"messages": results}

# 4. Build the State Graph
workflow = StateGraph(AgentState)

# 5. Add nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))

# 6. Connect edges
workflow.add_edge(START, "agent")  # Start with agent reasoning
workflow.add_conditional_edges(
    "agent",
    tools_condition,  # Use built-in condition to route
    {
        "tools": "tools",  # If tools needed, go to tool node
        END: END  # If no tools, end conversation
    }
)
workflow.add_edge("tools", "agent")  # After tools, back to agent for synthesis

# 7. Compile to runnable graph
app = workflow.compile()

# 8. Execute the graph
async def run_agent(user_message: str, session_id: str, user_id: str):
    """Run agent with streaming"""
    initial_state = AgentState(
        messages=[HumanMessage(content=user_message)],
        user_id=user_id,
        session_id=session_id,
        next_action=""
    )
    
    # Stream results as they execute
    async for event in app.astream(initial_state):
        yield event
```

### Integration: LangChain + LangGraph in FastAPI

```python
# backend/app/integrations/agent.py

from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain.agents import create_react_agent
from langchain.llms.bedrock import BedrockLLM
from langchain.tools import Tool

class ChatbotAgent:
    """Chatbot agent using LangChain + LangGraph"""
    
    def __init__(self):
        # Initialize LLM (Claude Haiku via Bedrock)
        self.llm = BedrockLLM(
            model_id="us.anthropic.claude-haiku-4-5-20251001-v1:0",
            region_name="us-east-1"
        )
        
        # Define tools (LangChain)
        self.tools = [
            Tool(
                name="web_search",
                func=self.web_search,
                description="Search the web for information"
            ),
            Tool(
                name="code_interpreter",
                func=self.code_interpreter,
                description="Execute Python code"
            ),
            Tool(
                name="semantic_search",
                func=self.semantic_search,
                description="Search articles by semantic similarity"
            )
        ]
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
    
    def _build_workflow(self):
        """Build the LangGraph state graph"""
        from typing import TypedDict, Annotated
        import operator
        
        class AgentState(TypedDict):
            messages: Annotated[list, operator.add]
            user_id: str
            session_id: str
        
        def agent_node(state: AgentState):
            """Agent reasoning node"""
            response = self.llm.invoke(state["messages"])
            return {"messages": [response]}
        
        # Create graph
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            tools_condition,
            {"tools": "tools", END: END}
        )
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    async def stream_response(
        self,
        user_message: str,
        session_id: str,
        user_id: str
    ):
        """Stream response tokens and tool invocations"""
        from langchain.schema import HumanMessage
        
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "user_id": user_id,
            "session_id": session_id
        }
        
        async for event in self.workflow.astream(initial_state):
            # Emit token events
            if "token" in event:
                yield {"type": "token", "content": event["token"]}
            
            # Emit tool invocation events
            if "tool_call" in event:
                yield {"type": "tool_invocation", **event["tool_call"]}
            
            # Emit tool result events
            if "tool_result" in event:
                yield {"type": "tool_result", **event["tool_result"]}
    
    async def web_search(self, query: str, max_results: int = 10):
        """Web search tool (AWS Browser Tool)"""
        # Uses AWS Browser Tool to navigate search engines and extract results
        pass
    
    async def code_interpreter(self, code: str):
        """Code interpreter tool (AWS containerized execution)"""
        # Calls AWS code interpreter with containerized isolation within AgentCore
        pass
    
    async def semantic_search(self, query: str, top_k: int = 10):
        """Semantic search tool (Qdrant)"""
        # Calls Qdrant for vector search
        pass
```

### FastAPI Integration

```python
# backend/app/api/v1/chat/router.py

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from backend.app.integrations.agent import ChatbotAgent

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
agent = ChatbotAgent()

@router.post("/message")
async def chat_message(request: ChatMessageRequest, current_user: User = Depends()):
    """Send message to chatbot using LangChain + LangGraph agent"""
    
    async def stream_response():
        async for event in agent.stream_response(
            user_message=request.user_message,
            session_id=request.session_id,
            user_id=current_user.id
        ):
            if event["type"] == "token":
                yield f"event: token\ndata: {json.dumps(event)}\n\n"
            elif event["type"] == "tool_invocation":
                yield f"event: tool_invocation\ndata: {json.dumps(event)}\n\n"
            elif event["type"] == "tool_result":
                yield f"event: tool_result\ndata: {json.dumps(event)}\n\n"
    
    return StreamingResponse(stream_response(), media_type="text/event-stream")
```

### Key Concepts

| Concept | LangChain | LangGraph | Purpose |
|---------|-----------|-----------|---------|
| **Tools** | Defined here | Referenced in workflow | What agent can do |
| **Agent** | Core logic | Wrapper (node) | Reasoning + tool selection |
| **Workflow** | Single-step | Multi-step graph | Orchestration & loops |
| **Streaming** | Token-level | Event-level | Real-time user feedback |
| **State** | Implicit (messages) | Explicit (TypedDict) | What persists across steps |
| **Routing** | Manual | Conditional edges | Automatic flow control |

---

## Architecture

### System Diagram

```
┌──────────────────────────────────────────────────────────────┐
│ Frontend (React)                                              │
│ - Chatbot UI (Apple design + liquid glass)                    │
│ - Navbar with Chatbot tab                                     │
│ - Session management (create, list, load)                     │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ POST /api/v1/chat/message
                     │ { user_message, session_id, context }
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ FastAPI Backend (Port 8000)                                   │
│ - POST /api/v1/chat/message                                   │
│ - GET /api/v1/chat/sessions                                   │
│ - POST /api/v1/chat/sessions                                  │
│ - Handles auth, session validation, logging                   │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     │ HTTP API calls
                     │ (Agent Core Runtime integration)
                     ▼
┌──────────────────────────────────────────────────────────────┐
│ AWS Agent Core Runtime Service (ECS/Managed)                  │
│ - Orchestrates agent workflow                                 │
│ - Integrates with Agent Core Memory (separate service)        │
│ - Invokes tools & handles responses                           │
│ - Streaming response support                                  │
│ - Auto-routing to appropriate models                          │
└────────────────────┬─────────────────────────────────────────┘
                     │
         ┌───────────┼───────────┬─────────────┐
         │           │           │             │
         ▼           ▼           ▼             ▼
   ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌────────────┐
   │ Web     │ │ Code     │ │Semantic │ │  Bedrock / │
   │ Search  │ │Interpreter│ │ Search  │ │ Claude API │
   │ (AWS)   │ │ (AWS)    │ │(Qdrant) │ │(LLM)       │
   └─────────┘ └──────────┘ └─────────┘ └────────────┘
         │           │           │             │
         └───────────┼───────────┴─────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │ DynamoDB              │
         │ - sessions table       │
         │ - messages table       │
         │ - user preferences     │
         └───────────────────────┘
```

### Component Roles

| Component | Responsibility | Details |
|-----------|-----------------|---------|
| **Frontend** | User interaction | Chat interface, session UI, message rendering |
| **FastAPI Backend** | Request routing & auth | Validate user, fetch context, invoke Agent Core Runtime, persist sessions |
| **Agent Core Runtime** | AI orchestration | Tool invocation, reasoning, response generation via Claude Haiku |
| **Agent Core Memory** | Session persistence | Stores short-term conversation events (separate AWS service) |
| **Tools** | External capabilities | Browser (containerized web navigation), Code Interpreter (containerized execution), semantic search on embeddings |
| **DynamoDB** | Persistence | Store chat sessions, message history, user preferences |
| **Qdrant** | Semantic search | Article embeddings, vector database for similarity search |
| **Bedrock** | Language model | Claude Haiku (us.anthropic.claude-haiku-4-5-20251001-v1:0) for reasoning, summaries, and natural language generation |

---

## Agent Core Runtime

### Deployment & Configuration

**Infrastructure Setup:**

```hcl
# infra/terraform/ecs.tf (add new service for Agent Core)

resource "aws_ecs_cluster" "agent_core" {
  name = "${local.name_prefix}-agent-core"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = local.common_tags
}

resource "aws_ecs_task_definition" "agent_core" {
  family                   = "${local.name_prefix}-agent-core"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "2048"
  memory                   = "4096"
  execution_role_arn       = aws_iam_role.ecs_task_execution_agent_core.arn
  task_role_arn            = aws_iam_role.ecs_task_agent_core.arn

  container_definitions = jsonencode([{
    name      = "agent-core"
    image     = "aws-agent-core:latest"  # AWS provided image
    essential = true
    portMappings = [{
      containerPort = 8080
      hostPort      = 8080
      protocol      = "tcp"
    }]

    environment = [
      {
        name  = "AWS_REGION"
        value = var.aws_region
      },
      {
        name  = "AGENT_MODEL"
        value = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
      },
      {
        name  = "MEMORY_TYPE"
        value = "short_term"
      },
      {
        name  = "TOOL_TIMEOUT"
        value = "30"  # seconds
      }
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.agent_core.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}

resource "aws_ecs_service" "agent_core" {
  name            = "${local.name_prefix}-agent-core"
  cluster         = aws_ecs_cluster.agent_core.id
  task_definition = aws_ecs_task_definition.agent_core.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  load_balancer {
    target_group_arn = aws_lb_target_group.agent_core.arn
    container_name   = "agent-core"
    container_port   = 8080
  }

  network_configuration {
    subnets          = local.private_subnet_ids
    security_groups  = [aws_security_group.agent_core.id]
    assign_public_ip = false
  }

  depends_on = [
    aws_lb_listener.agent_core
  ]

  tags = local.common_tags
}

resource "aws_lb_target_group" "agent_core" {
  name        = "${local.name_prefix}-agent-core"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = local.vpc_id
  target_type = "ip"

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = local.common_tags
}

resource "aws_lb" "agent_core" {
  name               = "${local.name_prefix}-agent-core"
  internal           = true  # Only accessible from backend VPC
  load_balancer_type = "application"
  subnets            = local.private_subnet_ids
  security_groups    = [aws_security_group.agent_core_lb.id]

  tags = local.common_tags
}

resource "aws_lb_listener" "agent_core" {
  load_balancer_arn = aws_lb.agent_core.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agent_core.arn
  }
}

resource "aws_iam_role" "ecs_task_execution_agent_core" {
  name = "${local.name_prefix}-agent-core-execution"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_agent_core" {
  role       = aws_iam_role.ecs_task_execution_agent_core.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_agent_core" {
  name = "${local.name_prefix}-agent-core-task"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "agent_core_tools" {
  name = "${local.name_prefix}-agent-core-tools"
  role = aws_iam_role.ecs_task_agent_core.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeAgentCore"  # For agent orchestration and tool execution
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:*"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_security_group" "agent_core" {
  name   = "${local.name_prefix}-agent-core"
  vpc_id = local.vpc_id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_security_group" "agent_core_lb" {
  name   = "${local.name_prefix}-agent-core-lb"
  vpc_id = local.vpc_id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "agent_core" {
  name              = "/ecs/${local.name_prefix}-agent-core"
  retention_in_days = 7

  tags = local.common_tags
}
```

### Agent Core Memory: Short-Term Strategy (Separate Service)

Agent Core Memory is a separate, fully managed AWS service that provides persistent memory for AI agents. You must explicitly create and configure it for your AgentCore Runtime agents.

#### Short-Term Memory Strategy (User's Choice)

**Configuration:**
- Strategy type: SHORT_TERM
- Stores: Raw conversation events (user messages + agent responses)
- Scope: Single session lifetime
- Loading: Automatic via memory hooks at agent initialization
- No long-term extraction: Focus only on immediate conversational context

**How it works:**
1. Agent Core Runtime initializes → triggers AgentInitializedEvent hook
2. Hook loads recent short-term memory events from Agent Core Memory service
3. During conversation, agent writes each interaction (user message, response) as events
4. Events are chronologically ordered and automatically available to agent
5. Memory persists for session duration, then follows DynamoDB TTL (90 days)

**Integration in agent code:**

```python
from bedrock_agentcore import Agent, MemoryManager

# 1. Create Agent Core Memory resource separately
memory_manager = MemoryManager(
    agent_id="chatbot-agent",
    memory_type="short_term",  # SHORT-TERM ONLY
    session_id=session_id
)

# 2. Initialize agent with memory hooks
agent = Agent(
    agent_name="news-chatbot",
    memory=memory_manager,
    on_agent_initialized=lambda: memory_manager.load_recent_events()
)

# 3. During conversation, write events
await agent.add_event(
    role="user",
    content=user_message,
    timestamp=int(time.time())
)

response = await agent.process_message(user_message)

await agent.add_event(
    role="assistant",
    content=response,
    timestamp=int(time.time())
)
```

**Architecture:**
```
Agent Core Runtime
├─ Initializes
├─ Triggers AgentInitializedEvent
│  └─ Loads recent short-term memory events from Agent Core Memory service
├─ Processes user message
├─ Writes event to Agent Core Memory (user + response)
└─ Next turn: memory available for context
```

**Key points:**
- Agent Core Memory is NOT built-in; it's a separate service
- Short-term memory stores raw conversation history only
- No async extraction or background processing
- Memory TTL: 90 days (matches DynamoDB session TTL)
- Perfect for conversation context without cross-session persistence

---

## Tools Definition

AWS Agent Core Runtime automatically provides two powerful built-in tools. We must implement one custom tool for semantic article search.

### Tool Classification Summary

| Tool | Type | Status | Implementation | When Ready |
|------|------|--------|-----------------|-----------|
| **Browser Tool** | AWS Built-In | Ready Now | Zero — AWS handles it automatically | ✓ Available on Day 1 |
| **Code Interpreter** | AWS Built-In | Ready Now | Zero — AWS handles it automatically | ✓ Available on Day 1 |
| **Semantic Search** | Custom (Qdrant) | Requires Build | Must implement handler + register | Blocks deployment until complete |

**Implementation Effort Summary:**
- **Browser Tool:** 0 hours (AWS provides)
- **Code Interpreter:** 0 hours (AWS provides)
- **Semantic Search:** ~8-12 hours (implement + test + register)

---

### AWS Agent Core Built-In Tools (Automatic)

These tools are provided by AWS Agent Core Runtime automatically. **NO custom implementation needed** — AWS handles all infrastructure and invocation.

#### 1. Browser Tool (AWS Built-In)

**Tool ID:** `aws.browser.v1`  
**Status:** Provided by AWS Agent Core Runtime  
**Implementation:** No custom code required — AWS manages the browser automation  
**How it works:** Agent Core runs browser in containerized environment within AgentCore, integrated with Playwright/Puppeteer/Selenium via WebSocket  
**Cost:** Included in Agent Core Runtime pricing  

**Technology & Execution:**
- **Environment:** Containerized browser within AWS Agent Core infrastructure
- **Protocol:** Chrome DevTools Protocol (CDP) via WebSocket
- **Integration:** Compatible with Playwright, Puppeteer, Selenium, Browser Use library, Amazon Nova Act
- **Isolation:** Web activity isolated from local system in managed container

**Capabilities:**

- **Web Automation via Chrome DevTools Protocol (CDP)**
  - `navigate(url)` — Navigate to URLs
  - `click(selector)` — Click on elements
  - `fill(selector, text)` — Fill form fields
  - `type(text)` — Type text into focused element
  - `extract(selector)` — Extract text or HTML from elements
  - `screenshot()` — Capture current page state
  - `keyboard` — Send keyboard shortcuts
  - `mouse` — Move mouse and perform click/drag actions
  - `shortcuts` — Execute OS-level shortcuts (Ctrl+C, etc.)

**Viewport & Session Details:**
- Default viewport: 1456 x 819 pixels (customizable)
- Default timeout: 15 minutes (900 seconds)
- Maximum timeout: 8 hours (28,800 seconds) — configurable
- Internet access: YES (can navigate websites and access public APIs)
- Multiple concurrent sessions supported
- Ephemeral sessions that reset after each use
- Each session has its own browser context

**Observability & Recording:**
- Live View: Real-time monitoring of browser sessions for human intervention
- Session Recording: Captures DOM changes, user actions, console logs, network events
- CloudWatch Metrics: Real-time performance insights and integration with AWS monitoring
- Recording Storage: Sessions recorded to S3 bucket for replay
- Replay Features: Video playback, timeline navigation, user action tracking

**Security:**
- Containerized environment isolated from your local system
- Session isolation ensures complete separation between users
- Ephemeral sessions that reset after each use
- Automatic termination when TTL expires
- Fully managed by AWS (no self-managed infrastructure)
- Network isolation between sessions
- Human intervention capability through Live View

**Usage Example:**
```json
{
  "tool_id": "aws.browser.v1",
  "name": "browser",
  "description": "Automate browser interactions, navigate URLs, extract content, and take screenshots",
  "capabilities": [
    "navigate to any URL",
    "fill and submit forms",
    "click buttons and links",
    "extract text or structured data from pages",
    "take screenshots",
    "search on Google or other search engines",
    "interact with dynamic content (JavaScript-rendered pages)"
  ]
}
```

**Python SDK Example:**
```python
import boto3

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

# Start browser session (containerized browser provisioned)
session = client.start_browser_session(
    browserIdentifier='aws.browser.v1',
    sessionTimeoutSeconds=900
)

session_id = session['sessionId']

# Navigate to URL
response = client.invoke_browser(
    browserIdentifier='aws.browser.v1',
    sessionId=session_id,
    action={'navigate': {'url': 'https://news.example.com'}}
)

# Take screenshot
screenshot = client.invoke_browser(
    browserIdentifier='aws.browser.v1',
    sessionId=session_id,
    action={'screenshot': {}}
)

# Extract content
content = client.invoke_browser(
    browserIdentifier='aws.browser.v1',
    sessionId=session_id,
    action={'extract': {'selector': '.article-content'}}
)
```

**For Web Search Specifically:**
- Use Browser tool to navigate to search engines (Google, Bing, etc.)
- Extract search results from the page
- Parse and structure results for agent
- OR use custom tool with Tavily/Serper/NewsAPI APIs
- Browser tool is more flexible for discovering articles and real-time content

**What the Agent Does With Results:**
- Agent Core extracts structured data from browsed pages
- Parses HTML/DOM for relevant information
- Synthesizes findings into natural language response
- Can chain multiple page navigations for deeper research

#### 2. Code Interpreter (AWS Built-In)

**Tool ID:** `aws.codeinterpreter.v1`  
**Status:** Provided by AWS Agent Core Runtime  
**Implementation:** No custom code required — AWS manages the execution environment  
**How it works:** Agent Core provisions containerized code execution environments for secure code execution with configurable timeouts  
**Cost:** Included in Agent Core Runtime pricing  

**Execution Environment (Containerized within AgentCore):**
- **Technology:** Containerized execution within Amazon Bedrock AgentCore
- **Architecture:** Isolated container per session
- **Isolation:** Strict session isolation model
  - Containerized environment isolated from your local system
  - Isolated memory allocation per container
  - Isolated network namespace per session
  - Container terminated after session ends
- **Pre-installed:** Pre-built runtimes for multiple languages with common libraries

**Supported Languages:**
- Python
- JavaScript
- TypeScript

**API Operations:**
- `executeCode(language, code)` — Execute code in container
- `executeCommand(command)` — Run shell commands
- `readFiles()` — Read file contents
- `listFiles()` — List files in session storage
- `writeFiles()` — Create/modify files
- `removeFiles()` — Delete files

**Resource Constraints:**
- Default timeout: 15 minutes (900 seconds)
- Max timeout: 8 hours (28,800 seconds) — configurable
- File upload (inline): Up to 100 MB
- File upload (via S3): Up to 5 GB
- Filesystem: Temporary session storage (isolated per execution)
- Internet access: YES (can make API calls to external services)
- Multiple concurrent sessions supported
- Session isolation ensures security

**Usage Example:**
```json
{
  "tool_id": "aws.codeinterpreter.v1",
  "name": "code_interpreter",
  "description": "Execute code for data analysis, calculations, and visualization",
  "input": {
    "language": "python",
    "code": "import json\ndata = [{'title': 'Article 1', 'engagement': 4.2}, {'title': 'Article 2', 'engagement': 3.5}]\nanalysis = sum(d['engagement'] for d in data) / len(data)\nprint(f'Average engagement: {analysis:.2f}')"
  },
  "output": {
    "stdout": "Average engagement: 3.85",
    "stderr": "",
    "execution_time_ms": 245,
    "status": "success"
  }
}
```

**Python SDK Example:**
```python
import boto3
client = boto3.client('bedrock-agentcore', region_name='us-east-1')

# Start session (containerized execution environment provisioned)
session = client.start_code_interpreter_session(
    codeInterpreterIdentifier='aws.codeinterpreter.v1',
    name='analysis_session',
    sessionTimeoutSeconds=900  # Can extend to 28800 (8 hours)
)

session_id = session['sessionId']

# Execute code in the container
response = client.invoke_code_interpreter(
    codeInterpreterIdentifier='aws.codeinterpreter.v1',
    sessionId=session_id,
    name='executeCode',
    arguments={
        'language': 'python',
        'code': '''
import pandas as pd
import numpy as np

data = [
    {"title": "Article 1", "views": 1000, "likes": 50},
    {"title": "Article 2", "views": 1500, "likes": 75}
]
df = pd.DataFrame(data)
analysis = df.groupby('views').agg({'likes': 'mean'})
print(df.describe())
print(analysis)
'''
    }
)

print(response['output']['stdout'])
```

**Session Management:**
- Sessions require explicit start/stop
- `sessionTimeoutSeconds`: 900-28800 (15 min to 8 hours, configurable)
- `clientToken`: Prevents duplicate sessions on retries
- Multiple operations can share same session
- Session storage is temporary and isolated
- Container is automatically terminated when session ends

**What the Agent Does With Results:**
- Agent Core captures stdout/stderr from execution
- Returns results as structured JSON
- Agent interprets results and explains findings in natural language
- Can chain multiple code executions in same session for iterative analysis

---

### Custom Tools (We Must Build)

#### 3. Semantic Search (CUSTOM — Using Qdrant)

**Status:** Custom implementation REQUIRED  
**Purpose:** Search article embeddings in Qdrant for semantic similarity to user queries  
**Why Custom:** This tool bridges Agent Core with your existing Qdrant vector database and article data — AWS doesn't provide this out of the box  
**Implementation Required:**
- Build Python handler that integrates Qdrant client
- Register handler with Agent Core at runtime
- Handle embedding, searching, and result enrichment
- Return article metadata to agent for synthesis

**Implementation Details:**

```python
# backend/app/integrations/agent_core_client.py

class AgentCoreClient:
    """Client for Agent Core Runtime API calls"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url  # e.g., "http://agent-core-lb:8080"
        self.api_key = api_key
        self.http_client = httpx.AsyncClient()
    
    async def invoke_agent(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any],
        user_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Invoke Agent Core Runtime and stream responses
        """
        payload = {
            "session_id": session_id,
            "user_message": user_message,
            "context": {
                "user_id": user_id,
                "timestamp": int(time.time()),
                **context
            },
            "tools": [
                {
                    "tool_id": "web_search",
                    "enabled": True
                },
                {
                    "tool_id": "code_interpreter",
                    "enabled": True
                },
                {
                    "tool_id": "semantic_search",
                    "enabled": True,
                    "config": {
                        "embedding_service_url": self.embedding_service_url,
                        "qdrant_url": self.qdrant_url,
                        "top_k": 10,
                        "min_score": 0.6
                    }
                }
            ]
        }
        
        async with self.http_client.stream(
            "POST",
            f"{self.base_url}/v1/agents/invoke",
            json=payload,
            headers={"X-API-Key": self.api_key},
            timeout=60.0
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    try:
                        chunk = json.loads(line[6:])
                        yield chunk
                    except json.JSONDecodeError:
                        pass
```

**Semantic Search Tool Specification:**

```python
# backend/app/tools/semantic_search_tool.py

class SemanticSearchTool:
    """Custom tool for semantic article search via Agent Core"""
    
    def __init__(self, qdrant_client, embedding_service):
        self.qdrant_client = qdrant_client
        self.embedding_service = embedding_service
    
    async def execute(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.6,
        filters: Optional[Dict] = None
    ) -> List[ArticleResult]:
        """
        Search articles semantically using Qdrant embeddings
        
        Args:
            query: Natural language search query
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1)
            filters: DynamoDB filters (source, date range, etc.)
        
        Returns:
            List of relevant articles with scores
        """
        # 1. Embed query
        query_embedding = await self.embedding_service.embed_text(query)
        
        # 2. Search Qdrant
        search_results = await self.qdrant_client.search(
            collection_name="article_embeddings",
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=min_score
        )
        
        # 3. Fetch article metadata from DynamoDB
        article_ids = [hit.payload["article_id"] for hit in search_results]
        articles = await self.fetch_articles(article_ids)
        
        # 4. Enrich with relevance scores
        results = [
            ArticleResult(
                article_id=article.id,
                title=article.title,
                summary=article.summary,
                relevance_score=hit.score,
                source=article.source,
                url=article.url,
                published_at=article.published_at
            )
            for hit, article in zip(search_results, articles)
        ]
        
        return results

# Tool definition for Agent Core
SEMANTIC_SEARCH_TOOL_DEFINITION = {
    "tool_id": "semantic_search",
    "name": "semantic_search",
    "description": "Search article database semantically by meaning. Use this to find articles related to a topic.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query (e.g., 'recent AI breakthroughs', 'climate change solutions')"
            },
            "top_k": {
                "type": "integer",
                "description": "Number of results to return (default: 10, max: 50)",
                "default": 10
            },
            "min_score": {
                "type": "number",
                "description": "Minimum relevance score 0-1 (default: 0.6)",
                "default": 0.6
            }
        },
        "required": ["query"]
    },
    "output_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "article_id": {"type": "string"},
                        "title": {"type": "string"},
                        "summary": {"type": "string"},
                        "relevance_score": {"type": "number"},
                        "source": {"type": "string"},
                        "url": {"type": "string"},
                        "published_at": {"type": "number"}
                    }
                }
            },
            "total_results": {"type": "integer"}
        }
    }
}
```

**Tool Registration with Agent Core (REQUIRED):**

At Agent Core Runtime startup, register the semantic search custom tool:

```python
# backend/app/integrations/agent_core_client.py - Tool Registration

from backend.app.tools.semantic_search_tool import (
    SemanticSearchTool,
    SEMANTIC_SEARCH_TOOL_DEFINITION
)

class AgentCoreClient:
    """Client for Agent Core Runtime API calls"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.http_client = httpx.AsyncClient()
        self.qdrant_client = QdrantClient(url=QDRANT_URL)
        self.embedding_service = BedrockEmbedding()
    
    async def register_custom_tools(self):
        """Register custom tools with Agent Core Runtime"""
        # Initialize custom tool handlers
        semantic_search = SemanticSearchTool(
            qdrant_client=self.qdrant_client,
            embedding_service=self.embedding_service
        )
        
        # Register with Agent Core
        tools_config = [
            {
                **SEMANTIC_SEARCH_TOOL_DEFINITION,
                "handler": semantic_search  # Custom handler
            }
        ]
        
        # Send tool registration to Agent Core
        await self.http_client.post(
            f"{self.base_url}/v1/tools/register",
            json={"tools": tools_config},
            headers={"X-API-Key": self.api_key}
        )

# During FastAPI startup
@app.on_event("startup")
async def startup_agent_core():
    agent_core_client = AgentCoreClient(AGENT_CORE_URL, AGENT_CORE_API_KEY)
    await agent_core_client.register_custom_tools()
    app.state.agent_core = agent_core_client
```

**Key Points on Tool Registration:**
- **Built-in tools (Browser, Code Interpreter):** Already registered by AWS Agent Core — no action needed
- **Custom tools (Semantic Search):** Must be registered explicitly at startup
- **Tool invocation:** When user sends message, Agent Core automatically selects and invokes appropriate tools
- **Response handling:** Agent Core handles tool execution and streams results back to backend

---

## Agent Instance Isolation for Concurrent Users

**Critical Pattern:** Each user request must get its own isolated agent instance. Singleton agents cause deadlocks, race conditions, and shared state corruption when handling concurrent requests.

### The Problem: Singleton Pattern Deadlock

When a single global agent instance is shared across concurrent requests, multiple problems arise:

```
❌ BAD: Single global agent instance

Request 1 → Global Agent Instance ← Request 2
                 ↓
          Deadlock/Race condition
                 ↓
    One user's context overwrites another's

When two users send messages simultaneously:
- Shared state conflicts (message history, memory)
- Session interference (User A's context affects User B's response)
- Potential deadlocks (state machine locks)
- Memory/session contamination (messages leak between users)
- Unpredictable behavior (first request wins, second blocked)
```

**Real-world impact:**
- User A asks "Explain quantum computing"
- User B asks "What about AI safety?"
- If their requests overlap, User B's response might include quantum computing context
- Session state gets corrupted: messages belong to wrong users
- Requests timeout waiting for locks to release

### The Solution: Per-Request Instance Isolation

Create a fresh agent instance for each incoming request. Each request gets complete isolation:

```
✅ GOOD: Per-request agent instance

Request 1 → Agent Instance A (isolated) → Response 1
Request 2 → Agent Instance B (isolated) → Response 2

Each user gets fresh agent state:
- No shared state between requests
- No deadlocks or race conditions
- Full user session isolation
- Safe concurrent handling of 100+ simultaneous users
```

**Benefits:**
- Zero deadlock risk
- True session isolation (User A cannot see User B's messages)
- Linear scalability with load
- No state corruption
- Performance cost negligible (~1-2ms per instance creation)

### FastAPI Implementation: Dependency Injection Pattern

Use FastAPI's dependency injection to create fresh agent instances per request:

```python
from fastapi import FastAPI, Depends
from langchain.agents import AgentExecutor, create_react_agent
from langgraph.graph import StateGraph
from typing import AsyncGenerator

app = FastAPI()

# Expensive, shared resource (SAFE to share - stateless)
# Bedrock client is thread-safe and has no mutable state
shared_bedrock_client = Anthropic(api_key=BEDROCK_KEY)

# Per-request dependency - creates fresh instance for each request
def get_agent_for_request() -> AgentExecutor:
    """Creates a NEW agent instance for each request - ensures isolation"""
    
    # Define tools fresh for this request
    tools = [
        Tool(
            name="code_interpreter",
            func=execute_code,
            description="Execute Python code for analysis"
        ),
        Tool(
            name="browser",
            func=browse_web,
            description="Browse web pages and extract content"
        ),
        Tool(
            name="semantic_search",
            func=search_articles,
            description="Search articles semantically"
        )
    ]
    
    # Create fresh agent workflow for this request
    workflow = StateGraph(state_schema=AgentState)
    
    # Add nodes (fresh instances)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    
    # Define edges
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END}
    )
    workflow.add_edge("tools", "agent")
    
    # Compile to runnable graph
    agent_app = workflow.compile()
    
    return agent_app

@app.post("/api/v1/chat/message")
async def stream_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    agent = Depends(get_agent_for_request),  # ← Fresh instance per request
    bedrock_client = Depends(lambda: shared_bedrock_client)  # ← Shared (stateless)
):
    """Each request gets its own agent instance - no deadlock risk"""
    
    # Initialize state fresh for this request only
    state = AgentState(
        messages=[HumanMessage(content=request.user_message)],
        user_id=current_user.id,
        session_id=request.session_id,
        context={}
    )
    
    # Stream response - no state interference from other users
    async for event in agent.astream(state):
        if event.get('type') == 'token':
            yield {"data": json.dumps({"type": "token", "content": event['content']})}
        elif event.get('type') == 'tool_invocation':
            yield {"data": json.dumps({"type": "tool_invocation", **event})}
```

### Key Architectural Principles

| Principle | What | Why |
|-----------|------|-----|
| **Share:** | Bedrock client (stateless) | Thread-safe, no mutable state |
| **Create Fresh:** | Agent instance | Prevents deadlocks, isolation |
| **Per-Request:** | New workflow graph | No shared state across users |
| **Memory:** | Negligible (~1-2ms) | Agent creation is lightweight |
| **Safety:** | Eliminates race conditions | Each request is independent |

### Concurrency Comparison: Singleton vs Per-Request

```
┌────────────────────┬──────────────────┬─────────────────┐
│ Aspect             │ Singleton Agent  │ Per-Request     │
├────────────────────┼──────────────────┼─────────────────┤
│ Deadlock risk      │ ❌ HIGH          │ ✅ NONE         │
│ Race conditions    │ ❌ YES           │ ✅ NO           │
│ Memory per user    │ ⚠️ Shared        │ ✅ Isolated     │
│ User isolation     │ ❌ Poor          │ ✅ Perfect      │
│ Concurrent users   │ ❌ Limited (~5)  │ ✅ Unlimited    │
│ Code complexity    │ ✅ Simple        │ ⚠️ Slightly+    │
│ Performance        │ ✅ Fast          │ ✅ Same (~1-2ms)│
│ Horizontal scaling │ ❌ Difficult     │ ✅ Easy         │
│ No affinity needed │ ❌ Requires      │ ✅ YES          │
│ Load balancing     │ ⚠️ Sticky        │ ✅ Round-robin  │
└────────────────────┴──────────────────┴─────────────────┘
```

### Testing Concurrent Requests

```python
import asyncio
import httpx

async def test_concurrent_requests():
    """Test that 100 concurrent requests work without deadlock or interference"""
    
    async with httpx.AsyncClient() as client:
        tasks = [
            client.post(
                "http://localhost:8000/api/v1/chat/message",
                json={
                    "session_id": f"session-{i}",
                    "user_message": f"User {i}: Analyze this article about AI..."
                },
                headers={"Authorization": f"Bearer token-{i}"}
            )
            for i in range(100)
        ]
        
        # Execute all 100 requests concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        success_count = sum(1 for r in results if isinstance(r, httpx.Response) and r.status_code == 200)
        print(f"Successfully handled {success_count}/100 concurrent requests")
        
        # Check for interference (verify no message leakage)
        for i, result in enumerate(results):
            if isinstance(result, httpx.Response) and result.status_code == 200:
                response_text = result.text
                # Verify no other user's message appears in User i's response
                for j in range(100):
                    if i != j:
                        assert f"User {j}" not in response_text, \
                            f"User {i}'s response contains User {j}'s context!"
        
        print("✓ All requests isolated - no cross-contamination")
```

### Production Deployment Notes

**Load Balancer Configuration:**
- No sticky sessions required (requests are independent)
- Round-robin load balancing works perfectly
- Any backend instance can handle any request
- Horizontal scaling: add more instances, requests distribute automatically

**Database Connection Pooling:**
- No per-agent connection pooling needed
- Bedrock client handles connection pooling internally
- Each request reuses shared client (thread-safe)
- DynamoDB connection pool shared across all requests

**Session Management:**
- Sessions stored in DynamoDB (separate from agent state)
- Optimistic concurrency control (conditional writes)
- No locking needed between requests
- Session isolation via partition key (user_id) + sort key (session_id)

**Monitoring & Debugging:**
- Track concurrent request count in CloudWatch
- Monitor per-request agent creation time (should be ~1-2ms)
- Log request ID in all agent operations for tracing
- Alert if deadlock patterns detected (high p99 latency)

### Common Mistake: Using Global Agent Instance

❌ **WRONG:**
```python
# This causes deadlocks and race conditions!
agent = ChatbotAgent()  # Created once at startup

@app.post("/api/v1/chat/message")
async def chat(request: ChatRequest):
    # All users share same agent instance
    async for event in agent.stream_response(request.user_message):
        yield event
```

✅ **CORRECT:**
```python
def get_agent() -> ChatbotAgent:
    return ChatbotAgent()  # Fresh instance per request

@app.post("/api/v1/chat/message")
async def chat(
    request: ChatRequest,
    agent = Depends(get_agent)  # Fresh instance for this request
):
    # Each user gets isolated agent
    async for event in agent.stream_response(request.user_message):
        yield event
```

---

## API Design

### Backend Endpoints

#### 1. POST /api/v1/chat/message
Send a message to the chatbot and get a response (streaming).

**Request:**
```json
{
  "session_id": "sess-user123-0528",
  "user_message": "What are the latest AI breakthroughs in May 2026?",
  "context": {
    "preferred_sources": ["techcrunch", "arxiv"],
    "include_analysis": true
  }
}
```

**Response (Server-Sent Events Stream):**
```
event: token
data: {"content": "Based"}

event: token
data: {"content": " on"}

event: token
data: {"content": " recent"}

...

event: tool_invocation
data: {"tool_id": "semantic_search", "query": "AI breakthroughs May 2026", "status": "executing"}

event: tool_result
data: {"tool_id": "semantic_search", "results_count": 12, "top_result": "GPT-5 Training Complete"}

event: token
data: {"content": " articles"}

...

event: done
data: {"message_id": "msg-456", "total_tokens": 287}
```

**Implementation:**
```python
# backend/app/api/v1/chat/router.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from backend.app.integrations.agent_core_client import AgentCoreClient
from backend.app.services.chat_service import ChatService

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

@router.post("/message")
async def chat_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    agent_core: AgentCoreClient = Depends(),
    chat_service: ChatService = Depends()
):
    """
    Send a message to the chatbot
    Returns: Server-Sent Events stream of response tokens and tool invocations
    """
    
    # 1. Validate session ownership
    session = await chat_service.get_session(request.session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 2. Save user message
    user_msg = await chat_service.add_message(
        session_id=request.session_id,
        user_id=current_user.id,
        role="user",
        content=request.user_message
    )
    
    # 3. Stream response from Agent Core
    async def stream_response():
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        assistant_content = ""
        
        try:
            async for chunk in agent_core.invoke_agent(
                session_id=request.session_id,
                user_message=request.user_message,
                context=request.context or {},
                user_id=current_user.id
            ):
                if chunk["type"] == "token":
                    assistant_content += chunk["content"]
                    yield f"event: token\ndata: {json.dumps(chunk)}\n\n"
                
                elif chunk["type"] == "tool_invocation":
                    yield f"event: tool_invocation\ndata: {json.dumps(chunk)}\n\n"
                
                elif chunk["type"] == "tool_result":
                    yield f"event: tool_result\ndata: {json.dumps(chunk)}\n\n"
            
            # 4. Save assistant message
            await chat_service.add_message(
                session_id=request.session_id,
                user_id=current_user.id,
                role="assistant",
                content=assistant_content,
                message_id=message_id
            )
            
            yield f"event: done\ndata: {json.dumps({'message_id': message_id, 'tokens': len(assistant_content.split())})}\n\n"
        
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream"
    )
```

#### 2. GET /api/v1/chat/sessions
List all chat sessions for the current user.

**Request:**
```
GET /api/v1/chat/sessions?page=1&page_size=10&sort_by=recent
```

**Response:**
```json
{
  "sessions": [
    {
      "id": "sess-user123-0528",
      "title": "AI Breakthroughs Discussion",
      "created_at": 1717008000,
      "last_message_at": 1717010800,
      "message_count": 8,
      "preview": "What are the latest AI breakthroughs..."
    }
  ],
  "pagination": {
    "total": 24,
    "page": 1,
    "page_size": 10
  }
}
```

**Implementation:**
```python
@router.get("/sessions")
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    sort_by: str = Query("recent"),
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends()
):
    sessions = await chat_service.list_sessions(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        sort_by=sort_by
    )
    return {
        "sessions": sessions,
        "pagination": {
            "total": len(sessions),
            "page": page,
            "page_size": page_size
        }
    }
```

#### 3. POST /api/v1/chat/sessions
Create a new chat session.

**Request:**
```json
{
  "title": "AI Breakthroughs Discussion"
}
```

**Response:**
```json
{
  "id": "sess-user123-0528",
  "title": "AI Breakthroughs Discussion",
  "created_at": 1717008000
}
```

**Implementation:**
```python
@router.post("/sessions")
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends()
):
    session = await chat_service.create_session(
        user_id=current_user.id,
        title=request.title
    )
    return session
```

#### 4. GET /api/v1/chat/sessions/{session_id}
Retrieve full conversation history for a session.

**Request:**
```
GET /api/v1/chat/sessions/sess-user123-0528?page=1&page_size=20
```

**Response:**
```json
{
  "session_id": "sess-user123-0528",
  "title": "AI Breakthroughs Discussion",
  "created_at": 1717008000,
  "messages": [
    {
      "id": "msg-123",
      "role": "user",
      "content": "What are the latest AI breakthroughs?",
      "timestamp": 1717008100
    },
    {
      "id": "msg-124",
      "role": "assistant",
      "content": "Based on recent articles...",
      "timestamp": 1717008150,
      "tool_calls": [
        {
          "tool_id": "semantic_search",
          "query": "AI breakthroughs",
          "results": 12
        }
      ]
    }
  ],
  "pagination": {
    "total": 24,
    "page": 1,
    "page_size": 20
  }
}
```

---

## Streaming Implementation: Server-Sent Events (SSE)

### Why SSE for This Application

**Server-Sent Events (SSE)** is the optimal choice for streaming chat responses in the Tech News chatbot. Here's why:

1. **One-directional (Perfect for server → client streaming)**
   - Chatbot only needs to send tokens to the client
   - Client sends messages via REST POST, receives stream via SSE
   - No need for bidirectional communication

2. **Industry Standard**
   - OpenAI uses SSE for all streaming endpoints (ChatGPT, API)
   - Anthropic (Claude API) uses SSE for streaming responses
   - Google Gemini uses SSE for streaming
   - Well-documented, reliable, battle-tested at scale

3. **Simpler Than WebSocket**
   - No persistent connection state to manage
   - HTTP-based: works with existing infrastructure (load balancers, CDNs)
   - Automatic reconnection built into browser EventSource API
   - Stateless backend: scale horizontally without sticky sessions

4. **Better DynamoDB Scaling**
   - Sessions stored asynchronously AFTER streaming completes
   - No connection-level state in database
   - Each request is independent (horizontal scaling)
   - No need for connection pools or persistent WebSocket handlers

5. **Native Browser Support**
   - EventSource API built into all modern browsers
   - No external libraries required (fetch API handles everything)
   - Mobile-friendly (works on all browsers/devices)
   - Graceful fallback if JavaScript disabled

### SSE vs WebSocket Comparison

| Aspect | SSE | WebSocket |
|--------|-----|-----------|
| **Simplicity** | ✅ Simple | ❌ Complex |
| **Latency** | ⚠️ 5-10ms (typical) | ✅ 1-3ms (lowest) |
| **One-way streaming** | ✅ Perfect use case | ⚠️ Overkill |
| **Bidirectional comm** | ❌ Not designed for | ✅ Yes |
| **DynamoDB compat** | ✅ Great (async save) | ✅ Good (sync state) |
| **Industry standard** | ✅ OpenAI, Claude, Google | ⚠️ For agents, games |
| **HTTP compatible** | ✅ Yes | ❌ Protocol upgrade |
| **Load balancer friendly** | ✅ Stateless | ⚠️ Sticky sessions |
| **Reconnection** | ✅ Built-in (automatic) | ❌ Manual handling |
| **Browser support** | ✅ Native | ✅ Native |

**For this chatbot:** SSE is the clear choice. We only stream server → client, no bidirectional communication needed.

### Architecture Overview

```
User Interface (React/Next.js)
├─ fetch() POST to /api/v1/chat/message
├─ Receive response.body as ReadableStream
├─ Parse SSE events (token, tool_invocation, tool_result, done, error)
└─ Update UI in real-time as tokens arrive

FastAPI Backend (Port 8000)
├─ POST /api/v1/chat/message endpoint
├─ Validate auth & session
├─ Save user message to DynamoDB
├─ Stream tokens via EventSourceResponse
└─ Save assistant message after streaming completes

Agent Core Runtime (ECS/Managed)
├─ Receives invoke request
├─ Streams token events
├─ Invokes tools (web search, code interpreter, semantic search)
├─ Yields tool_invocation and tool_result events
└─ Returns final response tokens

DynamoDB (Sessions & Messages)
├─ Read message history BEFORE streaming
├─ Save user message IMMEDIATELY
├─ Stream response tokens to UI
└─ Save assistant message AFTER streaming ends
```

### Backend Implementation (FastAPI + Bedrock)

#### Endpoint with Streaming Response

```python
# backend/app/api/v1/chat/router.py

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from anthropic import Anthropic
import json
import uuid
import logging

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
logger = logging.getLogger(__name__)

class ChatMessageRequest(BaseModel):
    session_id: str
    user_message: str
    context: Optional[Dict[str, Any]] = None

@router.post("/message")
async def stream_chat_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(),
    anthropic_client: Anthropic = Depends()
):
    """
    Stream chat response as Server-Sent Events.
    
    Tokens arrive individually, allowing real-time UI updates.
    Tool invocations and results are streamed as events.
    Session is saved asynchronously after streaming completes.
    """
    
    # Validate session and get history
    session = await chat_service.get_session(request.session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages_history = await chat_service.get_messages(request.session_id)
    
    # Save user message immediately
    await chat_service.add_message(
        session_id=request.session_id,
        user_id=current_user.id,
        role="user",
        content=request.user_message
    )
    
    async def event_generator():
        try:
            response_text = ""
            message_id = f"msg-{uuid.uuid4().hex[:12]}"
            
            # Prepare messages for API
            api_messages = messages_history + [{
                "role": "user",
                "content": request.user_message
            }]
            
            # Stream response from Claude Haiku via Bedrock
            with anthropic_client.messages.stream(
                model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                max_tokens=1024,
                messages=api_messages
            ) as stream:
                for text in stream.text_stream:
                    response_text += text
                    
                    # Send token as SSE event
                    yield f"event: token\ndata: {json.dumps({"
                        "type": "token",
                        "content": text
                    })}\n\n"
            
            # Save assistant message to DynamoDB after streaming
            await chat_service.add_message(
                session_id=request.session_id,
                user_id=current_user.id,
                role="assistant",
                content=response_text,
                message_id=message_id
            )
            
            # Send completion event
            yield f"event: done\ndata: {json.dumps({"
                "type": "done",
                "message_id": message_id,
                "tokens": len(response_text.split())
            })}\n\n"
        
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({"
                "type": "error",
                "error": str(e)
            })}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

#### Tool Invocation Streaming with LangGraph

```python
# backend/app/api/v1/chat/router.py - Agent Core with tool streaming

from langgraph.graph import StateGraph, START, END
from langchain.schema import HumanMessage, AIMessage, ToolMessage
from typing import AsyncGenerator
from uuid import uuid4

@router.post("/message")
async def stream_chat_message_with_tools(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    chat_service: ChatService = Depends(),
    workflow: StateGraph = Depends()  # LangGraph workflow
):
    """
    Stream chat response with tool invocations as events.
    Uses LangGraph agent for multi-step reasoning.
    """
    
    session = await chat_service.get_session(request.session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages_history = await chat_service.get_messages(request.session_id)
    
    # Save user message
    await chat_service.add_message(
        session_id=request.session_id,
        user_id=current_user.id,
        role="user",
        content=request.user_message
    )
    
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            # Compile workflow to runnable
            app = workflow.compile()
            
            messages = messages_history + [
                HumanMessage(content=request.user_message)
            ]
            
            response_text = ""
            tool_calls_made = []
            message_id = f"msg-{uuid4().hex[:12]}"
            
            # Stream from agent
            async for event in app.astream(
                {"messages": messages},
                config={"run_id": str(uuid4())}
            ):
                # Process agent tokens
                if "agent" in event:
                    node_output = event["agent"]
                    if hasattr(node_output, "content"):
                        response_text += node_output.content
                        yield f"event: token\ndata: {json.dumps({"
                            "type": "token",
                            "content": node_output.content
                        })}\n\n"
                
                # Process tool invocations
                elif "tools" in event:
                    tools_output = event["tools"]
                    if hasattr(tools_output, "tool_calls"):
                        for tool_call in tools_output.tool_calls:
                            yield f"event: tool_invocation\ndata: {json.dumps({"
                                "type": "tool_invocation",
                                "tool_name": tool_call.get("name"),
                                "tool_args": tool_call.get("args"),
                                "tool_id": tool_call.get("id")
                            })}\n\n"
                            
                            tool_calls_made.append({
                                "tool_id": tool_call.get("id"),
                                "tool_name": tool_call.get("name"),
                                "status": "executing",
                                "args": tool_call.get("args")
                            })
                
                # Process tool results
                if "tool_result" in event:
                    result = event["tool_result"]
                    yield f"event: tool_result\ndata: {json.dumps({"
                        "type": "tool_result",
                        "tool_name": result.get("tool_name"),
                        "result_summary": result.get("summary"),
                        "status": "completed"
                    })}\n\n"
            
            # Save conversation to DynamoDB after streaming completes
            await chat_service.add_message(
                session_id=request.session_id,
                user_id=current_user.id,
                role="assistant",
                content=response_text,
                message_id=message_id,
                tool_calls=tool_calls_made
            )
            
            # Send completion event
            yield f"event: done\ndata: {json.dumps({"
                "type": "done",
                "message_id": message_id,
                "tokens": len(response_text.split()),
                "tools_invoked": len(tool_calls_made)
            })}\n\n"
        
        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({"
                "type": "error",
                "error": str(e),
                "error_code": "STREAMING_ERROR"
            })}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
            "Content-Encoding": "identity"  # Don't compress SSE
        }
    )
```

### Frontend Implementation (React/Next.js)

#### SSE Hook for Chat Streaming

```typescript
// frontend/src/hooks/useStreamChat.ts

import { useState, useCallback, useRef } from 'react';

export interface ChatMessage {
    id: string;
    role: 'user' | 'assistant' | 'tool' | 'error';
    content: string;
    timestamp: number;
    tool_calls?: ToolCall[];
}

export interface ToolCall {
    tool_id: string;
    tool_name: string;
    status: 'executing' | 'completed' | 'failed';
    args?: Record<string, any>;
    result?: any;
}

export interface SSEEvent {
    type: 'token' | 'tool_invocation' | 'tool_result' | 'done' | 'error';
    content?: string;
    tool_name?: string;
    tool_id?: string;
    tool_args?: Record<string, any>;
    message_id?: string;
    tokens?: number;
    error?: string;
}

export function useStreamChat() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    const sendMessage = useCallback(
        async (sessionId: string, userMessage: string) => {
            setIsLoading(true);
            setError(null);
            
            // Add user message to UI
            const userMsgId = `user-${Date.now()}`;
            setMessages(prev => [...prev, {
                id: userMsgId,
                role: 'user',
                content: userMessage,
                timestamp: Date.now()
            }]);

            abortControllerRef.current = new AbortController();

            try {
                const response = await fetch('/api/v1/chat/message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        session_id: sessionId,
                        user_message: userMessage
                    }),
                    signal: abortControllerRef.current.signal
                });

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const reader = response.body!.getReader();
                const decoder = new TextDecoder();
                let assistantContent = '';
                let assistantId = '';
                let buffer = '';

                // Initialize assistant message
                setMessages(prev => [...prev, {
                    id: `assistant-${Date.now()}`,
                    role: 'assistant',
                    content: '',
                    timestamp: Date.now()
                }]);

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    
                    // Keep last incomplete line in buffer
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const event: SSEEvent = JSON.parse(line.slice(6));
                                
                                if (event.type === 'token') {
                                    assistantContent += event.content || '';
                                    
                                    // Update last assistant message
                                    setMessages(prev => {
                                        const messages = [...prev];
                                        const lastMsg = messages[messages.length - 1];
                                        if (lastMsg?.role === 'assistant') {
                                            lastMsg.content = assistantContent;
                                        }
                                        return messages;
                                    });
                                } 
                                else if (event.type === 'tool_invocation') {
                                    setMessages(prev => [...prev, {
                                        id: `tool-${event.tool_id}-${Date.now()}`,
                                        role: 'tool',
                                        content: `🔧 Calling ${event.tool_name}...`,
                                        timestamp: Date.now(),
                                        tool_calls: [{
                                            tool_id: event.tool_id || '',
                                            tool_name: event.tool_name || '',
                                            status: 'executing',
                                            args: event.tool_args
                                        }]
                                    }]);
                                } 
                                else if (event.type === 'tool_result') {
                                    setMessages(prev => [...prev, {
                                        id: `tool-result-${event.tool_name}-${Date.now()}`,
                                        role: 'tool',
                                        content: `✓ ${event.tool_name}: Task completed`,
                                        timestamp: Date.now()
                                    }]);
                                } 
                                else if (event.type === 'done') {
                                    assistantId = event.message_id || '';
                                } 
                                else if (event.type === 'error') {
                                    setError(event.error || 'Unknown error occurred');
                                    setMessages(prev => [...prev, {
                                        id: `error-${Date.now()}`,
                                        role: 'error',
                                        content: `❌ Error: ${event.error}`,
                                        timestamp: Date.now()
                                    }]);
                                }
                            } catch (parseError) {
                                console.error('Failed to parse SSE event:', parseError);
                            }
                        }
                    }
                }
            } catch (err) {
                if (err instanceof Error && err.name === 'AbortError') {
                    console.log('Chat request cancelled');
                } else {
                    const errorMsg = err instanceof Error ? err.message : 'Chat error';
                    setError(errorMsg);
                    console.error('Chat error:', err);
                }
            } finally {
                setIsLoading(false);
                abortControllerRef.current = null;
            }
        },
        []
    );

    const cancelMessage = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            setIsLoading(false);
        }
    }, []);

    return { messages, isLoading, error, sendMessage, cancelMessage };
}
```

#### Chat Interface Component

```typescript
// frontend/src/components/ChatInterface.tsx

import React, { useState, useRef, useEffect } from 'react';
import { useStreamChat, ChatMessage as ChatMessageType } from '../hooks/useStreamChat';

interface ChatInterfaceProps {
    sessionId: string;
    sessionTitle?: string;
}

export function ChatInterface({ sessionId, sessionTitle }: ChatInterfaceProps) {
    const { messages, isLoading, error, sendMessage, cancelMessage } = useStreamChat();
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userInput = input;
        setInput('');
        await sendMessage(sessionId, userInput);
    };

    return (
        <div className="chat-interface">
            <div className="chat-header">
                <h2>{sessionTitle || 'New Chat'}</h2>
            </div>

            <div className="messages-container">
                {messages.length === 0 ? (
                    <div className="empty-state">
                        <h3>Start a conversation</h3>
                        <p>Ask me anything about tech news, articles, or analysis.</p>
                    </div>
                ) : (
                    messages.map(msg => (
                        <ChatMessage key={msg.id} message={msg} />
                    ))
                )}

                {error && (
                    <div className="error-message">
                        <strong>Error:</strong> {error}
                    </div>
                )}

                {isLoading && (
                    <div className="loading-indicator">
                        <div className="spinner" />
                        <span>Assistant is typing...</span>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            <form onSubmit={handleSubmit} className="input-form">
                <div className="input-wrapper">
                    <textarea
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyPress={e => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmit(e as any);
                            }
                        }}
                        placeholder="Type your message (Shift+Enter for new line)..."
                        disabled={isLoading}
                        rows={3}
                    />
                    <div className="button-group">
                        <button
                            type="submit"
                            disabled={isLoading || !input.trim()}
                            className="send-button"
                        >
                            {isLoading ? 'Sending...' : 'Send'}
                        </button>
                        {isLoading && (
                            <button
                                type="button"
                                onClick={cancelMessage}
                                className="cancel-button"
                            >
                                Cancel
                            </button>
                        )}
                    </div>
                </div>
                <p className="input-hint">
                    I can search articles, analyze data, and answer questions about tech news.
                </p>
            </form>
        </div>
    );
}

// Individual message component
interface ChatMessageProps {
    message: ChatMessageType;
}

function ChatMessage({ message }: ChatMessageProps) {
    return (
        <div className={`chat-message ${message.role}`}>
            <div className="message-avatar">
                {message.role === 'user' && '👤'}
                {message.role === 'assistant' && '🤖'}
                {message.role === 'tool' && '🔧'}
                {message.role === 'error' && '⚠️'}
            </div>

            <div className="message-content">
                <p className="message-text">{message.content}</p>

                {message.tool_calls && message.tool_calls.length > 0 && (
                    <div className="tool-calls">
                        {message.tool_calls.map((call, idx) => (
                            <div key={idx} className="tool-call">
                                <span className="tool-icon">
                                    {call.status === 'executing' ? '⏳' : '✓'}
                                </span>
                                <span className="tool-name">{call.tool_name}</span>
                                {call.args && (
                                    <span className="tool-args">
                                        ({JSON.stringify(call.args).substring(0, 50)}...)
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                )}

                <div className="message-time">
                    {new Date(message.timestamp).toLocaleTimeString()}
                </div>
            </div>
        </div>
    );
}
```

### Error Handling Strategy

```python
# backend/app/api/v1/chat/router.py - Error handling

async def event_generator():
    message_id = f"msg-{uuid.uuid4().hex[:12]}"
    assistant_content = ""
    
    try:
        # Save user message
        await chat_service.add_message(
            session_id=request.session_id,
            user_id=current_user.id,
            role="user",
            content=request.user_message
        )
        
        # Stream response
        async for event in stream_source:
            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
            if event['type'] == 'token':
                assistant_content += event.get('content', '')
        
        # Save successful response
        await chat_service.add_message(
            session_id=request.session_id,
            user_id=current_user.id,
            role="assistant",
            content=assistant_content,
            message_id=message_id
        )
    
    except asyncio.TimeoutError:
        logger.error(f"Streaming timeout: {request.session_id}")
        yield f"event: error\ndata: {json.dumps({
            "type": "error",
            "error": "Response took too long",
            "code": "TIMEOUT"
        })}\n\n"
    
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        yield f"event: error\ndata: {json.dumps({
            "type": "error",
            "error": "Invalid request",
            "code": "VALIDATION_ERROR"
        })}\n\n"
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        yield f"event: error\ndata: {json.dumps({
            "type": "error",
            "error": "An unexpected error occurred",
            "code": "INTERNAL_ERROR"
        })}\n\n"
```

### Event Types Definition

```
SSE Event Types:

1. token
   - Sent continuously while streaming text
   - Contains: {"type": "token", "content": "word"}
   - Use: Append to current message

2. tool_invocation
   - Sent when agent calls a tool
   - Contains: {"type": "tool_invocation", "tool_name": "semantic_search", "tool_args": {...}}
   - Use: Show "Calling tool_name..." indicator

3. tool_result
   - Sent after tool completes
   - Contains: {"type": "tool_result", "tool_name": "semantic_search", "result_summary": "..."}
   - Use: Show "✓ tool_name completed" indicator

4. done
   - Final event before stream closes
   - Contains: {"type": "done", "message_id": "msg-xyz", "tokens": 287}
   - Use: Mark conversation as complete, enable input

5. error
   - Sent if error occurs during streaming
   - Contains: {"type": "error", "error": "...", "code": "TIMEOUT"}
   - Use: Show error message to user, enable retry
```

### DynamoDB Session Integration

**Key Pattern:**
1. ✅ Fetch messages BEFORE streaming (for context window)
2. ✅ Save user message IMMEDIATELY (before streaming starts)
3. ✅ Stream response tokens to UI (real-time)
4. ✅ Save assistant message AFTER streaming completes (async)
5. ✅ No connection-level state in database

```python
# Flow in /api/v1/chat/message endpoint:

async def stream_chat_message(...):
    # Step 1: Read messages before streaming
    messages_history = await chat_service.get_messages(request.session_id)
    
    # Step 2: Save user message immediately
    await chat_service.add_message(
        session_id=request.session_id,
        role="user",
        content=request.user_message
    )
    
    async def event_generator():
        # Step 3: Stream tokens
        async for chunk in agent.stream(...):
            yield f"event: token\ndata: {chunk}\n\n"
        
        # Step 4: Save assistant message after streaming
        await chat_service.add_message(
            session_id=request.session_id,
            role="assistant",
            content=full_response_text
        )
        
        # Step 5: Send done event
        yield f"event: done\ndata: ...\n\n"
    
    return StreamingResponse(event_generator())
```

### Testing SSE Streaming

```bash
# Test endpoint directly with curl
curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "session_id": "sess-test-001",
    "user_message": "What are the latest AI breakthroughs?"
  }'

# Should see:
# event: token
# data: {"type": "token", "content": "Based"}
#
# event: token
# data: {"type": "token", "content": " on"}
# ...
# event: tool_invocation
# data: {"type": "tool_invocation", "tool_name": "semantic_search", ...}
#
# event: done
# data: {"type": "done", "message_id": "msg-abc123", "tokens": 287}
```

---

## Database Schema

### DynamoDB: tech-news-conversation_sessions Table

```
Partition Key: user_id (String)
Sort Key: session_id (String)

Attributes:
- user_id (String, PK)
- session_id (String, SK)
  └─ Format: "sess-{user_id}-{random}"
- title (String)
  └─ User-provided or auto-generated from first message
- created_at (Number, unix timestamp)
- last_message_at (Number, unix timestamp)
- message_count (Number)
  └─ Total messages in session (cache for performance)
- preview (String)
  └─ First 200 chars of first user message
- status (String)
  └─ "active", "archived"
- ttl (Number)
  └─ 90 days from creation (30-day session + 60-day archive)

Global Secondary Index:
- user_id-last_message_at-index
  └─ For sorting by recency
```

### DynamoDB: tech-news-conversation_messages Table

```
Partition Key: session_id (String)
Sort Key: message_id (String)

Attributes:
- session_id (String, PK)
- message_id (String, SK)
  └─ Format: "msg-{random}"
- user_id (String)
  └─ For access control validation
- role (String)
  └─ "user", "assistant"
- content (String)
  └─ Full message text
- tokens (Number)
  └─ Approximate token count
- timestamp (Number, unix timestamp)
- tool_calls (List<Object>)
  └─ Array of tool invocations:
  └─ [
       {
         "tool_id": "semantic_search",
         "query": "AI breakthroughs",
         "status": "success",
         "results_count": 12,
         "execution_time_ms": 250
       }
     ]
- ttl (Number)
  └─ Same as session TTL (90 days)

Index:
- session_id-timestamp-index
  └─ For ordered message retrieval
```

### DynamoDB: tech-news-chat_user_preferences Table

```
Partition Key: user_id (String)

Attributes:
- user_id (String, PK)
- preferred_sources (List<String>)
  └─ ["techcrunch", "arxiv", "wired"]
- include_analysis (Boolean)
  └─ Include code interpreter for data analysis
- max_results_per_search (Number)
  └─ Default: 10
- theme (String)
  └─ "light", "dark"
- updated_at (Number, unix timestamp)
```

---

## Frontend Components

### Chatbot UI Components

#### 1. Navbar Chatbot Tab
```tsx
// frontend/src/components/Navbar.tsx

<nav className="navbar">
  {/* Existing tabs */}
  <NavLink to="/home">Home</NavLink>
  <NavLink to="/explore">Explore</NavLink>
  <NavLink to="/topics">Topics</NavLink>
  
  {/* NEW: Chatbot tab */}
  <NavLink 
    to="/chatbot"
    className="nav-link chatbot-tab"
    icon={<MessageCircle />}
  >
    Chatbot
  </NavLink>
  
  <NavLink to="/search">Search</NavLink>
  <NavLink to="/profile">Profile</NavLink>
</nav>
```

#### 2. Chatbot Page Layout

```tsx
// frontend/src/pages/ChatbotPage.tsx

export function ChatbotPage() {
  const [sessions, setSessions] = useState([])
  const [currentSession, setCurrentSession] = useState(null)
  const [isCreating, setIsCreating] = useState(false)

  return (
    <div className="chatbot-page">
      {/* Left Sidebar: Session List */}
      <aside className="chatbot-sidebar">
        <div className="sidebar-header">
          <h2>Conversations</h2>
          <Button
            onClick={() => setIsCreating(true)}
            icon={<Plus />}
          >
            New Chat
          </Button>
        </div>

        <SessionList
          sessions={sessions}
          activeSession={currentSession}
          onSelectSession={setCurrentSession}
        />
      </aside>

      {/* Main Content: Chat Interface */}
      <main className="chatbot-main">
        {currentSession ? (
          <ChatInterface session={currentSession} />
        ) : (
          <EmptyState onNewChat={() => setIsCreating(true)} />
        )}
      </main>

      {/* Modal: Create New Session */}
      {isCreating && (
        <CreateSessionModal
          onCreate={(session) => {
            setSessions([session, ...sessions])
            setCurrentSession(session)
            setIsCreating(false)
          }}
          onClose={() => setIsCreating(false)}
        />
      )}
    </div>
  )
}
```

#### 3. Chat Interface Component

```tsx
// frontend/src/components/ChatInterface.tsx

interface ChatInterfaceProps {
  session: ChatSession
}

export function ChatInterface({ session }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const handleSendMessage = async () => {
    if (!inputText.trim()) return

    // Add user message
    const userMsg = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: inputText,
      timestamp: Date.now()
    }
    setMessages(prev => [...prev, userMsg])
    setInputText("")
    setIsLoading(true)

    try {
      // Stream response from backend
      const eventSource = new EventSource(
        `/api/v1/chat/message?session_id=${session.id}&message=${encodeURIComponent(inputText)}`
      )

      let assistantContent = ""

      eventSource.addEventListener("token", (event) => {
        const data = JSON.parse(event.data)
        assistantContent += data.content

        // Update last message in real-time
        setMessages(prev => {
          const last = prev[prev.length - 1]
          if (last?.role === "assistant") {
            return [
              ...prev.slice(0, -1),
              { ...last, content: assistantContent }
            ]
          }
          return prev
        })
      })

      eventSource.addEventListener("tool_invocation", (event) => {
        const data = JSON.parse(event.data)
        // Show tool invocation in UI
        console.log(`Tool: ${data.tool_id} - ${data.status}`)
      })

      eventSource.addEventListener("done", (event) => {
        const data = JSON.parse(event.data)
        eventSource.close()
        setIsLoading(false)
        scrollToBottom()
      })

      eventSource.addEventListener("error", (event) => {
        eventSource.close()
        setIsLoading(false)
      })
    } catch (error) {
      console.error("Chat error:", error)
      setIsLoading(false)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  return (
    <div className="chat-interface">
      {/* Messages Container */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <ChatWelcome onSuggestClick={setInputText} />
        ) : (
          messages.map(msg => (
            <ChatMessage key={msg.id} message={msg} />
          ))
        )}
        {isLoading && <ChatLoading />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="input-area">
        <div className="input-wrapper">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSendMessage()
              }
            }}
            placeholder="Ask me anything..."
            disabled={isLoading}
          />
          <Button
            onClick={handleSendMessage}
            disabled={isLoading || !inputText.trim()}
            icon={<Send />}
          >
            Send
          </Button>
        </div>
        <p className="input-hint">
          I can search articles, analyze data, and answer questions.
        </p>
      </div>
    </div>
  )
}
```

#### 4. Chat Message Component

```tsx
// frontend/src/components/ChatMessage.tsx

interface ChatMessageProps {
  message: Message
}

export function ChatMessage({ message }: ChatMessageProps) {
  return (
    <div className={`chat-message ${message.role}`}>
      <div className="message-avatar">
        {message.role === "user" ? <User /> : <Bot />}
      </div>

      <div className="message-content">
        <div className="message-text">
          {/* Render markdown with syntax highlighting */}
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Show tool invocations if present */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="tool-calls">
            {message.tool_calls.map((call, idx) => (
              <div key={idx} className="tool-call">
                <span className="tool-name">{call.tool_id}</span>
                <span className="tool-status">
                  {call.status === "success" ? "✓" : "○"}
                </span>
                {call.results_count && (
                  <span className="tool-results">
                    {call.results_count} results
                  </span>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="message-time">
          {formatTime(message.timestamp)}
        </div>
      </div>
    </div>
  )
}
```

#### 5. Liquid Glass Styling

```css
/* frontend/src/styles/chatbot.css */

.chatbot-interface {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  min-height: 100vh;
  display: flex;
  gap: 1px;
}

.chatbot-sidebar {
  width: 280px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border-right: 1px solid rgba(255, 255, 255, 0.3);
  padding: 16px;
  overflow-y: auto;
}

.chatbot-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 0;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-message {
  display: flex;
  gap: 12px;
  animation: slideIn 0.3s ease-out;
}

.chat-message.user {
  justify-content: flex-end;
}

.message-content {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.chat-message.user .message-content {
  background: rgba(59, 130, 246, 0.1);
  border-color: rgba(59, 130, 246, 0.3);
}

.input-area {
  padding: 16px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(255, 255, 255, 0.3);
}

.input-wrapper {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}

.input-wrapper textarea {
  flex: 1;
  padding: 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  resize: none;
  max-height: 120px;
  font-family: inherit;
}

.input-wrapper textarea:focus {
  outline: none;
  border-color: rgba(59, 130, 246, 0.5);
  background: rgba(255, 255, 255, 1);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Dark mode */
@media (prefers-color-scheme: dark) {
  .chatbot-interface {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  }

  .chatbot-sidebar,
  .input-area {
    background: rgba(30, 30, 46, 0.8);
    border-color: rgba(255, 255, 255, 0.1);
  }

  .message-content {
    background: rgba(255, 255, 255, 0.08);
    color: #e0e0e0;
  }

  .input-wrapper textarea {
    background: rgba(50, 50, 70, 0.9);
    color: #e0e0e0;
    border-color: rgba(255, 255, 255, 0.15);
  }
}
```

#### 6. Session List Component

```tsx
// frontend/src/components/SessionList.tsx

interface SessionListProps {
  sessions: ChatSession[]
  activeSession: ChatSession | null
  onSelectSession: (session: ChatSession) => void
}

export function SessionList({
  sessions,
  activeSession,
  onSelectSession
}: SessionListProps) {
  return (
    <div className="session-list">
      {sessions.length === 0 ? (
        <p className="empty-message">No conversations yet</p>
      ) : (
        sessions.map(session => (
          <div
            key={session.id}
            className={`session-item ${
              activeSession?.id === session.id ? "active" : ""
            }`}
            onClick={() => onSelectSession(session)}
          >
            <div className="session-title">{session.title}</div>
            <div className="session-preview">{session.preview}</div>
            <div className="session-time">
              {formatTime(session.last_message_at)}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
```

---

## Implementation Plan

### Week 1: Terraform & Agent Core Infrastructure
- [ ] Set up ECS cluster for Agent Core Runtime
- [ ] Configure load balancer (internal)
- [ ] Create IAM roles and security groups
- [ ] Deploy Agent Core Runtime service (2 replicas)
- [ ] Verify health checks passing
- [ ] Test API connectivity from backend VPC

### Week 2: Backend FastAPI Integration
- [ ] Create DynamoDB tables (sessions, messages, preferences)
- [ ] Implement AgentCoreClient (HTTP API wrapper)
- [ ] Create ChatService (CRUD operations, business logic)
- [ ] Build FastAPI endpoints (/chat/message, /chat/sessions, etc.)
- [ ] Implement streaming response handling
- [ ] Add authentication & authorization checks
- [ ] Write unit tests for all endpoints

### Week 3: Frontend Chatbot Component
- [ ] Create ChatbotPage component
- [ ] Build ChatInterface with message rendering
- [ ] Implement SessionList component
- [ ] Add streaming SSE listener
- [ ] Create chat message components
- [ ] Add liquid glass styling (CSS)
- [ ] Responsive design for mobile/tablet

### Week 4: Tool Integration & Testing
- [ ] Register semantic search tool with Agent Core
- [ ] Implement SemanticSearchTool class
- [ ] Test tool invocation end-to-end
- [ ] Verify web search (AWS built-in) works
- [ ] Test code interpreter (AWS built-in)
- [ ] Integration tests: message → tool call → response
- [ ] Performance testing (response latency, concurrency)

### Week 5: Polish & Optimization
- [ ] Error handling improvements
- [ ] User feedback on tool execution
- [ ] Session management (create, list, delete)
- [ ] Add suggested prompts for new sessions
- [ ] Implement session search
- [ ] Add session export (export conversation as JSON/PDF)
- [ ] Optimize DynamoDB queries (add indexes if needed)

### Week 6: Integration Testing & Deployment
- [ ] End-to-end testing (create session → send message → get response)
- [ ] Load testing (concurrent users)
- [ ] Accessibility audit (a11y)
- [ ] Security audit (auth, data validation)
- [ ] Deployment to staging
- [ ] Smoke tests in staging
- [ ] Deployment to production
- [ ] Monitor for 48 hours (errors, latency, user feedback)

---

## Deployment

### Terraform Apply Order
```bash
# 1. Apply Agent Core infrastructure
terraform apply -target=module.agent_core

# 2. Verify Agent Core is running
aws ecs describe-services --cluster agent-core-cluster --services agent-core-service

# 3. Test Agent Core API health
curl -H "X-API-Key: $AGENT_CORE_API_KEY" http://agent-core-lb:8080/health

# 4. Apply backend changes
terraform apply -target=module.backend

# 5. Deploy FastAPI container
./deploy-backend.sh

# 6. Verify endpoints
curl http://localhost:8000/api/v1/chat/sessions
```

### Pre-Deployment Checklist
- [ ] Agent Core Runtime service is healthy
- [ ] DynamoDB tables are created with correct schemas
- [ ] IAM roles have necessary permissions
- [ ] VPC security groups allow traffic (backend → Agent Core)
- [ ] Backend can reach Agent Core Runtime endpoint
- [ ] FastAPI tests pass locally
- [ ] Frontend builds without errors

### Rollback Plan
- If Agent Core fails: Scale down ECS service, revert to previous AMI
- If FastAPI fails: Revert container image, restart service
- If DynamoDB issue: Restore from backup snapshot
- If frontend fails: Revert to previous build, clear browser cache

---

## Integration with Existing Systems

### Data Reuse
- **Articles:** Query existing `articles` table for semantic search
- **Embeddings:** Reuse existing embedding service (Bedrock)
- **User Auth:** Leverage existing JWT authentication

### API Design Consistency
- Follow existing REST conventions (`/api/v1/...`)
- Use existing error handling & pagination patterns
- Match existing response schemas

### UI Consistency
- Use existing color scheme (liquid glass, dark mode)
- Follow existing navbar structure
- Reuse existing components (Button, Modal, etc.)

---

## Success Metrics

### Performance
- Agent Core response time: < 3 seconds p95
- API response time: < 1 second p95
- Frontend message rendering: < 100ms

### Adoption
- 10% of daily active users try chatbot in first month
- 30% of chatbot users create follow-up messages
- Average session length: 5+ messages

### Quality
- Tool invocation success rate: > 95%
- User satisfaction: > 4.0/5.0 (survey)
- Error rate: < 0.1%

---

## Notes

- **No Lambda deployment needed:** Agent Core Runtime is a separate managed service
- **Short-term memory only:** Sessions don't persist across chat instances
- **Streaming responses:** Server-Sent Events for real-time token delivery
- **Tool orchestration:** Agent Core handles all tool routing automatically
- **Semantic search integration:** Custom tool bridges Agent Core with Qdrant
- **AWS-native:** Uses Agent Core Runtime (AWS-managed), Bedrock for Claude Haiku (us.anthropic.claude-haiku-4-5-20251001-v1:0), Browser Tool (containerized within AgentCore) for web navigation, Code Interpreter (containerized within AgentCore) for safe code execution
- **Model consistency:** All LLM inference uses Haiku model via Bedrock for cost efficiency and fast inference

