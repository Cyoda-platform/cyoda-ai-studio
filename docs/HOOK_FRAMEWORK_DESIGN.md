# Hook Framework Design - Analysis & Architecture

## Current State Analysis

### ✅ What Works Well
1. **Hook Creation Functions** - Well-organized in `hook_utils.py` with clear naming
2. **Hook Types** - Diverse: `ui_function`, `code_changes`, `option_selection`, `cloud_window`, `canvas_tab`, `background_task`
3. **Documentation** - `UI_HOOKS_GUIDE.md` provides clear patterns
4. **Streaming Integration** - Hooks properly extracted and sent via SSE

### ❌ Current Issues (DRY & SOLID Violations)

#### 1. **Prompt-Tool Mismatch**
- Prompts reference hook functions but don't have a registry
- Each prompt manually documents which tools create hooks
- No single source of truth for hook-tool mapping
- Duplication: Same hook instructions repeated across multiple prompts

#### 2. **Tool-Hook Coupling**
- Tools create hooks inline with business logic
- No separation of concerns (tool logic vs. hook creation)
- Hook creation scattered throughout tool implementations
- Hard to test hook creation independently

#### 3. **Hook Metadata Missing**
- No registry of available hooks
- No hook documentation accessible to prompts
- No validation of hook parameters
- No hook versioning or deprecation tracking

#### 4. **Prompt Documentation Issues**
- Hook usage documented in multiple places (prompts, guides, comments)
- No programmatic way to discover which tools create hooks
- Manual synchronization between tool changes and prompt updates
- Inconsistent hook naming conventions

#### 5. **Tool Organization**
- Tools grouped by category but no hook metadata
- No way to query "which tools create hooks?"
- No hook-specific tool grouping
- Tool imports scattered across agent files

## Proposed Hook Framework

### Architecture Principles (SOLID)
- **S**ingle Responsibility: Separate hook creation from tool logic
- **O**pen/Closed: Extensible hook registry without modifying core
- **L**iskov Substitution: All hooks follow same interface
- **I**nterface Segregation: Tools only depend on hook creation interface
- **D**ependency Inversion: Tools depend on hook abstractions, not implementations

### Core Components

#### 1. **Hook Registry** (`hook_registry.py`)
```python
class HookMetadata:
    name: str
    hook_type: str
    description: str
    parameters: Dict[str, ParameterSpec]
    when_to_use: str
    example: str
    tool_name: str
    
class HookRegistry:
    register(metadata: HookMetadata)
    get_hook(name: str) -> HookMetadata
    get_hooks_by_tool(tool_name: str) -> List[HookMetadata]
    get_hooks_by_type(hook_type: str) -> List[HookMetadata]
    list_all() -> List[HookMetadata]
```

#### 2. **Hook Factory** (`hook_factory.py`)
```python
class HookFactory:
    create_hook(hook_name: str, **params) -> Dict[str, Any]
    validate_parameters(hook_name: str, params: Dict) -> bool
    get_hook_template(hook_name: str) -> str
```

#### 3. **Tool Hook Decorator** (`hook_decorator.py`)
```python
@creates_hook("issue_technical_user")
@creates_hook("cloud_window")
async def deploy_cyoda_environment(...):
    # Tool logic
    hook = create_issue_technical_user_hook(...)
    return wrap_response_with_hook(message, hook)
```

#### 4. **Prompt Hook Helper** (`prompt_hook_helper.py`)
```python
class PromptHookHelper:
    get_available_hooks() -> List[HookMetadata]
    get_hook_instructions(hook_name: str) -> str
    get_tool_for_hook(hook_name: str) -> str
    generate_hook_documentation() -> str
```

### Implementation Strategy

**Phase 1: Hook Registry & Metadata**
- Create `hook_registry.py` with all hook metadata
- Register all existing hooks with parameters and documentation
- Add validation layer

**Phase 2: Hook Factory**
- Extract hook creation logic into factory
- Centralize parameter validation
- Add hook versioning support

**Phase 3: Tool Decorators**
- Add `@creates_hook()` decorator to tools
- Auto-register tools with their hooks
- Enable hook discovery

**Phase 4: Prompt Integration**
- Create prompt helper for hook documentation
- Generate hook reference sections automatically
- Add hook usage examples to prompts

**Phase 5: Testing & Validation**
- Unit tests for hook creation
- Integration tests for tool-hook coupling
- Prompt validation against registry

## Benefits

✅ **DRY**: Single source of truth for hook definitions
✅ **SOLID**: Clear separation of concerns
✅ **Maintainability**: Changes in one place propagate everywhere
✅ **Discoverability**: Tools and hooks easily discoverable
✅ **Testability**: Hook creation independently testable
✅ **Documentation**: Auto-generated from registry
✅ **Extensibility**: New hooks added without modifying core

