# CLI Process Manager

## Overview

The CLI Process Manager monitors and limits the number of concurrent Augment CLI processes to prevent resource exhaustion and runaway builds.

## Features

- **PID Tracking**: Maintains a registry of all active CLI process IDs
- **Concurrency Limiting**: Enforces a maximum number of concurrent processes (default: 5)
- **Dead Process Cleanup**: Automatically removes PIDs of processes that have exited
- **Thread-Safe**: Uses asyncio locks for safe concurrent access
- **Singleton Pattern**: Global instance ensures consistent state across the application

## Usage

### Basic Usage in Code

```python
from application.agents.shared.process_manager import get_process_manager

# Get the global process manager
process_manager = get_process_manager()

# Check if a new process can be started
if await process_manager.can_start_process():
    # Start your CLI process
    process = await asyncio.create_subprocess_exec(...)
    
    # Register the process
    if await process_manager.register_process(process.pid):
        # Process registered successfully
        pass
    else:
        # Limit exceeded, terminate process
        await process.terminate()

# When process completes
await process_manager.unregister_process(process.pid)
```

### Monitoring Status

```python
from application.agents.shared.process_monitor import get_process_status

# Get current status
status = await get_process_status()
print(f"Active processes: {status['active_processes']}/{status['max_allowed']}")
print(f"Utilization: {status['utilization_percent']}%")
print(f"Can start new: {status['can_start_new']}")
```

### Emergency Shutdown

```python
from application.agents.shared.process_monitor import kill_all_cli_processes

# Forcefully terminate all active CLI processes
result = await kill_all_cli_processes()
print(f"Killed {result['killed_count']} processes")
```

### Adjusting Limits

```python
from application.agents.shared.process_monitor import set_process_limit

# Change the maximum concurrent processes
result = await set_process_limit(10)
print(f"Limit changed from {result['old_limit']} to {result['new_limit']}")
```

## Configuration

### Default Limit

The default maximum concurrent processes is **5**. This can be changed:

```python
from application.agents.shared.process_manager import get_process_manager

# Initialize with custom limit (only works on first call)
process_manager = get_process_manager(max_concurrent=10)

# Or change after initialization
await set_process_limit(10)
```

### Environment Variable

You can set the limit via environment variable (if implemented):

```bash
export CLI_MAX_CONCURRENT_PROCESSES=10
```

## Integration Points

### In `generate_application()` (Full App Generation)

The process manager is integrated into the build process:

1. **Before starting CLI**: Check if limit allows new process
2. **After starting CLI**: Register the process PID
3. **On completion**: Unregister the process PID
4. **On timeout**: Unregister and terminate the process

### In `generate_code_with_cli()` (Incremental Code Generation)

The process manager is also integrated into incremental code generation:

1. **Before starting CLI**: Check if limit allows new process
2. **After starting CLI**: Register the process PID
3. **On completion**: Unregister the process PID
4. **On timeout**: Unregister and terminate the process

### Error Handling

When the limit is exceeded:

```
ERROR: Cannot start build: maximum concurrent CLI processes (5) reached.
Please wait for existing builds to complete.
```

Or for code generation:

```
ERROR: Cannot start code generation: maximum concurrent CLI processes (5) reached.
Please wait for existing builds to complete.
```

## Monitoring and Debugging

### View Active Processes

```python
pids = await process_manager.get_active_pids()
count = await process_manager.get_active_count()
print(f"Active PIDs: {pids}")
print(f"Count: {count}")
```

### Check Process Alive Status

```python
is_alive = process_manager._is_process_alive(pid)
```

## Testing

Run the test suite:

```bash
pytest application/agents/shared/tests/test_process_manager.py -v
```

Tests cover:
- Process registration within limits
- Limit enforcement
- Process unregistration
- Dead process cleanup
- Concurrent access safety

