# CLI Process Manager - Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│  (generate_application, build endpoints, etc.)                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Process Manager Integration Layer                   │
│  (repository_tools.py - generate_application function)           │
│                                                                   │
│  1. Check limit: can_start_process()                             │
│  2. Start CLI subprocess                                         │
│  3. Register PID: register_process(pid)                          │
│  4. Monitor process                                              │
│  5. Unregister PID: unregister_process(pid)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Process Manager Core Layer                          │
│  (process_manager.py)                                            │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ CLIProcessManager (Singleton)                            │   │
│  │                                                          │   │
│  │ - active_pids: Set[int]                                 │   │
│  │ - max_concurrent_processes: int = 5                     │   │
│  │ - _lock: asyncio.Lock                                   │   │
│  │                                                          │   │
│  │ Methods:                                                │   │
│  │ • can_start_process()                                   │   │
│  │ • register_process(pid)                                 │   │
│  │ • unregister_process(pid)                               │   │
│  │ • get_active_count()                                    │   │
│  │ • get_active_pids()                                     │   │
│  │ • _cleanup_dead_processes()                             │   │
│  │ • kill_all_processes()                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Monitoring & Control Layer                          │
│  (process_monitor.py)                                            │
│                                                                   │
│  - get_process_status()                                          │
│  - kill_all_cli_processes()                                      │
│  - get_process_limit()                                           │
│  - set_process_limit()                                           │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Starting a Build

```
User Request
    │
    ▼
generate_application()
    │
    ├─→ Check: can_start_process()?
    │   │
    │   ├─ YES: Continue
    │   └─ NO: Return error, exit
    │
    ├─→ Start CLI subprocess
    │   │
    │   └─ Get process.pid
    │
    ├─→ Register: register_process(pid)
    │   │
    │   ├─ Check limit
    │   ├─ Add to active_pids
    │   └─ Return success/failure
    │
    ├─→ Monitor process in background
    │   │
    │   └─ _monitor_build_process()
    │
    └─→ Return immediately with task_id
```

### Process Completion

```
Process exits (normal, silent, or timeout)
    │
    ▼
_monitor_build_process() detects completion
    │
    ├─→ Unregister: unregister_process(pid)
    │   │
    │   └─ Remove from active_pids
    │
    ├─→ Update BackgroundTask status
    │
    └─→ Next process can now start
```

## Concurrency Model

### Thread Safety

```
Multiple concurrent requests
    │
    ├─→ Request 1: can_start_process()
    │   │
    │   └─→ Acquire lock
    │       ├─ Check count < max
    │       └─ Release lock
    │
    ├─→ Request 2: register_process(pid)
    │   │
    │   └─→ Acquire lock
    │       ├─ Cleanup dead processes
    │       ├─ Check count < max
    │       ├─ Add to active_pids
    │       └─ Release lock
    │
    └─→ Request 3: get_active_count()
        │
        └─→ Acquire lock
            ├─ Cleanup dead processes
            ├─ Return count
            └─ Release lock
```

### Lock Strategy

- **Async Lock**: `asyncio.Lock()` for async-safe operations
- **Scope**: Minimal - only held during critical sections
- **Cleanup**: Happens inside lock to ensure consistency
- **No Deadlocks**: Single lock, no nested acquisitions

## State Management

### Active PIDs Set

```
┌─────────────────────────────────┐
│ active_pids: Set[int]           │
│                                 │
│ {1234, 1235, 1236, ...}         │
│                                 │
│ Operations:                     │
│ • add(pid)                      │
│ • discard(pid)                  │
│ • len() for count               │
│ • copy() for snapshot           │
└─────────────────────────────────┘
```

### Cleanup Logic

```
_cleanup_dead_processes():
    │
    ├─→ For each pid in active_pids:
    │   │
    │   └─→ Check: os.kill(pid, 0)
    │       │
    │       ├─ Success: Process alive, keep it
    │       └─ Failure: Process dead, remove it
    │
    └─→ Update active_pids set
```

## Configuration

### Default Settings

```python
CLIProcessManager(max_concurrent_processes=5)
```

### Runtime Adjustment

```python
process_manager.max_concurrent_processes = 10
```

### Singleton Pattern

