# What Happens When Augment Fails with JS Error

## Real Example: Your Augment Error

**Error Output:**
```
Exit code: 1

Log output:
Create realistic example JSON files for each entity in application/resources/entity/
[x] UUID:eqiF5tNoraH6nx4f3oZgAb
NAME:Implement Core Entities

🤖 Now let me create the example JSON files...
🔧 Tool call: str-replace-editor
❌ Agent execution failed: e.split is not a function
```

---

## Step-by-Step Flow with Smart Analysis

### Step 1: Process Exits
```python
Process terminates with exit code 1
Monitor detects failure
Calls: _handle_process_failure(config, returncode=1, timeout_occurred=False)
```

### Step 2: Read Log File
```python
# Read last 2000 chars for analysis
log_content = """
...
Agent execution failed: e.split is not a function
"""
```

### Step 3: Call Smart Classifier
```python
from _cli_error_analyzer import classify_cli_error

error_type, description = classify_cli_error(
    returncode=1,
    log_content=log_content,
    timeout_occurred=False
)
```

### Step 4: Exit Code Analysis
```python
# In classify_cli_error()

retryable_by_code = _is_retryable_by_exit_code(returncode=1)
# Result: None (inconclusive - need to analyze logs)
```

### Step 5: Detect Error Source
```python
# In _detect_error_source()

log_lower = "agent execution failed: e.split is not a function"

# Check network indicators
network_indicators = ["connect", "timeout", "429", ...]
# Result: NO MATCH

# Check configuration indicators
config_indicators = ["api key", "auth", "401", ...]
# Result: NO MATCH

# Check CLI tool indicators
cli_tool_indicators = [
    "agent execution failed",  ✅ MATCH!
    "tool execution failed",
    "internal error",
    ...
]
# Result: MATCH FOUND

# Check CLI path indicators (in stack traces)
cli_path_indicators = ["/node_modules/", "augment", "cli.js", ...]
# Result: Could match if stack trace present

# Conclusion
error_source = ErrorSource.CLI_TOOL
```

### Step 6: Check for Stack Trace
```python
# In _contains_stack_trace()

stack_trace_patterns = [
    r"at\s+\S+\s+\([^)]+:\d+:\d+\)",  # JavaScript
    r"File\s+\"[^\"]+\",\s+line\s+\d+",  # Python
    r"Traceback\s+\(most recent call last\)",
    r"Stack trace:",
]

log_content = "Agent execution failed: e.split is not a function"

# Check each pattern
for pattern in stack_trace_patterns:
    if re.search(pattern, log_content, re.IGNORECASE):
        return True

# Result: False (no stack trace in this case)
```

### Step 7: Classification Decision
```python
# In classify_cli_error()

if error_source == ErrorSource.CLI_TOOL:
    has_stack_trace = _contains_stack_trace(log_content)

    if has_stack_trace:
        return (
            CliErrorType.PERMANENT,
            "CLI tool crashed with unhandled exception"
        )
    else:
        return (
            CliErrorType.PERMANENT,
            "CLI tool internal error - bug in CLI tool itself"
        )

# For your case:
# error_source = CLI_TOOL
# has_stack_trace = False

# Result:
error_type = CliErrorType.PERMANENT
description = "CLI tool internal error - bug in CLI tool itself"
```

### Step 8: Update Task Metadata
```python
# In _handle_process_failure()

metadata = {
    "error_type": "permanent",  # From error_type.value
    "error_description": "CLI tool internal error - bug in CLI tool itself",
    "exit_code": 1,
    "is_retryable": False,  # error_type == PERMANENT
    "timeout_occurred": False,
}

await task_service.update_task_status(
    task_id=task_id,
    status="failed",
    message="Process failed: CLI tool internal error - bug in CLI tool itself",
    progress=0,
    error="""
        Exit code: 1
        Error type: permanent
        Description: CLI tool internal error - bug in CLI tool itself
        Permanent: This error is unlikely to succeed on retry

        Last log output:
        Agent execution failed: e.split is not a function
    """,
    metadata=metadata,
)
```

### Step 9: Record Circuit Breaker Failure
```python
# In _handle_process_failure()

circuit_breaker = get_circuit_breaker()
circuit_breaker.record_failure()

# Circuit breaker state:
# failure_count: 1/3
# state: CLOSED (still allowing operations)
```

### Step 10: User Sees Failed Task
```json
{
  "task_id": "abc-123",
  "status": "failed",
  "error_type": "permanent",
  "error_description": "CLI tool internal error - bug in CLI tool itself",
  "is_retryable": false,
  "exit_code": 1
}
```

### Step 11: User Tries to Retry
```python
User: "Retry the build"

Agent calls: retry_failed_generation(task_id="abc-123")

# In retry_failed_generation()
task = await task_service.get_task("abc-123")
is_retryable = task.metadata.get("is_retryable")  # False

if not is_retryable:
    error_description = task.metadata.get("error_description")
    # "CLI tool internal error - bug in CLI tool itself"

    # Check for "cli tool internal error" in description
    if "cli tool internal error" in error_description.lower():
        guidance = """
        This is a bug in the CLI tool itself (not your code).

        Recommended actions:
          1. Try a different/simpler prompt that may avoid triggering the bug
          2. Report the issue to the CLI provider support
          3. Wait for the CLI provider to fix the bug
          4. Use an alternative code generation approach
        """

    return f"""
    ❌ Cannot retry task abc-123:

    Error type: permanent
    Description: CLI tool internal error - bug in CLI tool itself

    This error is classified as PERMANENT and is unlikely to succeed on retry.

    {guidance}
    """
```

