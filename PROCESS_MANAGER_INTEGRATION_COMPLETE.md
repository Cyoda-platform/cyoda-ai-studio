# Process Manager Integration - Complete

## Overview

The CLI Process Manager has been successfully integrated into **both** CLI invocation functions:

1. **`generate_application()`** - Full application generation
2. **`generate_code_with_cli()`** - Incremental code generation

## Integration Summary

### generate_application()
**File**: `application/agents/shared/repository_tools.py`

- ✅ Line ~1329: Check process limit before starting
- ✅ Line ~1349: Register process after successful start
- ✅ Line ~1768: Unregister on normal completion
- ✅ Line ~1836: Unregister on silent exit detection
- ✅ Line ~1981: Unregister on timeout

### generate_code_with_cli()
**File**: `application/agents/github/tools.py`

- ✅ Line ~2588: Check process limit before starting
- ✅ Line ~2618: Register process after successful start
- ✅ Line ~2255: Unregister on normal completion
- ✅ Line ~2383: Unregister on silent exit detection
- ✅ Line ~2422: Unregister on timeout

## Integration Pattern

Both functions follow the same pattern:

```python
# 1. Check limit
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
await process_manager.unregister_process(pid)
```

## Verification

✅ Code compiles without errors
✅ All tests pass (8/8)
✅ No syntax errors
✅ Proper error handling
✅ Consistent behavior across both functions

## Benefits

- **Unified Process Management**: Both functions use the same process manager
- **Resource Protection**: Prevents resource exhaustion from concurrent CLI processes
- **Automatic Cleanup**: Dead processes are automatically cleaned up
- **Observable Status**: Process status can be monitored via API
- **Emergency Control**: Can kill all processes if needed
- **Consistent Limits**: Same limit applies to all CLI invocations

## Testing

```bash
pytest application/agents/shared/tests/test_process_manager.py -v
# Result: 8 passed in 5.85s
```

## Documentation

- `PROCESS_MANAGER.md` - Updated with both functions
- `PROCESS_MANAGER_ARCHITECTURE.md` - Added integration summary
- `PROCESS_MANAGER_USAGE_GUIDE.md` - Usage examples

## Status

✅ **COMPLETE** - Process manager is now integrated into both CLI functions