```python
# First call creates instance
manager1 = get_process_manager(max_concurrent=5)

# Subsequent calls return same instance
manager2 = get_process_manager(max_concurrent=10)

# manager1 is manager2 → True
# max_concurrent parameter ignored on subsequent calls
```

## Error Handling

### Limit Exceeded

```
generate_application()
    │
    └─→ can_start_process() → False
        │
        └─→ Return error message:
            "Cannot start build: maximum concurrent CLI processes (5) 
             reached. Please wait for existing builds to complete."
```

### Registration Failure

```
generate_application()
    │
    ├─→ Start subprocess
    │
    └─→ register_process(pid) → False
        │
        ├─→ Terminate process
        │
        └─→ Return error message:
            "Cannot start build: process limit exceeded. 
             Please try again."
```

## Monitoring Integration

### Status Reporting

```
get_process_status()
    │
    └─→ Returns:
        {
            'active_processes': 3,
            'max_allowed': 5,
            'active_pids': [1234, 1235, 1236],
            'can_start_new': True,
            'utilization_percent': 60
        }
```

### Emergency Control

```
kill_all_cli_processes()
    │
    ├─→ Get all active PIDs
    │
    ├─→ For each PID:
    │   └─→ os.kill(pid, 9)  # SIGKILL
    │
    └─→ Clear active_pids set
```

## Performance Characteristics

| Operation | Time | Space |
|-----------|------|-------|
| can_start_process() | O(n) | O(1) |
| register_process() | O(n) | O(1) |
| unregister_process() | O(1) | O(1) |
| get_active_count() | O(n) | O(1) |
| get_active_pids() | O(n) | O(n) |
| _cleanup_dead_processes() | O(n) | O(1) |

*n = number of active processes (typically 1-5)*

## Testing Strategy

```
Unit Tests (test_process_manager.py)
    │
    ├─→ Registration Tests
    │   ├─ Within limit
    │   └─ Exceeds limit
    │
    ├─→ Limit Tests
    │   ├─ can_start_process()
    │   └─ Enforcement
    │
    ├─→ Cleanup Tests
    │   └─ Dead process removal
    │
    ├─→ Concurrency Tests
    │   └─ Thread safety
    │
    └─→ Singleton Tests
        └─ Instance consistency
```

## Integration Summary

### Functions Using Process Manager

The process manager is integrated into **two main CLI invocation functions**:

#### 1. `generate_application()` (application/agents/shared/repository_tools.py)
- **Purpose**: Full application generation from scratch
- **Integration Points**:
  - Line ~1329: Check limit before starting
  - Line ~1349: Register process after start
  - Line ~1768: Unregister on normal completion
  - Line ~1836: Unregister on silent exit detection
  - Line ~1981: Unregister on timeout

#### 2. `generate_code_with_cli()` (application/agents/github/tools.py)
- **Purpose**: Incremental code generation (entities, workflows, etc.)
- **Integration Points**:
  - Line ~2588: Check limit before starting
  - Line ~2618: Register process after start
  - Line ~2255: Unregister on normal completion
  - Line ~2383: Unregister on silent exit detection
  - Line ~2422: Unregister on timeout

### Integration Pattern

Both functions follow the same pattern:

```python
# 1. Check limit before starting
process_manager = get_process_manager()
if not await process_manager.can_start_process():
    return f"ERROR: Cannot start: maximum concurrent processes reached"

# 2. Start subprocess
process = await asyncio.create_subprocess_exec(...)

# 3. Register process
if not await process_manager.register_process(process.pid):
    await _terminate_process(process)
    return f"ERROR: Process limit exceeded"

# 4. Monitor in background
monitoring_task = asyncio.create_task(_monitor_process(...))

# 5. Unregister on completion (in monitoring function)
# - Normal completion
# - Silent exit detection
# - Timeout
await process_manager.unregister_process(pid)
```

## Future Enhancements

1. **Metrics Collection**: Track process lifecycle events
2. **Process Priorities**: Queue-based scheduling
3. **Timeout Configuration**: Per-build timeout settings
4. **Webhooks**: Notifications on limit exceeded
5. **Persistent State**: Save/restore process state
6. **Process Groups**: Manage related processes together

