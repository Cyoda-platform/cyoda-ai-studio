# CLI Process Error Recovery Guide

This guide explains how the automatic error recovery system works and how to manually retry failed code generation tasks.

## Overview

The system now includes:
1. **Automatic Error Classification** - Identifies if errors are retryable
2. **Circuit Breaker** - Prevents cascading failures
3. **Task Metadata** - Tracks error details for informed retry decisions
4. **Manual Retry Tool** - Allows users to retry failed tasks

---

## How It Works Automatically

### When a CLI Process Fails:

1. **Error Classification**
   - System analyzes exit code and log files
   - Classifies error as: `transient`, `recoverable`, or `permanent`
   - Stores classification in task metadata

2. **Task Update**
   - Task marked as `failed`
   - Error details stored with:
     - `error_type`: Classification of the error
     - `error_description`: Human-readable explanation
     - `is_retryable`: Boolean indicating if retry is recommended
     - `exit_code`: Process exit code
     - `timeout_occurred`: Whether timeout caused failure

3. **Circuit Breaker Tracking**
   - Failure recorded in circuit breaker
   - After 3 failures: Circuit opens (blocks new CLI operations for 5 minutes)
   - After timeout: Circuit tests recovery (half-open state)
   - 2 successful operations: Circuit closes (back to normal)

---

## Error Types

### Transient Errors (Automatically Retryable)
**Examples:**
- API rate limits (429)
- Network timeouts
- Connection errors (ECONNRESET)
- Service unavailable (503)
- Gateway errors (502, 504)

**Characteristics:**
- Temporary issues that usually resolve on their own
- High success rate on retry
- System recommends immediate retry

### Recoverable Errors (Retry with Caution)
**Examples:**
- Process timeouts
- Process killed/terminated
- Resource exhausted

**Characteristics:**
- May succeed on retry with adjustments
- Could indicate capacity issues
- System recommends retry after investigation

### Permanent Errors (Do Not Retry)
**Examples:**
- Syntax errors in generated code
- Invalid configuration
- Missing required files
- Authentication failures (invalid API keys)
- Compilation errors
- **CLI tool internal errors** (bugs in Augment/CLI itself):
  - `"e.split is not a function"` - JavaScript bugs
  - `"TypeError:"` - Type errors in CLI code
  - `"Cannot read property of undefined"` - Null reference errors
  - `"Agent execution failed"` - Tool execution bugs
  - `"Uncaught exception"` - Unhandled errors in CLI

**Characteristics:**
- Will fail again without code/config changes
- Requires user intervention to fix root cause
- For CLI bugs: Need to report to CLI provider or wait for fix
- System blocks automatic retry

---

## Manual Retry Tool

### Tool Name
`retry_failed_generation`

### Usage

**Basic Syntax:**
```python
await retry_failed_generation(task_id="<failed-task-id>")
```

**Example Conversation:**
```
User: "The build failed with a timeout error"

Agent: "I see the build failed. Let me check the task details..."
       [Checks task metadata]
       "This was a timeout error (recoverable type). Would you like me to retry?"

User: "Yes, please retry"

Agent: [Calls retry_failed_generation(task_id="abc-123")]
       "✅ Successfully retried failed application build (original task: abc-123).

       ✅ Application build started on branch `feature-branch` using python.

       The build is running in the background (Task ID: xyz-789).
       You can monitor progress in the Tasks panel.

       Original error was: Process timeout - may need longer timeout or retry"
```

### When the Tool Succeeds

```
✅ Successfully retried failed application build (original task: abc-123).

✅ Application build started on branch `feature-branch` using python.

The build is running in the background (Task ID: xyz-789).

Original error was: API rate limit exceeded
```

### When Retry is Blocked (Permanent Error)

```
❌ Cannot retry task abc-123:

Error type: permanent
Description: Code syntax error

This error is classified as PERMANENT and is unlikely to succeed on retry.
Please review the error details and fix the underlying issue before creating a new task.
```

### When Circuit Breaker is Open

```
⚠️ Cannot retry task abc-123 at this time:

Circuit open - too many failures. Retry in 180s

The circuit breaker is currently OPEN due to too many recent failures.
This is a protective mechanism to prevent cascading failures.
Please wait for the circuit breaker to reset before retrying.
```

### When Task Cannot Be Found

```
ERROR: Task abc-123 not found
```

### When Task is Not Failed

```
ERROR: Task abc-123 is not in failed state (current status: completed).
Only failed tasks can be retried.
```

---

## Recommended Workflow

### For Transient Errors:
1. Check task status in Tasks panel
2. See error marked as `transient` with `is_retryable: true`
3. Immediately call `retry_failed_generation(task_id)`
4. Monitor new task for success

