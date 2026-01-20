# Task Status Checking Guide

## Overview

When you start a build or code generation, you receive a **Task ID**. You can now check the status of any task using this ID.

---

## Getting Task IDs

### When You Start a Build
```
User: "Generate a Python application for claims processing"

Agent:
✅ Application build started on branch `feature-claims` using python.

The build is running in the background (Task ID: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe).
You can monitor progress in the Tasks panel.
```

**Task ID:** `c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe`

### When You Start Code Generation
```
User: "Add a Customer entity with name and email fields"

Agent:
✅ Code generation started on branch `feature-customer`.

Processing your request: Add a Customer entity...

The generation is running in the background (Task ID: d8c5a23f-g0dc-22c3-cee6-3f78fd544gcf).
```

**Task ID:** `d8c5a23f-g0dc-22c3-cee6-3f78fd544gcf`

---

## Checking Task Status

### New Tool: `check_task_status`

**Simple Usage:**
```
User: "What's the status of task c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe?"

Agent calls: check_task_status(task_id="c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe")
```

### Example Outputs

#### Running Task
```
📋 Task Status: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe

Status: running 🔄
Progress: 45%
Name: Build python application: feature-claims

Started: 2024-01-19 15:08:23

Branch: feature-claims
Language: python
Repository: /tmp/repos/cyoda-claims-app

📝 Recent Updates:
  • Generated entity files (15:09:12)
  • Creating workflow definitions (15:10:45)
  • Building application structure (15:11:23)

⏳ Task is still running. Check back later for updates.
```

#### Completed Task
```
📋 Task Status: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe

Status: completed ✅
Progress: 100%
Name: Build python application: feature-claims

Started: 2024-01-19 15:08:23
Completed: 2024-01-19 15:15:47
Duration: 7 minutes 24 seconds

Branch: feature-claims
Language: python
Repository: /tmp/repos/cyoda-claims-app

📁 Files changed: 23

📝 Recent Updates:
  • All entity files created (15:13:12)
  • Workflow definitions complete (15:14:30)
  • Build successful (15:15:47)

✅ Task completed successfully!

Next steps:
  • Review changes in branch: feature-claims
  • Check repository: /tmp/repos/cyoda-claims-app
```

#### Failed Task (Retryable)
```
📋 Task Status: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe

Status: failed ❌
Progress: 0%
Name: Build python application: feature-claims

Started: 2024-01-19 15:08:23
Completed: 2024-01-19 15:09:12
Duration: 49 seconds

Branch: feature-claims
Language: python

❌ Error Details:
  Type: transient
  Description: CLI tool internal error - retry may work
  Retryable: Yes ✅

  Full error:
  Agent execution failed: e.split is not a function

❌ Task failed.

You can retry this task using:
  retry_failed_generation(task_id='c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe')
```

#### Failed Task (Not Retryable)
```
📋 Task Status: d8c5a23f-g0dc-22c3-cee6-3f78fd544gcf

Status: failed ❌
Progress: 0%
Name: Generate code: Add Customer entity

Started: 2024-01-19 15:20:10
Completed: 2024-01-19 15:21:05
Duration: 55 seconds

Branch: feature-customer
Language: python

❌ Error Details:
  Type: permanent
  Description: Generated code has errors - prompt needs adjustment
  Retryable: No ❌

  Full error:
  SyntaxError in application/entity/customer/customer.py, line 15
  invalid syntax: unexpected indent

❌ Task failed.

This error is not retryable. Please review the error and fix the underlying issue.
```

---

## Common User Prompts

### Check Status
```
"What's the status of task c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe?"
"Check my build task c7b6b12e"
"Is the generation still running?"
"Did task c7b6b12e finish?"
```

### After Seeing Status

**If Running:**
```
User: "Let me know when it's done"
Agent: "I'll check back in a few minutes"
```

**If Completed:**
```
User: "Great! Show me the files that were created"
Agent: [Uses repository tools to show changes]
```

**If Failed (Retryable):**
```
User: "Retry the build"
Agent: [Calls retry_failed_generation()]
```

**If Failed (Not Retryable):**
```
User: "What should I do?"
Agent: "The error indicates [explanation]. Let me help you fix the requirements and try again."
```

---

## Integration with Other Tools

### Complete Workflow

**Step 1: Start Build**
```
User: "Build a Python app for claims"
Agent: generate_application(requirements="...")
Result: Task ID: abc-123
```

**Step 2: Check Status**
```
User: "Check the status"
Agent: check_task_status(task_id="abc-123")
Result: Status: running 🔄
```

**Step 3: Wait if Needed**
```
Agent: "Still running. I'll check again in 30 seconds"
[wait 30 seconds]
Agent: check_task_status(task_id="abc-123")
Result: Status: completed ✅
```

**Step 4: Review Results**
```
User: "Show me what was created"
Agent: get_repository_diff(branch="feature-claims")
Result: [Shows all changes]
```

**Step 5: Handle Failures**
```
If failed + retryable:
  Agent: "The build failed with a CLI error. Shall I retry?"
  User: "Yes"
  Agent: retry_failed_generation(task_id="abc-123")

If failed + not retryable:
  Agent: "The build failed due to [error]. Let's fix the requirements."
  User: "OK"
  Agent: [Helps user fix issue, then starts new build]
```

---

## Error Handling

### Task Not Found
```
ERROR: Task not found: invalid-task-id

Possible reasons:
- Task ID is incorrect
- Task was deleted
- Task belongs to a different user
```

### Invalid Task ID
```
ERROR: Invalid task ID format: abc
```

### Permission Denied
```
ERROR: Task not found: c7b6b12e-f9cb-11b2-bdd5-2e67ec433fbe

Possible reasons:
- Task ID is incorrect
- Task was deleted
- Task belongs to a different user
```

---

## Benefits

### ✅ No More "Black Box"
```
Before: "I started a build... now what?"
After: "I can check the status anytime!"
```

### ✅ Self-Service Status Checks
```
Before: Agent has to manually check logs/processes
After: Simple tool call with task ID
```

### ✅ Clear Next Steps
```
Running: "Check back later"
Completed: "Review changes in branch X"
Failed (retryable): "Call retry_failed_generation()"
Failed (permanent): "Fix the issue and try again"
```

### ✅ Full Error Context
```
Shows:
- Error type (transient/permanent)
- Error description
- Whether it's retryable
- Full error message
- Suggested next steps
```

---

## Summary

**Tool:** `check_task_status(task_id="...")`

**Input:** Task ID (UUID from build/generation response)

**Output:**
- Current status (running/completed/failed)
- Progress percentage
- Time information
- Error details (if failed)
- Next steps

**Use Cases:**
- Check if build is done
- See why task failed
- Decide whether to retry
- Get task metadata

Simple, clear, and user-friendly! 🎯
