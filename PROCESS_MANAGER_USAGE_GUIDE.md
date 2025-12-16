# CLI Process Manager - Usage Guide

## Quick Start

### 1. Check Current Status

```python
from application.agents.shared.process_monitor import get_process_status

status = await get_process_status()
print(f"Active: {status['active_processes']}/{status['max_allowed']}")
print(f"Utilization: {status['utilization_percent']}%")
print(f"Can start new: {status['can_start_new']}")
```

### 2. Adjust Process Limit

```python
from application.agents.shared.process_monitor import set_process_limit

# Increase limit to 10
result = await set_process_limit(10)
print(f"Limit changed: {result['old_limit']} → {result['new_limit']}")
```

### 3. Emergency: Kill All Processes

```python
from application.agents.shared.process_monitor import kill_all_cli_processes

result = await kill_all_cli_processes()
print(f"Killed {result['killed_count']} processes: {result['killed_pids']}")
```

## Integration Points

### In API Endpoints

```python
from fastapi import FastAPI
from application.agents.shared.process_monitor import (
    get_process_status,
    set_process_limit,
    kill_all_cli_processes
)

app = FastAPI()

@app.get("/api/process-status")
async def process_status():
    """Get current CLI process status."""
    return await get_process_status()

@app.post("/api/process-limit")
async def update_limit(max_concurrent: int):
    """Update the process limit."""
    return await set_process_limit(max_concurrent)

@app.post("/api/process-kill-all")
async def kill_all():
    """Emergency: kill all CLI processes."""
    return await kill_all_cli_processes()
```

### In Monitoring/Logging

```python
import logging
from application.agents.shared.process_monitor import get_process_status

logger = logging.getLogger(__name__)

async def log_process_status():
    """Log current process status periodically."""
    status = await get_process_status()
    logger.info(
        f"Process Status: {status['active_processes']}/{status['max_allowed']} "
        f"({status['utilization_percent']}%) - "
        f"Can start: {status['can_start_new']}"
    )
```

### In Health Checks

```python
from application.agents.shared.process_monitor import get_process_status

async def health_check():
    """Health check including process status."""
    status = await get_process_status()
    
    # Warn if utilization is high
    if status['utilization_percent'] > 80:
        return {
            "status": "warning",
            "message": "High process utilization",
            "details": status
        }
    
    return {
        "status": "healthy",
        "details": status
    }
```

## Monitoring Dashboard

### Example Metrics to Track

```python
from application.agents.shared.process_monitor import get_process_status

async def collect_metrics():
    """Collect metrics for monitoring dashboard."""
    status = await get_process_status()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "active_processes": status['active_processes'],
        "max_allowed": status['max_allowed'],
        "utilization_percent": status['utilization_percent'],
        "can_start_new": status['can_start_new'],
        "active_pids": status['active_pids'],
    }
```

## Troubleshooting

### Issue: "Cannot start build: maximum concurrent CLI processes reached"

**Solution 1: Wait for existing builds**
- Check status: `await get_process_status()`
- Wait for processes to complete

**Solution 2: Increase limit**
```python
from application.agents.shared.process_monitor import set_process_limit
await set_process_limit(10)  # Increase from default 5
```

**Solution 3: Kill stuck processes**
```python
from application.agents.shared.process_monitor import kill_all_cli_processes
await kill_all_cli_processes()  # Emergency only!
```

### Issue: Process count not decreasing

**Cause**: Dead processes not cleaned up
**Solution**: Cleanup happens automatically on next `can_start_process()` or `get_active_count()` call

### Issue: Want to monitor specific process

```python
from application.agents.shared.process_manager import get_process_manager

manager = get_process_manager()
pids = await manager.get_active_pids()
print(f"Active PIDs: {pids}")

# Check if specific PID is active
if 12345 in pids:
    print("Process 12345 is still running")
```

## Configuration

### Default Settings

```python
# Default: 5 concurrent processes
from application.agents.shared.process_manager import get_process_manager
manager = get_process_manager()
print(f"Max concurrent: {manager.max_concurrent_processes}")
```

### Custom Initialization

```python
# Set custom limit on first call
from application.agents.shared.process_manager import get_process_manager
manager = get_process_manager(max_concurrent=10)
```

### Runtime Adjustment

```python
# Change limit at runtime
from application.agents.shared.process_monitor import set_process_limit
await set_process_limit(15)
```

## Best Practices

1. **Check before starting**: Always call `can_start_process()` before spawning
2. **Register immediately**: Register PID right after process creation
3. **Unregister on exit**: Always unregister when process completes
4. **Monitor regularly**: Log status periodically for visibility
5. **Set appropriate limit**: Balance between concurrency and resource usage
6. **Use emergency kill sparingly**: Only use `kill_all_processes()` when necessary

## Performance Considerations

- **Cleanup overhead**: Minimal - only checks PIDs that are registered
- **Lock contention**: Low - locks are held briefly
- **Memory usage**: Negligible - just stores PIDs in a set
- **CPU usage**: Negligible - no polling, event-driven

## Testing

```bash
# Run all tests
pytest application/agents/shared/tests/test_process_manager.py -v

# Run specific test
pytest application/agents/shared/tests/test_process_manager.py::test_register_process_within_limit -v

# Run with coverage
pytest application/agents/shared/tests/test_process_manager.py --cov=application.agents.shared.process_manager
```

