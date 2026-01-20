# Conversation Lock - Usage Examples

## Example 1: Build Already Running

### User Interaction

```
User (Conversation ABC):
"Generate a Python application for claims processing with these entities: Claim, Customer, Policy"

Agent:
✅ Application build started on branch `feature-claims` using python.

The build is running in the background (Task ID: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe).
You can monitor progress in the Tasks panel.

---

User (same conversation, 30 seconds later):
"Also add a validation workflow for claims"

Agent:
❌ Application build already running for this conversation

Task: Build python application: feature-claims
Task ID: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe

Only one code generation task can run at a time per conversation.
Please wait for the current task to complete before starting a new one.

You can check task status using:
  check_task_status(task_id='c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe')

---

User:
"What's the status?"

Agent calls: check_task_status("c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe")

📋 Task Status: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe

Status: running 🔄
Progress: 75%
Name: Build python application: feature-claims

Started: 2024-01-19 15:08:23

Branch: feature-claims
Language: python

📝 Recent Updates:
  • Generated entity files (15:09:12)
  • Creating workflow definitions (15:10:45)
  • Building application structure (15:11:23)

⏳ Task is still running. Check back later for updates.

---

[5 minutes later]

User:
"Now add the validation workflow"

Agent calls: check_task_status("c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe")

📋 Task Status: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe

Status: completed ✅
Progress: 100%

Agent:
Great! The previous build has completed. Let me add the validation workflow now.

Agent calls: generate_code_with_cli(
    user_request="Add a validation workflow for claims",
    ...
)

✅ Code generation started on branch `feature-claims`.
Processing your request: Add a validation workflow...
```

## Example 2: Code Generation Running

```
User (Conversation XYZ):
"Add validation to the Customer entity - check email format and name length"

Agent:
✅ Code generation started on branch `feature-customer`.

Processing your request: Add validation to Customer entity...

The generation is running in the background (Task ID: d8c5a23f-g0dc-22c3-cee6-3f78fd544gcf).

---

User (immediately after):
"Actually, start a new build from scratch"

Agent:
❌ Code generation already running for this conversation

Task: Generate code: Add Customer entity validation
Task ID: d8c5a23f-g0dc-22c3-cee6-3f78fd544gcf

Only one code generation task can run at a time per conversation.
Please wait for the current task to complete before starting a new one.

You can check task status using:
  check_task_status(task_id='d8c5a23f-g0dc-22c3-cee6-3f78fd544gcf')
```

## Example 3: Different Conversations (Parallel Execution Allowed)

```
Conversation 1 (User A):
"Build a Python claims processing app"

Agent:
✅ Application build started (Task ID: conv1-task-abc)

---

Conversation 2 (User B, different conversation):
"Build a Java inventory management app"

Agent:
✅ Application build started (Task ID: conv2-task-xyz)

// Both builds run in parallel - different conversations!
```

## Example 4: Task Completed, New Task Allowed

```
User (Conversation DEF):
"Generate a Python app for order processing"

Agent:
✅ Application build started (Task ID: task-111)

---

[15 minutes later, build completes]

---

User:
"Add a shipping module"

Agent calls: check_conversation_lock()
// No running tasks found → Lock check passes

Agent:
✅ Code generation started (Task ID: task-222)

// New task allowed - previous task completed!
```

## Example 5: User Checks Status During Lock

```
User:
"Build a Python app"

Agent:
✅ Build started (Task ID: task-aaa)

---

User:
"Also generate a new entity"

Agent:
❌ Application build already running...

---

User:
"Check status of task-aaa"

Agent calls: check_task_status("task-aaa")

📋 Task Status: task-aaa

Status: running 🔄
Progress: 45%

⏳ Task is still running. Check back later for updates.

---

User:
"OK, I'll wait"

[waits 5 minutes]

User:
"Try again - generate new entity"

Agent calls: check_task_status("task-aaa")

Status: completed ✅

Agent:
The previous build is now complete! Let me generate the new entity.

✅ Code generation started (Task ID: task-bbb)
```

## Example 6: Failed Task Still Blocks

```
User:
"Build app"

Agent:
✅ Build started (Task ID: task-xxx)

---

[Build fails after 2 minutes]

Task status changes to: failed ❌

---

User:
"Generate new code"

Agent calls: check_conversation_lock()
// No running tasks (status = "failed", not "running")
// Lock check passes!

Agent:
✅ Code generation started (Task ID: task-yyy)

// Failed tasks don't block - only running tasks block!
```

## Example 7: No Conversation ID (Legacy Mode)

```
// Old code without conversation_id in context

User:
"Build app"

Agent calls: generate_application(...)
// conversation_id = None

check_conversation_lock(None, entity_service)
// Returns: (False, "No conversation lock (no conversation ID)")
// Lock check skipped!

Agent:
✅ Build started (Task ID: task-legacy)

// Legacy mode - no locking
```

## Example 8: Lock Check Fails (Fail Open)

```
User:
"Build app"

Agent calls: generate_application(...)

check_conversation_lock(conversation_id, entity_service)
// Database query fails with connection error

Exception: Connection timeout to Cyoda API

// Lock check fails → Fail open (allow execution)
// Returns: (False, "Lock check failed (allowing execution)")

Agent:
⚠️ Warning: Lock check failed but allowing execution
✅ Build started (Task ID: task-zzz)

// Execution allowed - don't block users on infrastructure issues
```

## Example 9: Multiple Conversations, Same User

```
User opens TWO conversations (tabs/sessions):

Conversation A:
"Build Python app"
✅ Build started (Task ID: conv-a-task)

Conversation B (same user, different conversation_id):
"Build Java app"
✅ Build started (Task ID: conv-b-task)

// BOTH ALLOWED - different conversation IDs!
// Lock is per-conversation, not per-user
```

## Example 10: Retry Blocked by Running Task

```
User (Conversation 123):
"Build app"

Agent:
✅ Build started (Task ID: task-original)

---

[Task fails after 3 minutes]

---

User:
"Retry the failed task"

Agent:
Let me retry task-original

Agent calls: retry_failed_generation("task-original")

// Inside retry_failed_generation:
// Calls generate_application() with same parameters
// generate_application() calls check_conversation_lock()
// Returns: No running tasks → OK to proceed

Agent:
✅ Retry started (Task ID: task-retry-1)

---

User (while retry is running):
"Start a fresh build"

Agent calls: generate_application(...)

check_conversation_lock()
// Finds task-retry-1 with status="running"

Agent:
❌ Application build already running for this conversation

Task: Build python application: feature-branch (retry)
Task ID: task-retry-1

// Blocked by retry task!
```

## Key Takeaways

1. **One task at a time per conversation** - Build or codegen, only one runs
2. **Different conversations can run in parallel** - No global bottleneck
3. **Clear error messages** - Users know what's running and how to check
4. **Task completion releases lock** - Completed/failed tasks don't block
5. **Safe defaults** - Fails open on errors, supports legacy mode
6. **Integrates with status checking** - Users can monitor progress
7. **Retry respects lock** - Retries also blocked if another task running

## Summary

The conversation lock prevents chaos and conflicts while preserving parallelism across conversations. Users get clear feedback and guidance when blocked. 🎯
