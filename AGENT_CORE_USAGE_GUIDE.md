# Agent Core Memory Usage Guide

## Quick Start

### 1. Using Agent Core Memory in Route Handlers

```python
from fastapi import APIRouter, Depends
from app.integrations.agent_core_memory import AgentCoreMemory
from app.api.dependencies import get_agent_memory

router = APIRouter()

@router.post("/conversation/message")
async def send_message(
    session_id: str,
    user_id: str,
    message: str,
    memory: AgentCoreMemory = Depends(get_agent_memory)
):
    """
    Send a message and store it in Agent Core memory.
    
    FastAPI automatically:
    1. Creates a fresh AgentCoreMemory instance for this request
    2. Passes it to the handler
    3. Cleans it up after the response
    
    No singleton = no cross-request contamination
    """
    
    # Initialize memory for this session (loads prior context from DB)
    await memory.initialize_memory(session_id, user_id)
    
    # Log the user's message
    await memory.log_message(session_id, "user", message)
    
    # Get conversation history for context
    context = await memory.get_memory_context(session_id)
    
    # Process the message...
    response = await process_with_agent_core(message, context)
    
    # Log the assistant's response
    await memory.log_message(session_id, "assistant", response)
    
    return {"response": response}
```

## API Reference

### AgentCoreMemory Class

#### `__init__()`
Initializes memory with:
- Type: SHORT_TERM
- Retention: 90 days
- TTL: 7,776,000 seconds

#### `initialize_memory(session_id, user_id, recent_events=None)`
Initialize memory for a conversation session.

**Parameters:**
- `session_id` (str): Unique session identifier
- `user_id` (str): User identifier
- `recent_events` (list, optional): Prior events loaded from Agent Core DB

**Returns:**
```python
{
    "status": "initialized",
    "session_id": "sess-001",
    "user_id": "user-123",
    "memory_type": "SHORT_TERM",
    "event_count": 5,  # Number of loaded events
    "retention_days": 90
}
```

**Example:**
```python
# Load with no prior context
result = await memory.initialize_memory("sess-001", "user-123")

# Load with prior events from DB
recent_events = [
    {
        "event_id": "evt-1",
        "role": "user",
        "content": "Previous message",
        "timestamp": 1234567890.0
    },
    ...
]
result = await memory.initialize_memory(
    "sess-001", "user-123", 
    recent_events=recent_events
)
```

#### `log_message(session_id, role, content, timestamp=None)`
Log a message to memory.

**Parameters:**
- `session_id` (str): Session identifier
- `role` (str): "user" or "assistant"
- `content` (str): Message content
- `timestamp` (float, optional): Unix timestamp (defaults to current time)

**Returns:**
```python
{
    "status": "logged",
    "event_id": "uuid-string",
    "role": "user",
    "timestamp": 1234567890.5,
    "session_id": "sess-001"
}
```

**Example:**
```python
# Log current message
result = await memory.log_message(
    "sess-001", "user", "What is Agent Core?"
)

# Log with custom timestamp
result = await memory.log_message(
    "sess-001", "assistant", "Agent Core stores...",
    timestamp=1234567891.0
)
```

#### `get_memory_context(session_id)`
Retrieve the full conversation history for a session.

**Parameters:**
- `session_id` (str): Session identifier

**Returns:** List of events sorted by timestamp
```python
[
    {
        "event_id": "evt-1",
        "role": "user",
        "content": "First message",
        "timestamp": 1000.0,
        "session_id": "sess-001"
    },
    {
        "event_id": "evt-2",
        "role": "assistant",
        "content": "First response",
        "timestamp": 1001.0,
        "session_id": "sess-001"
    },
    ...
]
```

**Example:**
```python
context = await memory.get_memory_context("sess-001")
print(f"Conversation has {len(context)} messages")

for event in context:
    print(f"{event['role']}: {event['content']}")
```

#### `get_memory_events(session_id, limit=None)`
Get memory events with optional limit.

**Parameters:**
- `session_id` (str): Session identifier
- `limit` (int, optional): Maximum number of events to return

**Returns:** List of events (last N if limit provided)

**Example:**
```python
# Get last 10 messages
recent = await memory.get_memory_events("sess-001", limit=10)

# Get all messages
all_events = await memory.get_memory_events("sess-001")
```

#### `get_session_summary(session_id)`
Get summary statistics for a session.

**Returns:**
```python
{
    "session_id": "sess-001",
    "total_events": 10,
    "user_messages": 5,
    "assistant_messages": 5,
    "retention_days": 90,
    "memory_type": "SHORT_TERM"
}
```

#### `clear_old_memory(session_id)`
Clean up expired messages (older than 90 days).

**Returns:**
```python
{
    "status": "cleared",
    "session_id": "sess-001",
    "removed_count": 2,
    "remaining_count": 8
}
```

#### `delete_session_memory(session_id)`
Delete all memory for a session.

