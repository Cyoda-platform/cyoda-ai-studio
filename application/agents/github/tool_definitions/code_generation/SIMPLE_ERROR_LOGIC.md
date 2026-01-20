# Simple Error Classification Logic

## The Simple Rule

**If it's not OUR fault → RETRY with same prompt**

---

## Error Types

### 1. TRANSIENT (Retry Automatically)

**Network/API Errors:**
- Rate limits (429)
- Service unavailable (503)
- Connection timeouts
- Network errors (ECONNRESET)

**Why retry:** Temporary issues, will resolve on their own

**CLI Tool Errors:**
- `"Agent execution failed: e.split is not a function"`
- `"Tool call failed: TypeError"`
- Any internal CLI tool bug

**Why retry:**
- NOT our prompt's fault
- CLI might have race conditions
- Different execution path might work
- CLI might get updated/fixed

---

### 2. RECOVERABLE (Retry with Caution)

**Process Issues:**
- Timeouts (exit code 124, 137, 143)
- Process killed

**Why retry:** Might work with more time or resources

---

### 3. PERMANENT (Don't Retry)

**Our Mistakes:**
- Invalid syntax in requirements
- Conflicting instructions
- Invalid configuration

**Generated Code Errors:**
- Syntax errors in generated Python/Java
- Compilation failures
- Import errors

**Why NOT retry:** Same prompt will generate same bad code

**Configuration Errors:**
- Invalid API keys
- Authentication failures
- Permission denied

**Why NOT retry:** Need to fix config first

---

## Classification Logic

```python
def classify_cli_error(returncode, log_content, timeout_occurred):
    # 1. Timeout? → RECOVERABLE
    if timeout_occurred or returncode in [124, 137, 143]:
        return RECOVERABLE, "Process timeout"

    # 2. Detect error source
    error_source = detect_where_error_came_from(log_content)

    # 3. Classify by source
    if error_source == NETWORK:
        return TRANSIENT, "Network error"

    if error_source == CLI_TOOL:
        return TRANSIENT, "CLI tool error - retry may work"  # ← Changed!

    if error_source == GENERATED_CODE:
        return PERMANENT, "Generated code has errors"

    if error_source == CONFIGURATION:
        return PERMANENT, "Configuration error"

    # 4. Default for exit code 1
    return TRANSIENT, "Generic error - retry may work"
```

---

## Your Augment Example

**Error:**
```
Exit code: 1
Log: "Agent execution failed: e.split is not a function"
```

**Old Logic (Too Strict):**
```
Source: CLI_TOOL
Result: PERMANENT ❌
is_retryable: false
Blocks retry
```

**New Logic (Simple):**
```
Source: CLI_TOOL
Result: TRANSIENT ✅
is_retryable: true
Allows retry with same prompt
```

**Why This Makes Sense:**
1. The prompt was fine
2. CLI tool had a bug (maybe race condition)
3. Retry might hit different code path
4. If it fails 5 times, circuit breaker opens
5. User gets protected by circuit breaker, not classification

---

## Circuit Breaker Protection

Even with TRANSIENT classification, circuit breaker protects against infinite retries:

```
Attempt 1: CLI error → TRANSIENT → Retry allowed
Attempt 2: CLI error → TRANSIENT → Retry allowed
Attempt 3: CLI error → TRANSIENT → Retry allowed
Attempt 4: Circuit OPENS → Retry blocked for 5 minutes
```

**Message:**
```
⚠️ Cannot retry at this time:

Circuit open - too many failures. Retry in 180s

The circuit breaker is currently OPEN due to too many recent failures.
```

---

## Comparison

### Example 1: CLI Tool Bug
```
Error: "Agent execution failed: e.split is not a function"

Old: PERMANENT (too strict, blocks useful retries)
New: TRANSIENT (allows retry, circuit breaker protects)
```

### Example 2: Generated Code Error
```
Error: "SyntaxError in application/entity/claim.py line 15"

Old: PERMANENT ✅
New: PERMANENT ✅
(Both block retry - correct!)
```

### Example 3: Network Error
```
Error: "Connection timeout - ECONNRESET"

Old: TRANSIENT ✅
New: TRANSIENT ✅
(Both allow retry - correct!)
```

---

## Benefits of Simplified Logic

### ✅ Fewer False Negatives
```
Before: CLI bug → PERMANENT → No retry → User stuck
After: CLI bug → TRANSIENT → Retry works → Problem solved!
```

### ✅ Circuit Breaker Catches Persistent Issues
```
If same error happens 3 times:
  Circuit opens → Blocks further retries
  User gets clear message to try different approach
```

### ✅ Simple Mental Model
```
NOT our fault (network, CLI bugs) → RETRY
OUR fault (bad prompt, bad config) → DON'T RETRY
```

### ✅ Real-World Success Stories
```
Scenario: Augment has race condition
  Attempt 1: e.split is not a function → Retry
  Attempt 2: Works! ✅

Scenario: Bad prompt generates invalid code
  Attempt 1: SyntaxError → Don't retry
  User fixes prompt → Try again → Works! ✅
```

---

## Summary

**Simple Rule:** If it's not our fault → Retry

**Error Sources:**
- Network/API → TRANSIENT (retry)
- CLI tool bugs → TRANSIENT (retry) ← **Changed!**
- Generated code → PERMANENT (don't retry)
- Configuration → PERMANENT (don't retry)

**Protection:** Circuit breaker prevents infinite retries even for TRANSIENT errors

**Result:** More retries succeed, circuit breaker catches real issues

**Complexity:** Much simpler logic, easier to understand and maintain

🎯 **Your insight made this much better!** Thank you!
