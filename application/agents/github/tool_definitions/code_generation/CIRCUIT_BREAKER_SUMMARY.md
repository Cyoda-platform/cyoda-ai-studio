# Circuit Breaker Summary

## Quick Facts

**Max Retry Attempts:** 3
**Circuit Opens After:** 3 consecutive failures
**Cooldown Period:** 5 minutes
**Reset After:** 1 hour of no failures

---

## How It Works

### Normal Operation (Circuit CLOSED)
```
Attempt 1: Fail → Retry allowed (1/3 failures)
Attempt 2: Fail → Retry allowed (2/3 failures)
Attempt 3: Fail → Retry allowed (3/3 failures)
Attempt 4: BLOCKED → Circuit OPEN
```

### Circuit Opens
```
After 3 consecutive failures:
  - Circuit state: OPEN
  - New requests: BLOCKED for 5 minutes
  - User message: "Circuit open - too many failures. Retry in Xs"
```

### Recovery Testing (Circuit HALF_OPEN)
```
After 5 minute cooldown:
  - Circuit state: HALF_OPEN
  - Allow 1 test request
  - If successful: Circuit CLOSES (back to normal)
  - If fails: Circuit OPENS again for 5 more minutes
```

### Full Recovery (Circuit CLOSED)
```
After 2 consecutive successes in HALF_OPEN:
  - Circuit state: CLOSED
  - Failure count: Reset to 0
  - Normal operation resumes
```

---

## Configuration

```python
CircuitBreakerConfig(
    failure_threshold=3,        # Max 3 attempts before opening
    success_threshold=2,        # Need 2 successes to close
    timeout_seconds=300,        # 5 minute cooldown
    reset_timeout_seconds=3600  # Reset counter after 1 hour
)
```

---

## Example Scenarios

### Scenario 1: Transient Error That Fixes Itself
```
09:00 - Attempt 1: Network error → Fail (1/3)
09:01 - Attempt 2: Network error → Fail (2/3)
09:02 - Attempt 3: Network error → Fail (3/3)
09:03 - Circuit OPENS
09:08 - Circuit → HALF_OPEN (after 5 min)
09:08 - Test attempt: Success! → Circuit CLOSES
09:09 - Normal operation resumed
```

### Scenario 2: Permanent Error
```
09:00 - Attempt 1: Generated code has syntax error → Fail (1/3)
09:01 - Attempt 2: Same error → Fail (2/3)
09:02 - Attempt 3: Same error → Fail (3/3)
09:03 - Circuit OPENS
09:08 - Circuit → HALF_OPEN
09:08 - Test attempt: Still fails → Circuit OPENS again
09:13 - Circuit → HALF_OPEN
09:13 - User fixes prompt → Success! → Circuit CLOSES
```

### Scenario 3: Intermittent Failures
```
09:00 - Attempt 1: CLI bug → Fail (1/3)
09:01 - Attempt 2: CLI bug → Fail (2/3)
09:02 - Attempt 3: Success! → Failure count reset to 0
09:03 - Normal operation (circuit stayed CLOSED)
```

---

## User Messages

### Circuit CLOSED (Normal)
```
✅ Request allowed
No special message
```

### Circuit OPEN (Blocking)
```
⚠️ Cannot retry at this time:

Circuit open - too many failures. Retry in 180s

The circuit breaker is currently OPEN due to too many recent failures.
This is a protective mechanism to prevent cascading failures.
Please wait for the circuit breaker to reset before retrying.
```

### Circuit HALF_OPEN (Testing)
```
✅ Request allowed (testing recovery)
"Circuit half-open - testing recovery"
```

---

## Benefits of 3 Attempts (vs 5)

### ✅ Faster Failure Detection
```
Old: 5 failures × 2 min each = 10 minutes wasted
New: 3 failures × 2 min each = 6 minutes wasted
Savings: 4 minutes faster feedback
```

### ✅ Lower Resource Usage
```
Old: Up to 5 concurrent failed processes
New: Up to 3 concurrent failed processes
Reduction: 40% fewer wasted resources
```

### ✅ Better User Experience
```
Old: User waits through 5 failures before clear message
New: User gets clear message after 3 failures
Result: Faster guidance to fix the issue
```

### ✅ Still Allows Valid Retries
```
Transient errors (network, race conditions):
  - Often resolve within 1-2 retries
  - 3 attempts is sufficient
  - Circuit breaker prevents excessive retry spam

Permanent errors (bad code, bad config):
  - Won't succeed even after 10 retries
  - 3 attempts is enough to confirm
  - Faster feedback to user
```

---

## Summary

**Configuration:** Max 3 attempts, 5 min cooldown
**Protection:** Prevents excessive retries
**Recovery:** Auto-tests after cooldown
**User Impact:** Faster feedback, clear messages

Simple and effective! 🎯
