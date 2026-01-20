# Example: Augment CLI Error Recovery

## The Error

**Your Specific Case:**
```
Exit code: 1
Last log output:
  Create realistic example JSON files for each entity in application/resources/entity/
  [x] UUID:eqiF5tNoraH6nx4f3oZgAb
  NAME:Implement Core Entities
  DESCRIPTION:Create Python entity classes for Claim, ClaimDocument, FraudAlert, Policy, Queue, and User

  🤖 Now let me create the example JSON files. I'll update the existing Claim.json and create the others:
  🔧 Tool call: str-replace-editor
  ❌ Agent execution failed: e.split is not a function
```

---

## What Happens Now (With Error Recovery)

### Step 1: Error Classification

```python
# Error analysis
returncode = 1
log_content = "Agent execution failed: e.split is not a function"

# Pattern matching (updated classification)
log_lower = log_content.lower()

# Check transient patterns: NO MATCH
# Check recoverable patterns: NO MATCH
# Check permanent patterns:
#   - "agent execution failed" → MATCH ✅
#   - "is not a function" → MATCH ✅

# Result
error_type = CliErrorType.PERMANENT
error_description = "CLI tool internal error (JavaScript bug)"
```

### Step 2: Task Metadata Update

```json
{
  "task_id": "abc-123",
  "status": "failed",
  "error_type": "permanent",
  "error_description": "CLI tool internal error (JavaScript bug)",
  "exit_code": 1,
  "is_retryable": false,  ← Blocks retry
  "timeout_occurred": false,
  "error": "Process failed with exit code 1\n\nError type: permanent\nDescription: CLI tool internal error (JavaScript bug)\nPermanent: This error is unlikely to succeed on retry\n\nLast log output:\nAgent execution failed: e.split is not a function"
}
```

### Step 3: Circuit Breaker Tracking

```
Circuit Breaker Status:
  Failure recorded: YES
  Failure count: 1/3
  Circuit state: CLOSED (still allowing operations)

Note: Circuit won't open from CLI tool bugs alone
      (only opens when multiple operations fail, indicating systemic issues)
```

### Step 4: User Attempts Retry

**User:** "Retry the build"

**Agent Response:**
```
❌ Cannot retry task abc-123:

Error type: permanent
Description: CLI tool internal error (JavaScript bug)

This error is classified as PERMANENT and is unlikely to succeed on retry.

This is a bug in the CLI tool itself (not your code).

Recommended actions:
  1. Try a different/simpler prompt that may avoid triggering the bug
  2. Report the issue to the CLI provider support
  3. Wait for the CLI provider to fix the bug
  4. Use an alternative code generation approach
```

---

## Root Cause Analysis

### What Actually Failed

The error `"e.split is not a function"` indicates:

1. **Location:** Inside Augment CLI's `str-replace-editor` tool
2. **Cause:** JavaScript/TypeScript bug where:
   - Variable `e` was expected to be a string
   - But `e` is actually `undefined`, `null`, or a non-string type
   - Calling `.split()` on non-string throws this error

3. **Trigger:**
   - Augment was trying to create example JSON files
   - Used `str-replace-editor` tool to edit files
   - Tool received unexpected input format
   - Error handling missing, causing crash

### Why It's Not Retryable

```
Same Request → Same Code Path → Same Bug → Same Crash

Retrying with identical prompt will:
  1. Execute same Augment agent logic
  2. Reach same str-replace-editor call
  3. Pass same malformed input
  4. Trigger same JavaScript error
  5. Fail with exit code 1

Success Rate: 0%
```

---

## Workarounds

### Option 1: Simplify the Request

**Original (Failed):**
```
"Create Python entity classes for Claim, ClaimDocument, FraudAlert,
Policy, Queue, and User following the example_application pattern"
```

**Simplified (May Work):**
```
"Create Python entity class for Claim with basic fields: id, claim_number, status"
```

**Why This Might Work:**
- Fewer entities → Less complex execution path
- Single entity → Avoids batch processing bug
- Basic structure → Less likely to trigger edge cases

### Option 2: Break Into Smaller Tasks

Instead of one big task, create 6 separate tasks:
```
Task 1: "Create Claim entity class"
Task 2: "Create ClaimDocument entity class"
Task 3: "Create FraudAlert entity class"
... etc
```

**Benefits:**
- If one fails, others may succeed
- Easier to identify which specific entity triggers the bug
- Smaller scope reduces complexity

### Option 3: Manual Creation + Validation

```
1. Manually create entity skeleton files
2. Use generate_code_with_cli for specific parts:
   - "Add validation logic to Claim entity"
   - "Add serialization methods to ClaimDocument"
3. Augment fills in details instead of creating from scratch
```

### Option 4: Wait for Augment Fix

```
1. Report bug to Augment with full error details
2. Monitor Augment release notes
3. Retry when new version is released
```

---

## How to Report the Bug

### To Augment Support

**Subject:** `str-replace-editor tool crash: e.split is not a function`

**Body:**
```
Environment:
- CLI Provider: Augment
- Model: haiku4.5
- Tool: str-replace-editor

Error:
Agent execution failed: e.split is not a function

Context:
Creating multiple Python entity classes simultaneously.
Augment was attempting to create example JSON files when it crashed.

Reproduction:
Request: "Create Python entity classes for Claim, ClaimDocument,
         FraudAlert, Policy, Queue, and User"
Fails at: Creating example JSON files step

Expected:
Tool should handle edge cases gracefully or provide better error messages.

Full Log:
[Attach output log file from /tmp/build-*.log or /tmp/codegen-*.log]
```

---

## Prevention for Future

### Better Prompt Engineering

**Instead of:**
```
"Create entities for X, Y, Z with all examples"
```

**Use:**
```
"Create entity X with basic structure.
After reviewing, I'll ask for examples separately."
```

**Benefits:**
- Smaller, focused requests
- Less likely to hit tool bugs
- Easier to debug when failures occur

### Incremental Development

```
Phase 1: Create entity schemas only
Phase 2: Add validation logic
Phase 3: Add example data
Phase 4: Add serialization

Each phase is a separate CLI call
```

---

## Summary

**For Your Specific Error:**

| Aspect | Status |
|--------|--------|
| **Error Type** | PERMANENT (CLI tool bug) |
| **Is Retryable** | ❌ NO |
| **Root Cause** | JavaScript bug in Augment's str-replace-editor |
| **Will Same Prompt Work?** | ❌ NO (will fail identically) |
| **Circuit Breaker Blocked?** | ✅ NO (single failure, not systemic) |
| **Recommended Action** | Try simplified prompt or report to Augment |

**Next Steps:**
1. ❌ Don't retry with same prompt
2. ✅ Try simplified version (one entity at a time)
3. ✅ Report bug to Augment
4. ✅ Use workarounds above
5. ⏳ Wait for Augment fix if critical

**The system now correctly identifies this as a permanent error and blocks wasteful retry attempts!** 🎉