---

## Why It Detects As CLI Tool Error

### Detection Logic

**✅ Positive Indicators (CLI Tool Error):**
1. Message contains `"agent execution failed"` → CLI framework error
2. No mention of user's generated code files
3. No user code paths in error
4. Generic JavaScript error (`e.split is not a function`)
5. Exit code 1 with no network/config indicators

**❌ NOT Detected As:**
- Network error: No "timeout", "connection", "429", etc.
- Config error: No "api key", "auth", "401", etc.
- User code error: No file paths like `application/entity/Claim.py`

### Source Detection Breakdown

```python
log = "Agent execution failed: e.split is not a function"

# Analysis
1. Contains "agent execution failed"
   → Indicates CLI framework/tool error

2. JavaScript error pattern detected
   → "is not a function" suggests runtime error

3. No user code context
   → No paths like "application/", "entity/", "workflow/"

4. No stack trace with user files
   → Would show if error was in generated code

# Conclusion
error_source = ErrorSource.CLI_TOOL → PERMANENT
```

---

## Different Scenarios

### Scenario 1: With Stack Trace
```
Error:
Agent execution failed: e.split is not a function
    at Object.handler (/augment/tools/str-replace-editor.js:45:12)
    at processTicksAndRejections (node:internal/process/task_queues:95:5)

Classification:
  Source: CLI_TOOL (path shows /augment/tools/)
  Stack trace: YES
  Result: PERMANENT - "CLI tool crashed with unhandled exception"
  is_retryable: false
```

### Scenario 2: Different JS Error
```
Error:
Tool execution failed: TypeError: Cannot read property 'length' of undefined

Classification:
  Source: CLI_TOOL ("tool execution failed")
  Result: PERMANENT - "CLI tool internal error"
  is_retryable: false
```

### Scenario 3: User Code Error
```
Error:
Build failed: SyntaxError in application/entity/claim/claim.py, line 15
    invalid syntax

Classification:
  Source: GENERATED_CODE (mentions user file path)
  Result: PERMANENT - "Generated code has errors - prompt needs adjustment"
  is_retryable: false
```

### Scenario 4: Network Error
```
Error:
Request failed: ECONNRESET - Connection reset by peer

Classification:
  Source: NETWORK ("connection reset", "econnreset")
  Result: TRANSIENT - "Network or API error - likely transient"
  is_retryable: true
```

---

## Complete Flow Diagram

```
Augment Process Fails
        ↓
Exit Code: 1
        ↓
Read Logs: "Agent execution failed: e.split is not a function"
        ↓
Classify Error
        ↓
Exit Code Analysis
  returncode=1 → Inconclusive, check logs
        ↓
Detect Error Source
  Check network indicators → NO
  Check config indicators → NO
  Check CLI tool indicators → YES ("agent execution failed")
        ↓
  error_source = CLI_TOOL
        ↓
Check Stack Trace
  Has stack trace? → NO (for your case)
        ↓
Classification
  CLI_TOOL + no stack trace
  → PERMANENT
  → "CLI tool internal error - bug in CLI tool itself"
        ↓
Update Task
  error_type: "permanent"
  is_retryable: false
        ↓
Circuit Breaker
  Record failure (1/5)
  State: CLOSED
        ↓
User Notification
  Task marked as failed
  Retry blocked with helpful guidance
```

---

## Key Points

### ✅ Robust Detection
- **Not hardcoded** - detects pattern "agent execution failed"
- **Context aware** - knows it's CLI tool, not user code
- **Source-based** - classification based on WHERE error came from

### ✅ Correct Classification
- **PERMANENT** - CLI bugs won't fix on retry
- **is_retryable: false** - prevents wasted retry attempts
- **Helpful guidance** - tells user it's CLI bug, not their fault

### ✅ Self-Protecting
- **Circuit breaker** - prevents retry spam if user ignores warning
- **Clear messaging** - explains why retry blocked
- **Actionable advice** - suggests alternatives

### ✅ Works for All JS Errors
```javascript
"e.split is not a function"       → PERMANENT
"x.map is not a function"         → PERMANENT
"config.merge is not a function"  → PERMANENT
"data is not defined"             → PERMANENT
"Cannot read property 'x'"        → PERMANENT
```

**All detected by same logic - no hardcoding needed!** 🎉

---

## Summary

**When Augment fails with JS error:**

1. ✅ **Detected** - "agent execution failed" indicates CLI tool error
2. ✅ **Classified** - PERMANENT (CLI bug)
3. ✅ **Blocked** - is_retryable = false
4. ✅ **Guided** - User gets helpful error message
5. ✅ **Protected** - Circuit breaker prevents spam

**No hardcoding. Exit code + error source = robust detection.** 🚀
