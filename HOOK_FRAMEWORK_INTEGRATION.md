# Hook Framework Integration Guide

## Quick Start

### 1. Query Available Hooks
```python
from application.agents.shared.hook_registry import get_hook_registry

registry = get_hook_registry()
all_hooks = registry.list_active()
tool_hooks = registry.get_hooks_by_tool("environment_agent_tools")
```

### 2. Create Hooks with Validation
```python
from application.agents.shared.hook_factory import get_hook_factory

factory = get_hook_factory()
hook = factory.create_hook(
    "open_canvas_tab",
    conversation_id="conv-123",
    tab_name="entities"
)
```

### 3. Mark Tools with Hooks
```python
from application.agents.shared.hook_decorator import creates_hook

@creates_hook("code_changes")
@creates_hook("background_task")
async def deploy_user_application(tool_context, ...):
    # Implementation
    pass
```

### 4. Generate Prompt Documentation
```python
from application.agents.shared.prompt_hook_helper import get_prompt_hook_helper

helper = get_prompt_hook_helper()
reference = helper.generate_hook_reference_section()
mapping = helper.generate_tool_hook_mapping()
```

## Integration Steps

### Step 1: Add Hook Metadata
Edit `hook_definitions.py`:
```python
registry.register(
    HookMetadata(
        name="my_hook",
        hook_type="custom",
        description="What this hook does",
        parameters=[
            ParameterSpec(
                name="param1",
                type="str",
                required=True,
                description="Parameter description"
            )
        ],
        when_to_use="When to use this hook",
        tool_names=["my_tool"],
        example="hook = create_my_hook(...)"
    )
)
```

### Step 2: Decorate Tools
Add to tool functions:
```python
@creates_hook("my_hook")
async def my_tool(tool_context, ...):
    # Implementation
    pass
```

### Step 3: Update Prompts
Use helper in prompt generation:
```python
helper = get_prompt_hook_helper()
prompt += helper.generate_hook_reference_section()
```

### Step 4: Validate
```python
from application.agents.shared.hook_decorator import validate_tool_hooks

validate_tool_hooks(agent_tools)  # Raises if hooks not registered
```

## Common Patterns

### Pattern: Tool Creates Multiple Hooks
```python
@creates_hook("code_changes")
@creates_hook("background_task")
async def deploy_application(tool_context, ...):
    # Create both hooks
    code_hook = factory.create_hook("code_changes", ...)
    task_hook = factory.create_hook("background_task", ...)
    
    # Return with combined hook
    combined = create_combined_hook(code_hook, task_hook)
    return wrap_response_with_hook(message, combined)
```

### Pattern: Conditional Hook Creation
```python
@creates_hook("option_selection")
@creates_hook("cloud_window")
async def check_environment(tool_context, ...):
    if environment_exists:
        hook = factory.create_hook("cloud_window", ...)
    else:
        hook = factory.create_hook("option_selection", ...)
    
    return wrap_response_with_hook(message, hook)
```

### Pattern: Hook with Dynamic Parameters
```python
@creates_hook("background_task")
async def deploy_environment(tool_context, env_name: str):
    hook = factory.create_hook(
        "background_task",
        task_id=generate_task_id(),
        task_type="deploy",
        task_name=f"Deploy {env_name}",
        conversation_id=tool_context.state.get("conversation_id")
    )
    return wrap_response_with_hook(message, hook)
```

## Benefits Realized

### DRY (Don't Repeat Yourself)
- ✅ Single source of truth for hook definitions
- ✅ No duplication across prompts and tools
- ✅ Changes propagate automatically

### SOLID Principles
- ✅ **S**: Each component has single responsibility
- ✅ **O**: Extensible without modifying existing code
- ✅ **L**: All hooks follow same interface
- ✅ **I**: Tools only depend on what they use
- ✅ **D**: Depend on abstractions, not implementations

### Maintainability
- ✅ Centralized hook definitions
- ✅ Auto-generated documentation
- ✅ Clear tool-hook relationships
- ✅ Easy to find and update hooks

### Discoverability
- ✅ Tools automatically discoverable
- ✅ Hooks easily queryable
- ✅ Documentation auto-generated
- ✅ Clear usage patterns

### Testability
- ✅ Hook creation independently testable
- ✅ Parameter validation testable
- ✅ Tool-hook mapping verifiable
- ✅ No tight coupling

## Troubleshooting

### Hook Not Found
```
HookValidationError: Unknown hook: my_hook
```
**Solution:** Register hook in `hook_definitions.py`

### Missing Required Parameter
```
HookValidationError: Missing required parameter: conversation_id
```
**Solution:** Check hook metadata and provide all required parameters

### Tool Hook Not Registered
```
ValueError: Tool 'my_tool' references unknown hook: my_hook
```
**Solution:** Register hook before decorating tool

## Testing

### Test Hook Creation
```python
def test_hook_creation():
    factory = get_hook_factory()
    hook = factory.create_hook("open_canvas_tab", 
        conversation_id="test", tab_name="entities")
    assert hook["type"] == "canvas_tab"
```

### Test Hook Validation
```python
def test_hook_validation():
    factory = get_hook_factory()
    with pytest.raises(HookValidationError):
        factory.create_hook("open_canvas_tab", 
            conversation_id="test")  # Missing tab_name
```

### Test Tool Hooks
```python
def test_tool_hooks():
    from application.agents.shared.hook_decorator import get_tool_hooks
    hooks = get_tool_hooks(my_tool)
    assert "my_hook" in hooks
```

## Next Steps

1. **Decorate all tools** with `@creates_hook()`
2. **Update all prompts** to use `PromptHookHelper`
3. **Add tests** for hook creation and validation
4. **Monitor** hook usage and deprecations
5. **Document** new hooks as they're added

