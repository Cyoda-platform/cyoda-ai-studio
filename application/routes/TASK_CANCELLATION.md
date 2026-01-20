# Task Cancellation Feature

## Overview

Users can now cancel running or pending background tasks directly from the UI. This feature allows users to stop long-running builds or code generation processes that are no longer needed.

## Backend Implementation

### Endpoint

**DELETE/POST** `/v1/tasks/<task_id>/cancel`

### Features

1. **Authentication & Authorization**
   - Requires valid JWT token
   - Users can only cancel their own tasks (unless superuser)

2. **Process Termination**
   - Sends SIGTERM to process for graceful shutdown
   - Waits 1 second for process to terminate
   - If still running, sends SIGKILL to force termination
   - Handles cases where process has already exited

3. **Status Update**
   - Updates task status to `cancelled`
   - Adds cancellation message to progress log
   - Sets error field to indicate user-initiated cancellation

4. **Safety Checks**
   - Only allows cancellation of `pending` or `running` tasks
   - Returns error for tasks with other statuses

### Code Location

- **File**: `/home/kseniia/IdeaProjects/cyoda-ai-studio/application/routes/tasks.py`
- **Function**: `cancel_task(task_id: str)`

### Request/Response

**Request:**
```bash
DELETE /v1/tasks/abc-123-def-456/cancel
Authorization: Bearer <token>
```

**Success Response:**
```json
{
  "success": true,
  "message": "Task cancelled successfully",
  "task": {
    "technical_id": "abc-123-def-456",
    "status": "cancelled",
    "progress": 45,
    "error": "Task was cancelled by user request",
    ...
  }
}
```

**Error Responses:**
```json
// Task not found
{
  "success": false,
  "message": "Task not found"
}

// Cannot cancel
{
  "success": false,
  "message": "Cannot cancel task with status 'completed'. Only pending or running tasks can be cancelled."
}

// Access denied
{
  "success": false,
  "message": "Access denied"
}
```

## Frontend Implementation

### Service Method

**File**: `/home/kseniia/IdeaProjects/ai-assistant-ui-react/packages/web/src/services/taskService.ts`

```typescript
async cancelTask(taskId: string): Promise<{ message: string; task: BackgroundTask }> {
  const response = await privateClient.delete(`/v1/tasks/${taskId}/cancel`);
  return response.data;
}
```

### UI Component

**File**: `/home/kseniia/IdeaProjects/ai-assistant-ui-react/packages/web/src/components/TaskDashboard/TaskCard.tsx`

#### Features

1. **Cancel Button**
   - Appears in task card header
   - Only visible for `running` or `pending` tasks
   - Red stop icon (StopCircle)
   - Shows spinner while cancelling

2. **Confirmation Dialog**
   - Asks user to confirm before cancelling
   - Prevents accidental cancellations

3. **State Management**
   - `isCancelling` state tracks cancellation in progress
   - Disables button during cancellation
   - Updates task list on success

4. **Error Handling**
   - Shows alert with error message on failure
   - Logs error to console for debugging

#### User Flow

1. User sees running/pending task in TasksPanel
2. Red stop button appears in task header
3. User clicks stop button
4. Confirmation dialog: "Are you sure you want to cancel this task?"
5. User confirms
6. Button shows spinner
7. API call to cancel task
8. On success: Task status updates to "cancelled"
9. On error: Alert shows error message

### Visual Design

**Running Task (before cancellation):**
```
┌─────────────────────────────────────┐
│ 🔄 Build python app        [🛑] [▼] │
│ Building application...             │
│ ████████░░░░░░░░░░ 45%              │
└─────────────────────────────────────┘
```

**Cancelling:**
```
┌─────────────────────────────────────┐
│ 🔄 Build python app        [⏳] [▼] │
│ Building application...             │
│ ████████░░░░░░░░░░ 45%              │
└─────────────────────────────────────┘
```

**Cancelled:**
```
┌─────────────────────────────────────┐
│ ❌ Build python app             [▼] │
│ Building application...             │
│ ████████░░░░░░░░░░ 45%              │
│ Error: Task was cancelled by user   │
└─────────────────────────────────────┘
```

## Process Termination Details

### Signal Handling

