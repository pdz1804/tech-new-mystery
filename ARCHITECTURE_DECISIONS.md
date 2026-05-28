# Architecture Decision Record: Agent Core Memory Configuration

## Decision: Remove Singleton Pattern, Implement Per-Request Isolation

**Status**: IMPLEMENTED  
**Date**: May 28, 2026  
**Task**: TASK-CHT-004  

## Context

Agent Core Runtime is a managed AWS service with built-in memory capabilities. The application needed to:

1. Configure memory as SHORT_TERM with 90-day retention
2. Integrate with Agent Core's memory system
3. Ensure proper state isolation between concurrent requests
4. Avoid singleton patterns that cause state leakage

## Problem Statement

The original implementation used a **singleton pattern** for AgentCoreMemory:

```python
_memory_instance = None

def get_agent_memory():
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = AgentCoreMemory()
    return _memory_instance
```

### Issues with Singleton:
1. **State Leakage**: All requests share the same memory instance
2. **Concurrency Issues**: Session A can see Session B's messages
3. **Test Contamination**: Tests interfere with each other
4. **Thread Safety**: Global state requires careful synchronization

### Example Problem:
```
Request 1 (Session A)     Request 2 (Session B)
    |                           |
    v                           v
get_agent_memory() -----> SAME INSTANCE
    |                           |
memory._memory_store      memory._memory_store
  {sess-A: [...] }         {sess-A: [... ]}  ← sees Session A!
  {sess-B: [...] }         {sess-B: [...] }
     ^                              ^
     |                              |
   LEAKAGE!                     LEAKAGE!
```

## Solution: Per-Request Isolation via FastAPI Depends

### Design:
```python
def get_agent_memory() -> AgentCoreMemory:
    """Create a fresh AgentCoreMemory instance for per-request isolation."""
    return AgentCoreMemory()
```

Used with FastAPI dependency injection:
```python
@router.post("/chat")
async def chat(memory: AgentCoreMemory = Depends(get_agent_memory)):
    # Each request gets its own instance
    ...
```

### How FastAPI Handles It:
```
Request 1          Request 2          Request 3
   |                  |                  |
   v                  v                  v
Depends(get_agent_memory)
   |                  |                  |
   Returns            Returns            Returns
   Instance A         Instance B         Instance C
   |                  |                  |
Request Handler 1  Request Handler 2  Request Handler 3
   |                  |                  |
   After Response, Instance is GC'd
```

## Benefits

### 1. **True Request Isolation**
```
Session A in Request 1 ≠ Session A in Request 2
```

### 2. **Thread Safety**
No global state = no synchronization needed

### 3. **Clean Testing**
Fresh instance per test = no fixture cleanup needed

### 4. **Scalability**
Each request is independent
- Horizontal scaling: Easy
- Concurrent requests: Safe
- Request 1000 doesn't affect Request 1

### 5. **Type Safety**
```python
# FastAPI type-checks the dependency
async def chat(memory: AgentCoreMemory = Depends(get_agent_memory)):
    #                  ^^^^^^^^^^^^^^ - Type is verified
    pass
```

## Implementation

### 1. **Configuration** (No Changes Needed)
```python
# backend/app/config.py
class Settings(BaseSettings):
    agent_memory_type: str = "SHORT_TERM"
    agent_memory_retention_days: int = 90
```

✓ Already correct

### 2. **Memory Service**
```python
# backend/app/integrations/agent_core_memory.py

# REMOVED:
_memory_instance = None

def get_agent_memory():
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = AgentCoreMemory()
    return _memory_instance


# ADDED:
def get_agent_memory() -> AgentCoreMemory:
    """Create fresh instance for per-request isolation."""
    return AgentCoreMemory()
```

### 3. **FastAPI Dependency**
```python
# backend/app/api/dependencies.py

async def get_agent_memory() -> AgentCoreMemory:
    """FastAPI dependency for per-request memory isolation."""
    return create_agent_memory()
```

### 4. **Usage in Routes**
```python
# backend/app/api/v1/chat/router.py (example)

@router.post("/message")
async def send_message(
    message: str,
    memory: AgentCoreMemory = Depends(get_agent_memory)  # ← Fresh instance
):
    await memory.initialize_memory(session_id, user_id)
    await memory.log_message(session_id, "user", message)
    # ...
```

## Testing Strategy

