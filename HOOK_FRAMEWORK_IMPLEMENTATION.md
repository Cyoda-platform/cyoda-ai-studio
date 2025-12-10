# Hook Framework Implementation Guide

## Overview

The Hook Framework provides a centralized, DRY, and SOLID-compliant system for managing UI hooks across agents and tools.

## Core Components

### 1. Hook Registry (`hook_registry.py`)
**Purpose:** Single source of truth for hook metadata

```python
from application.agents.shared.hook_registry import get_hook_registry

registry = get_hook_registry()
hook_metadata = registry.get_hook("open_canvas_tab")
tools_with_hooks = registry.get_tools_with_hooks()
```

**Key Methods:**
- `register(metadata)` - Register a hook
- `get_hook(name)` - Get hook by name
- `get_hooks_by_tool(tool_name)` - Get hooks created by tool
- `get_hooks_by_type(hook_type)` - Get hooks by type
- `list_all()` / `list_active()` - List hooks

### 2. Hook Definitions (`hook_definitions.py`)
**Purpose:** Centralized hook metadata definitions

```python
from application.agents.shared.hook_definitions import register_all_hooks

registry = HookRegistry()
register_all_hooks(registry)
```

**Add new hooks here** - Single place to define all hook metadata

### 3. Hook Factory (`hook_factory.py`)
**Purpose:** Validated hook creation with parameter checking

```python
from application.agents.shared.hook_factory import get_hook_factory

factory = get_hook_factory()
hook = factory.create_hook("open_canvas_tab", 
    conversation_id="conv-123",
    tab_name="entities"
)
```

**Key Methods:**
- `create_hook(name, **params)` - Create with validation
- `validate_parameters(name, params)` - Validate only
- `get_hook_documentation(name)` - Get formatted docs
- `list_hooks_for_tool(tool_name)` - Get tool's hooks

### 4. Hook Decorator (`hook_decorator.py`)
**Purpose:** Mark tools that create hooks for auto-discovery

```python
from application.agents.shared.hook_decorator import creates_hook

@creates_hook("code_changes")
@creates_hook("background_task")
async def deploy_user_application(tool_context, ...):
    # Tool implementation
    pass
```

**Key Functions:**
- `@creates_hook(*names)` - Decorator for tools
- `get_tool_hooks(func)` - Get hooks from tool
- `get_tools_with_hooks(tools)` - Map tools to hooks
- `validate_tool_hooks(tools)` - Validate all hooks exist

### 5. Prompt Hook Helper (`prompt_hook_helper.py`)
**Purpose:** Integrate hooks into agent prompts

```python
from application.agents.shared.prompt_hook_helper import get_prompt_hook_helper

helper = get_prompt_hook_helper()
available_hooks = helper.get_available_hooks()
instructions = helper.get_hook_instructions("open_canvas_tab")
reference = helper.generate_hook_reference_section()
```

**Key Methods:**
- `get_available_hooks()` - List all hooks
- `get_hook_instructions(name)` - Get usage instructions
- `get_hooks_for_tool(tool_name)` - Get tool's hooks
- `generate_hook_reference_section()` - Auto-generate prompt section
- `generate_hook_usage_guide()` - Complete guide

## Usage Patterns

### Pattern 1: Add New Hook
1. Add metadata to `hook_definitions.py`
2. Call `register_all_hooks()` to register
3. Reference in prompts using helper

### Pattern 2: Mark Tool with Hooks
1. Add `@creates_hook()` decorator to tool
2. Tool automatically discoverable
3. Validation ensures hooks exist

### Pattern 3: Generate Prompt Documentation
1. Use `PromptHookHelper` in prompt generation
2. Auto-generate hook reference sections
3. Keep prompts in sync with code

### Pattern 4: Validate Hook Usage
1. Use `HookFactory.validate_parameters()`
2. Catch errors early
3. Provide clear error messages

## Benefits

✅ **DRY Principle**
- Single source of truth for hook definitions
- No duplication across prompts and tools
- Changes propagate automatically

✅ **SOLID Principles**
- **S**ingle Responsibility: Each component has one job
- **O**pen/Closed: Extensible without modifying core
- **L**iskov Substitution: All hooks follow same interface
- **I**nterface Segregation: Tools only depend on what they need
- **D**ependency Inversion: Depend on abstractions, not implementations

✅ **Maintainability**
- Centralized hook definitions
- Auto-generated documentation
- Clear tool-hook relationships
- Easy to find and update hooks

✅ **Discoverability**
- Tools automatically discoverable
- Hooks easily queryable
- Documentation auto-generated
- Clear usage patterns

✅ **Testability**
- Hook creation independently testable
- Parameter validation testable
- Tool-hook mapping verifiable
- No tight coupling

## Migration Path

### Phase 1: Framework Setup (DONE)
- ✅ Create registry, factory, decorator, helper
- ✅ Define all existing hooks
- ✅ Initialize registry

### Phase 2: Tool Decoration
- Add `@creates_hook()` to all tools
- Validate all hooks are registered
- Test tool-hook mapping

### Phase 3: Prompt Integration
- Use `PromptHookHelper` in prompt generation
- Auto-generate hook reference sections
- Update prompt templates

### Phase 4: Cleanup
- Remove manual hook documentation from prompts
- Remove duplicate hook definitions
- Consolidate hook creation logic

## Next Steps

1. **Decorate existing tools** with `@creates_hook()`
2. **Update prompts** to use `PromptHookHelper`
3. **Add tests** for hook creation and validation
4. **Document** hook usage patterns
5. **Monitor** hook usage and deprecations

