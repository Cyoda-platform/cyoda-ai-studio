# Conversation-Level Locking for Code Generation

## Overview

Code generation tools (`generate_application` and `generate_code_with_cli`) now enforce **conversation-level locking** to prevent parallel execution within the same conversation.

## Problem

When multiple code generation tasks run in parallel within the same conversation, they can:
- Create Git conflicts (both modifying the same branch)
- Interfere with each other's file operations
- Produce unpredictable results
- Waste resources on conflicting changes

## Solution

**One code generation task at a time per conversation.**

- ✅ Conversation 1: Build running → New build/codegen **BLOCKED**
- ✅ Conversation 2: Codegen running → New build/codegen **BLOCKED**
- ✅ Different conversations can run in parallel (Conversation 1 + Conversation 2 = OK)

## How It Works

### 1. Lock Check

Before starting any code generation:

```python
# Check if any code generation task is running in this conversation
is_locked, message = await check_conversation_lock(conversation_id, entity_service)

if is_locked:
    return error_message  # Blocked!
```

### 2. Locked Task Types

These task types are subject to conversation locking:
- `application_build` (from `generate_application`)
- `code_generation` (from `generate_code_with_cli`)

### 3. Query Logic

```python
# Search for running tasks in this conversation
builder = SearchConditionRequest.builder()
builder.add_condition("conversation_id", CyodaOperator.EQUALS, conversation_id)
builder.add_condition("status", CyodaOperator.EQUALS, "running")

responses = await entity_service.search(
    entity_class="BackgroundTask",
    condition=builder.build(),
    entity_version="1",
)

# Check if any running task is a code generation task
for task in responses:
    if task.task_type in ["application_build", "code_generation"]:
        return LOCKED  # Block execution
```

### 4. Integration Point

The lock check runs in `_validate_preconditions()` in `_code_generation_core.py`:

```python
async def _validate_preconditions(config, context):
    # STEP 1: Check conversation lock
    is_locked, lock_message = await check_conversation_lock(
        context.conversation_id, entity_service
    )
    if is_locked:
        return False, lock_message  # Fail fast

    # STEP 2: Other validations (branch protection, etc.)
    ...
```

This ensures we **fail fast** before:
- Validating branch protection
- Checking CLI limits
- Writing prompt files
- Starting processes

## User Experience

### Scenario 1: Build Running

```
User: "Generate a Python application for claims processing"

Agent: ✅ Application build started (Task ID: abc-123)

User: "Also add a Customer entity"

Agent: ❌ Application build already running for this conversation

Task: Build python application: feature-claims
Task ID: abc-123

Only one code generation task can run at a time per conversation.
Please wait for the current task to complete before starting a new one.

You can check task status using:
  check_task_status(task_id='abc-123')
```

### Scenario 2: Code Generation Running

```
User: "Add validation to Customer entity"

Agent: ✅ Code generation started (Task ID: def-456)

User: "Start a new build"

Agent: ❌ Code generation already running for this conversation

Task: Generate code: Add Customer entity validation
Task ID: def-456

Only one code generation task can run at a time per conversation.
Please wait for the current task to complete.
```

### Scenario 3: Different Conversations (Allowed)

```
Conversation 1:
  User: "Build Python app"
  Agent: ✅ Build started (Task ID: conv1-abc)

Conversation 2:
  User: "Build Java app"
  Agent: ✅ Build started (Task ID: conv2-xyz)  # Different conversation - OK!
```

## Error Message Format

When locked, users see:

```
❌ [Task Type] already running for this conversation

Task: [Task Name]
Task ID: [Task ID]

Only one code generation task can run at a time per conversation.
Please wait for the current task to complete before starting a new one.

You can check task status using:
  check_task_status(task_id='[TASK_ID]')
```

## Edge Cases

### No Conversation ID

If `conversation_id` is not available (legacy mode):
- Lock check is **skipped** (fail open)
- Warning logged
- Execution proceeds

```python
if not conversation_id:
    logger.warning("No conversation_id - skipping lock check")
    return False, "No conversation lock (no conversation ID)"
```

### Lock Check Failure

If the lock check itself fails (database error, network issue):
- Execution is **allowed** (fail open)
- Error logged
- User not blocked

```python
except Exception as e:
    logger.error(f"Failed to check conversation lock: {e}")
    return False, f"Lock check failed (allowing execution): {str(e)}"
```

### Task Completed But Status Not Updated

If a task completes but status remains "running":
- User will be blocked until status updates
- Task monitoring will eventually update status
- Worst case: User can wait and retry

## Benefits

### ✅ Prevents Conflicts
No more Git merge conflicts from parallel operations

### ✅ Clear User Feedback
Users know exactly what's running and how to check status

### ✅ Resource Efficiency
Avoid wasted CLI invocations on conflicting work

### ✅ Fail Fast
Block early before spending resources

### ✅ Cross-Conversation Parallelism
Different conversations can still run in parallel

## Implementation Files

- `_conversation_lock.py` - Lock checking logic
- `_code_generation_core.py` - Integration point in `_validate_preconditions()`
- `check_task_status_tool.py` - Tool for users to check task status

## Testing

### Test Lock Enforcement

```python
# Start first task
result1 = await generate_application(
    requirements="Build app",
    language="python",
    tool_context=context1  # conversation_id = "conv-1"
)
# Should succeed

# Try second task in same conversation
result2 = await generate_code_with_cli(
    user_request="Add entity",
    tool_context=context1  # Same conversation_id = "conv-1"
)
# Should be BLOCKED

# Try task in different conversation
result3 = await generate_application(
    requirements="Build app",
    tool_context=context2  # Different conversation_id = "conv-2"
)
# Should succeed
```

## Summary

**Simple Rule:** One code generation task at a time per conversation.

- Check happens early (fail fast)
- Clear error messages with guidance
- Cross-conversation parallelism preserved
- Fails open on errors (allows execution)

This prevents conflicts and provides a better user experience! 🎯