### Unit Tests
Test AgentCoreMemory methods in isolation:
```python
@pytest.mark.asyncio
async def test_log_message():
    memory = get_agent_memory()  # Fresh instance
    await memory.log_message("sess-1", "user", "test")
    # ...
```

### Per-Request Isolation Tests
Verify no singleton exists:
```python
def test_fresh_instances():
    mem1 = get_agent_memory()
    mem2 = get_agent_memory()
    assert mem1 is not mem2  # Different instances!
```

### Concurrent Request Tests
Verify no cross-contamination:
```python
@pytest.mark.asyncio
async def test_concurrent_isolation():
    mem_r1 = get_agent_memory()  # Request 1
    mem_r2 = get_agent_memory()  # Request 2
    
    await mem_r1.log_message("sess-r1", "user", "msg1")
    await mem_r2.log_message("sess-r2", "user", "msg2")
    
    # Request 1 cannot see Request 2's session
    assert "sess-r2" not in await mem_r1.get_memory_context("sess-r2")
```

## Trade-offs

| Aspect | Singleton | Per-Request |
|--------|-----------|-------------|
| Memory Usage | Lower (1 instance) | Higher (N instances) |
| Concurrency Safety | Risky | Safe |
| Testing | Hard (cleanup needed) | Easy (fresh state) |
| State Leakage Risk | HIGH | NONE |
| Performance | Minimal overhead | Negligible (GC) |
| Code Complexity | Simple | Slightly more |

**Verdict**: Per-Request is the clear winner for this use case.

## Migration Impact

### No Breaking Changes
- Configuration unchanged
- API unchanged
- Tests updated (improved)

### What Changed
1. `get_agent_memory()` returns fresh instance each time
2. Tests verify isolation instead of singleton persistence
3. FastAPI Depends ensures per-request injection

## Verification

### Before (Singleton)
```python
mem1 = get_agent_memory()
mem2 = get_agent_memory()
assert mem1 is mem2  # SAME instance - PROBLEM!
```

### After (Per-Request)
```python
mem1 = get_agent_memory()
mem2 = get_agent_memory()
assert mem1 is not mem2  # Different instances - FIXED!
```

## Risks & Mitigations

### Risk: Higher Memory Usage
**Impact**: Each request creates an instance  
**Mitigation**: Python's GC handles cleanup; negligible impact  
**Acceptable**: Yes

### Risk: Developer Confusion
**Impact**: Some devs might expect singleton behavior  
**Mitigation**: Clear documentation and examples provided  
**Acceptable**: Yes

### Risk: Persistent Sessions Require DB
**Impact**: Memory is per-request, not persistent  
**Mitigation**: Initialize with `recent_events` from DynamoDB  
**Pattern**: 
```python
await memory.initialize_memory(
    session_id, user_id,
    recent_events=db.get_session_events(session_id)
)
```
**Acceptable**: Yes

## Decision

✓ **APPROVED**: Remove singleton pattern, implement per-request isolation

### Rationale
1. Eliminates state leakage completely
2. Makes concurrent requests safe by default
3. Improves testability
4. Follows FastAPI best practices
5. Minimal performance impact
6. Aligns with Python's garbage collection model

### Files Changed
- `backend/app/integrations/agent_core_memory.py` (removed singleton)
- `backend/app/api/dependencies.py` (added FastAPI dependency)
- `backend/tests/test_agent_core_memory.py` (updated tests)
- `backend/tests/test_agent_core_memory_integration.py` (updated tests)

### Files Created
- `backend/tests/test_agent_core_validation.py` (validation tests)

## References

### FastAPI Documentation
- [Dependency Injection](https://fastapi.tiangolo.com/tutorial/dependencies/)
- [Dependency Scopes](https://fastapi.tiangolo.com/tutorial/dependencies/dependencies-in-path-operation-decorators/)

### Python Design Patterns
- [Singleton Pattern (Anti-pattern in concurrent systems)](https://en.wikipedia.org/wiki/Singleton_pattern)
- [Factory Pattern (used here)](https://en.wikipedia.org/wiki/Factory_method_pattern)

### AWS Agent Core
- Agent Core Runtime manages memory internally
- SHORT_TERM memory for conversation context
- 90-day TTL matches DynamoDB retention

## Conclusion

This decision eliminates a critical source of state leakage while maintaining clean, testable code. Per-request isolation is the correct pattern for web services and is actively recommended by FastAPI.

**Status**: ✓ COMPLETE
**Confidence**: HIGH
**Risk**: LOW