### For Recoverable Errors:
1. Check task status and error details
2. Investigate cause (timeout settings, resource availability)
3. If confident, call `retry_failed_generation(task_id)`
4. Consider adjusting timeout/resources if it fails again

### For Permanent Errors:
1. Review error message in task details
2. Fix underlying issue:
   - Update requirements/specs
   - Fix invalid configuration
   - Correct API keys
   - Fix code syntax in repository
3. Create NEW task with fixed parameters
4. Do NOT use `retry_failed_generation` (it will be blocked)

---

## Circuit Breaker States

### CLOSED (Normal Operation)
- All CLI operations allowed
- System tracks failures
- Resets failure count after 1 hour of no failures

### OPEN (Blocking)
- All CLI operations blocked
- Lasts for 5 minutes after threshold reached
- Error message tells user to wait
- Prevents cascading failures

### HALF_OPEN (Testing Recovery)
- After 5-minute timeout
- Allows one operation to test if system recovered
- Success → Circuit closes (back to normal)
- Failure → Circuit reopens for another 5 minutes

---

## Task Metadata Fields

When a task fails, check these metadata fields:

```json
{
  "error_type": "transient",
  "error_description": "API rate limit exceeded",
  "exit_code": 1,
  "is_retryable": true,
  "timeout_occurred": false,
  "changed_files": [...],
  "diff": {...}
}
```

**Key Fields:**
- `error_type`: `transient`, `recoverable`, or `permanent`
- `is_retryable`: Quick check if retry recommended
- `error_description`: Human-readable explanation
- `timeout_occurred`: Helps diagnose timeout issues

---

## Configuration

### Circuit Breaker Settings
Default values (can be customized in code):
```python
CircuitBreakerConfig(
    failure_threshold=3,        # Failures before opening circuit (max 3 attempts)
    success_threshold=2,        # Successes needed to close circuit
    timeout_seconds=300,        # Wait before testing recovery (5 min)
    reset_timeout_seconds=3600  # Reset failure count after 1 hour
)
```

### Retry Settings
Default values (for future automatic retry):
```python
RetryConfig(
    max_retries=3,            # Maximum retry attempts
    base_delay=5.0,           # Initial delay in seconds
    max_delay=60.0,           # Maximum delay between retries
    backoff_multiplier=2.0    # Exponential backoff multiplier
)
```

---

## Troubleshooting

### "Circuit breaker is OPEN"
**Solution:** Wait 5 minutes for automatic recovery, or investigate root cause of failures

### "Error is not retryable"
**Solution:** Review error details, fix underlying issue, create new task instead of retrying

### "Missing required parameters"
**Solution:** Task metadata incomplete. Create new task with proper parameters

### "Retry failed with same error"
**Solution:** Root cause not resolved. For permanent errors, fix code/config before retrying

### Example: Augment CLI Internal Error

**Scenario:**
```
Exit code: 1
Log: "Agent execution failed: e.split is not a function"
```

**What Happens:**
1. Error classified as **PERMANENT** (CLI tool internal error)
2. Task metadata: `is_retryable: false`
3. User tries to retry:
   ```
   ❌ Cannot retry task abc-123:

   Error type: permanent
   Description: CLI tool internal error (JavaScript bug)

   This error is classified as PERMANENT and is unlikely to succeed on retry.
   This is a bug in the Augment CLI tool itself.

   Recommended actions:
   - Try a different/simpler prompt that avoids triggering the bug
   - Report the issue to Augment support
   - Wait for Augment to fix the bug
   - Use alternative code generation approach
   ```

**Why It's Blocked:**
- This is a JavaScript error INSIDE Augment's code (`e.split is not a function`)
- Retrying with same prompt will trigger same code path and fail again
- Not a transient issue - it's a reproducible bug
- Requires Augment to fix their tool, or user to modify request to avoid the bug

---

## Best Practices

1. **Check Error Type First** - Always review `error_type` and `is_retryable` before retrying
2. **Respect Circuit Breaker** - If circuit is open, wait or fix root cause instead of forcing retry
3. **Fix Permanent Errors** - Never retry syntax/config errors without fixing the issue
4. **Monitor New Tasks** - After retry, watch new task to ensure success
5. **Learn from Patterns** - If same error happens repeatedly, investigate root cause

---

## Future Enhancements

Planned features (not yet implemented):
- **Automatic Retry**: System automatically retries transient errors with exponential backoff
- **Retry History**: Track all retry attempts and success rates
- **Smart Delay Calculation**: Adjust retry delay based on error type
- **Batch Retry**: Retry multiple failed tasks at once
- **Retry Notifications**: Alert users when automatic retry succeeds/fails