**Returns:**
```python
{
    "status": "deleted",
    "session_id": "sess-001",
    "deleted_count": 10
}
```

#### `validate_event_structure(event)`
Validate an event dictionary.

**Parameters:**
- `event` (dict): Event to validate

**Returns:** True if valid, raises ValueError otherwise

**Example:**
```python
event = {
    "role": "user",
    "content": "Message",
    "timestamp": 1234567890.0,
    "session_id": "sess-001"
}

is_valid = await memory.validate_event_structure(event)
```

## Per-Request Isolation Explanation

### Problem: Singleton Pattern
```python
# BAD - Singleton causes state leakage
_memory_instance = None

def get_agent_memory():
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = AgentCoreMemory()
    return _memory_instance

# Request 1          Request 2
# get_agent_memory() gets SAME instance
# Session 1 data visible to Session 2!
```

### Solution: Per-Request Isolation
```python
# GOOD - Fresh instance per request
def get_agent_memory():
    return AgentCoreMemory()  # New instance every time

# FastAPI's Depends() system handles:
# - Creating fresh instance for each request
# - Type-safe injection
# - Automatic cleanup after response

# Request 1                Request 2
# get_agent_memory() →    get_agent_memory() →
# Instance A (isolated)   Instance B (isolated)
```

## Configuration

### Agent Core Settings (backend/app/config.py)
```python
class Settings(BaseSettings):
    # Agent Core Memory
    agent_memory_type: str = "SHORT_TERM"
    agent_memory_retention_days: int = 90  # 90-day TTL
```

### Environment Variables
```bash
# Optional - defaults are shown
AGENT_MEMORY_TYPE=SHORT_TERM
AGENT_MEMORY_RETENTION_DAYS=90
```

## Testing

### Unit Tests
```bash
pytest backend/tests/test_agent_core_memory.py -v
```

### Integration Tests
```bash
pytest backend/tests/test_agent_core_memory_integration.py -v
```

### Validation Tests (Task CHT-004)
```bash
pytest backend/tests/test_agent_core_validation.py -v
```

## Common Patterns

### Pattern 1: Chat Session
```python
@router.post("/chat")
async def chat(
    session_id: str,
    user_id: str,
    message: str,
    memory: AgentCoreMemory = Depends(get_agent_memory)
):
    await memory.initialize_memory(session_id, user_id)
    await memory.log_message(session_id, "user", message)
    
    context = await memory.get_memory_context(session_id)
    response = await call_agent(message, context)
    
    await memory.log_message(session_id, "assistant", response)
    return {"response": response}
```

### Pattern 2: Session Recovery
```python
@router.get("/conversation/{session_id}")
async def get_conversation(
    session_id: str,
    user_id: str,
    memory: AgentCoreMemory = Depends(get_agent_memory),
    db = Depends(get_db)
):
    # Load prior events from DynamoDB
    recent_events = db.get_session_events(session_id, limit=50)
    
    # Initialize memory with prior context
    await memory.initialize_memory(session_id, user_id, recent_events)
    
    # Return conversation
    context = await memory.get_memory_context(session_id)
    return {"messages": context}
```

### Pattern 3: Multi-Turn with TTL
```python
@router.post("/conversation/{session_id}/cleanup")
async def cleanup_old_messages(
    session_id: str,
    memory: AgentCoreMemory = Depends(get_agent_memory)
):
    # Remove messages older than 90 days
    result = await memory.clear_old_memory(session_id)
    
    return {
        "removed": result["removed_count"],
        "remaining": result["remaining_count"]
    }
```

## Performance Notes

- **Memory Type**: SHORT_TERM - optimized for conversation context
- **Retention**: 90 days matches DynamoDB retention policy
- **TTL**: 7,776,000 seconds (90 days * 86,400 sec/day)
- **Per-Request**: No singleton = each request is isolated and thread-safe

## Troubleshooting

### Issue: "Session not initialized" error
```python
# WRONG - forgot to initialize
await memory.log_message("sess-001", "user", "message")

# CORRECT - initialize first
await memory.initialize_memory("sess-001", "user-123")
await memory.log_message("sess-001", "user", "message")
```

### Issue: Seeing other session's messages
```python
# This can't happen - each request gets its own instance!
# If it does, check that memory is injected via Depends()
# NOT created as a global singleton
```

### Issue: Messages not persisting
```python
# Remember: In-memory store is per-request
# To persist across requests, save to DynamoDB:

# After session, save to DB
await db.save_session_events(session_id, await memory.get_memory_context(session_id))

# Next request, load from DB
recent_events = await db.get_session_events(session_id)
await memory.initialize_memory(session_id, user_id, recent_events)
```

## References

- **AgentCoreMemory**: `backend/app/integrations/agent_core_memory.py`
- **FastAPI Dependency**: `backend/app/api/dependencies.py`
- **Configuration**: `backend/app/config.py`
- **Tests**: `backend/tests/test_agent_core_*.py`