1. **SIGTERM (15)** - Graceful shutdown
   - Allows process to clean up resources
   - Close file handles
   - Save state if needed

2. **SIGKILL (9)** - Force termination
   - Immediate termination
   - Used if SIGTERM doesn't work after 1 second
   - Cannot be caught or ignored

### Implementation

```python
# Try graceful termination
os.kill(pid, signal.SIGTERM)
await asyncio.sleep(1)

# Check if still running
is_running = await _is_process_running(pid)
if is_running:
    # Force kill
    os.kill(pid, signal.SIGKILL)
```

### Edge Cases

1. **Process Already Exited**
   - `ProcessLookupError` caught
   - Continues with status update
   - No error shown to user

2. **Process Kill Fails**
   - Error logged
   - Status still updated to "cancelled"
   - User informed of cancellation

3. **No PID Stored**
   - Only updates task status
   - No process termination attempted

## Status Updates

### Task Fields Updated

- `status`: Changed to `"cancelled"`
- `error`: Set to `"Task was cancelled by user request"`
- `progress`: Kept at current value (doesn't reset to 0)
- `progress_messages`: New message added: `"Task cancelled by user"`

### Example Task State Change

**Before:**
```json
{
  "status": "running",
  "progress": 45,
  "process_pid": 12345,
  "error": null
}
```

**After:**
```json
{
  "status": "cancelled",
  "progress": 45,
  "process_pid": 12345,
  "error": "Task was cancelled by user request",
  "progress_messages": [
    ...,
    {
      "message": "Task cancelled by user",
      "timestamp": "2024-01-19T15:30:00Z",
      "progress": 45
    }
  ]
}
```

## Testing

### Manual Testing

1. **Start a build task**
   ```
   User: "Build a Python application"
   → Task starts running
   ```

2. **Open Tasks Panel**
   - Click Tasks icon in UI
   - See running task with stop button

3. **Cancel task**
   - Click red stop button
   - Confirm cancellation
   - Verify:
     - Button shows spinner
     - Task status updates to "cancelled"
     - Error message shows cancellation

4. **Try to cancel completed task**
   - No stop button should appear
   - Task cannot be cancelled

### API Testing

```bash
# Get running task ID
curl -X GET "http://localhost:8000/v1/tasks?conversation_id=conv-123" \
  -H "Authorization: Bearer <token>"

# Cancel task
curl -X DELETE "http://localhost:8000/v1/tasks/task-abc-123/cancel" \
  -H "Authorization: Bearer <token>"

# Verify cancellation
curl -X GET "http://localhost:8000/v1/tasks/task-abc-123" \
  -H "Authorization: Bearer <token>"
```

## Rate Limiting

- **Limit**: 20 requests per minute per user
- **Reason**: Prevent abuse of process termination
- **Higher than default**: Allows quick consecutive cancellations if needed

## Security Considerations

1. **Authentication Required**
   - All cancellation requests must include valid JWT

2. **Ownership Validation**
   - Users can only cancel their own tasks
   - Superusers can cancel any task

3. **Status Validation**
   - Only pending/running tasks can be cancelled
   - Prevents manipulation of completed tasks

4. **Rate Limiting**
   - Prevents cancellation spam
   - Protects server resources

## Future Enhancements

1. **Batch Cancellation**
   - Cancel multiple tasks at once
   - "Cancel all running tasks" button

2. **Cancellation Reason**
   - Allow user to specify why they cancelled
   - Store in task metadata

3. **Undo Cancellation**
   - Restart cancelled task with same parameters
   - Only for recently cancelled tasks

4. **Notification**
   - Show toast notification on successful cancellation
   - Replace alert() with better UI feedback

5. **Cascade Cancellation**
   - Cancel dependent tasks automatically
   - Prevent orphaned tasks

## Summary

The task cancellation feature provides users with full control over their background tasks:

✅ **User-friendly** - Simple button, clear confirmation
✅ **Safe** - Only allows cancellation of appropriate tasks
✅ **Robust** - Handles edge cases gracefully
✅ **Secure** - Authentication and authorization enforced
✅ **Responsive** - Real-time UI updates
✅ **Well-documented** - Clear API and usage examples

Users can now stop unwanted tasks instantly, improving the overall user experience! 🎯
