# UI Hooks Guide for Agents

## 🎯 Core Principle: Hooks Are Buttons, Not Questions

**The fundamental rule: Do NOT ask the user if they want to open a tab or perform an action.**

Instead, return a hook. The UI will render it as a clickable button that the user can choose to click.

---

## ❌ WRONG Pattern (Don't do this)

```
Agent: "I've created the Customer entity. Would you like me to open the Entities tab so you can view it? (I can open it for you)"
```

**Problems:**
- Asks permission for something the UI can handle
- Creates unnecessary back-and-forth
- Confuses the user about what the agent can do
- Wastes a conversation turn

---

## ✅ CORRECT Pattern (Do this)

```
Agent: "✅ Customer entity created and saved!

📊 The entity is now on your canvas with fields: id, name, email, created_at

[Open Entities Tab] ← Button rendered by UI from the hook
```

**Benefits:**
- Direct, clear communication
- User controls whether to click
- No unnecessary conversation turns
- Clean, professional UX

---

## How Hooks Work

1. **Agent generates/saves a resource** (entity, workflow, requirement)
2. **Agent returns a hook** in the response
3. **UI receives the hook** and renders it as a clickable button
4. **User clicks the button** (or doesn't) - their choice
5. **No agent involvement needed** - UI handles the action

---

## Using `create_open_canvas_tab_hook()`

### Import
```python
from application.agents.shared.hook_utils import create_open_canvas_tab_hook
```

### Basic Usage
```python
hook = create_open_canvas_tab_hook(
    conversation_id=conversation_id,
    tab_name="entities",
    message="View Customer Entity"  # Button text
)
```

### Valid tab_name values
- `"entities"` - Opens Canvas Entities tab
- `"workflows"` - Opens Canvas Workflows tab
- `"requirements"` - Opens Canvas Requirements tab
- `"cloud"` - Opens Cloud/Environments tab

### Return in Response
```python
return {
    "message": "✅ Customer entity created and saved!",
    "hook": hook
}
```

---

## Real-World Examples

### Example 1: After Creating an Entity

**WRONG:**
```
"I've created the Customer entity. Would you like me to open it in Canvas?"
```

**RIGHT:**
```python
hook = create_open_canvas_tab_hook(
    conversation_id=conversation_id,
    tab_name="entities",
    message="View Customer Entity"
)

return {
    "message": "✅ Customer entity created and saved!\n\n📊 Fields: id, name, email, created_at",
    "hook": hook
}
```

### Example 2: After Creating a Workflow

**WRONG:**
```
"The OrderProcessing workflow is ready. Should I open it in Canvas?"
```

**RIGHT:**
```python
hook = create_open_canvas_tab_hook(
    conversation_id=conversation_id,
    tab_name="workflows",
    message="View OrderProcessing Workflow"
)

return {
    "message": "✅ OrderProcessing workflow created!\n\n📊 States: initial, validation, payment, completed",
    "hook": hook
}
```

### Example 3: After Creating Requirements

**WRONG:**
```
"I've written the requirements. Would you like to see them in Canvas?"
```

**RIGHT:**
```python
hook = create_open_canvas_tab_hook(
    conversation_id=conversation_id,
    tab_name="requirements",
    message="View Requirements"
)

return {
    "message": "✅ Requirements document created!\n\n📋 Includes user stories, acceptance criteria, and business rules",
    "hook": hook
}
```

---

## Other Common Hooks

### `create_option_selection_hook()`
Use when you need the user to choose from options.

**WRONG:**
```
"Should I create a new branch or use an existing one?"
```

**RIGHT:**
```python
hook = create_option_selection_hook(
    conversation_id=conversation_id,
    question="How would you like to proceed?",
    options=[
        {"value": "new", "label": "Create New Branch"},
        {"value": "existing", "label": "Use Existing Branch"}
    ]
)
```

### `create_code_changes_hook()`
Use when code changes are made and canvas should refresh.

```python
hook = create_code_changes_hook(
    conversation_id=conversation_id,
    repository_name="my-repo",
    branch_name="main",
    changed_files=["entities/customer.json"],
    resource_type="entity"
)
```

### `create_background_task_hook()`
Use when starting a long-running task.

```python
hook = create_background_task_hook(
    task_id="build-123",
    task_type="application_build",
    task_name="Building Application",
    task_description="Compiling and building your application..."
)
```

---

## Key Principles

1. **Hooks Are Buttons**: They render as clickable UI elements
2. **No Permission Asking**: Don't ask "would you like me to...?"
3. **Direct Communication**: State what you did, show the hook
4. **User Controls**: User decides whether to click
5. **One Hook Per Action**: No duplicate hooks
6. **Clean UX**: Simple, professional interaction

---

## When to Use Hooks vs. When to Ask

### Use Hooks (Don't Ask):
- Opening canvas tabs
- Showing code changes
- Displaying resources
- Launching background tasks
- Offering next steps

### Ask the User (Use option_selection_hook):
- When user needs to make a choice
- When there are multiple valid paths forward
- When the agent can't decide for the user
- When user input is required

---

## Testing Your Hook Usage

Ask yourself:
1. ✅ Am I asking permission for something the UI can handle?
2. ✅ Could this be a button instead of a question?
3. ✅ Is the user in control of whether to click?
4. ✅ Is my message clear about what was accomplished?

If you answered yes to questions 1-3, use a hook instead of asking!

