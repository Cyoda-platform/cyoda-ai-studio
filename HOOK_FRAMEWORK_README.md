# Hook Framework - Complete Guide

## Overview

A comprehensive, DRY, and SOLID-compliant hook framework that integrates seamlessly with prompts and tools. Provides centralized hook management, validation, and documentation generation.

## ✅ What's Included

### Core Framework Components
- **Hook Registry** - Single source of truth for hook metadata
- **Hook Factory** - Validated hook creation with parameter checking
- **Hook Decorator** - Mark tools that create hooks for auto-discovery
- **Prompt Helper** - Generate hook documentation for prompts
- **Hook Definitions** - Centralized metadata for all hooks

### Documentation
- `HOOK_FRAMEWORK_DESIGN.md` - Architecture and analysis
- `HOOK_FRAMEWORK_IMPLEMENTATION.md` - Implementation guide
- `HOOK_FRAMEWORK_INTEGRATION.md` - Step-by-step integration
- `HOOK_FRAMEWORK_SUMMARY.md` - Executive summary
- `hook_framework_examples.py` - Code examples

## 🚀 Quick Start

### 1. Query Hooks
```python
from application.agents.shared.hook_registry import get_hook_registry

registry = get_hook_registry()
all_hooks = registry.list_active()
tool_hooks = registry.get_hooks_by_tool("environment_agent_tools")
```

### 2. Create Hooks
```python
from application.agents.shared.hook_factory import get_hook_factory

factory = get_hook_factory()
hook = factory.create_hook(
    "open_canvas_tab",
    conversation_id="conv-123",
    tab_name="entities"
)
```

### 3. Mark Tools
```python
from application.agents.shared.hook_decorator import creates_hook

@creates_hook("code_changes")
@creates_hook("background_task")
async def deploy_application(tool_context, ...):
    # Implementation
    pass
```

### 4. Generate Prompts
```python
from application.agents.shared.prompt_hook_helper import get_prompt_hook_helper

helper = get_prompt_hook_helper()
reference = helper.generate_hook_reference_section()
mapping = helper.generate_tool_hook_mapping()
```

## 📚 Available Hooks

| Hook | Type | Purpose | Created By |
|------|------|---------|-----------|
| `open_canvas_tab` | canvas_tab | Open canvas tabs | github_agent_tools |
| `code_changes` | code_changes | Trigger canvas refresh | github_agent_tools |
| `option_selection` | option_selection | Show user options | environment, setup agents |
| `cloud_window` | cloud_window | Open cloud panel | environment_agent_tools |
| `background_task` | background_task | Track background tasks | environment, github agents |
| `issue_technical_user` | ui_function | Issue M2M credentials | environment, setup agents |

## 🏗️ Architecture

### DRY Principle
- ✅ Single source of truth for hook definitions
- ✅ No duplication across prompts and tools
- ✅ Changes propagate automatically

### SOLID Principles
- ✅ **S**ingle Responsibility: Each component has one job
- ✅ **O**pen/Closed: Extensible without modifying core
- ✅ **L**iskov Substitution: All hooks follow same interface
- ✅ **I**nterface Segregation: Tools only depend on what they need
- ✅ **D**ependency Inversion: Depend on abstractions, not implementations

## 📁 File Structure

```
application/agents/shared/
├── hook_registry.py              # Hook metadata registry
├── hook_definitions.py           # Hook definitions
├── hook_factory.py               # Hook creation factory
├── hook_decorator.py             # Tool decoration
├── prompt_hook_helper.py         # Prompt integration
└── hook_framework_examples.py    # Usage examples
```

## 🔧 Common Tasks

### Add New Hook
1. Edit `hook_definitions.py`
2. Add `HookMetadata` with parameters
3. Call `register_all_hooks()`
4. Reference in tools and prompts

### Decorate Tool
```python
@creates_hook("hook_name")
async def my_tool(tool_context, ...):
    pass
```

### Validate Hooks
```python
from application.agents.shared.hook_decorator import validate_tool_hooks
validate_tool_hooks(agent_tools)
```

### Generate Documentation
```python
helper = get_prompt_hook_helper()
docs = helper.generate_hook_usage_guide()
```

## ✨ Key Features

### Validation
- Parameter validation at creation time
- Early error detection with clear messages
- Hook existence verification
- Deprecation tracking

### Documentation
- Auto-generated hook reference sections
- Tool-hook mapping documentation
- Usage examples for each hook
- Comprehensive integration guides

### Discoverability
- Tools automatically discoverable via decorators
- Hooks easily queryable by name, type, or tool
- Clear tool-hook relationships
- Documentation auto-generated from metadata

### Testability
- Hook creation independently testable
- Parameter validation testable
- Tool-hook mapping verifiable
- No tight coupling

## 🧪 Testing

### Test Hook Creation
```python
def test_hook_creation():
    factory = get_hook_factory()
    hook = factory.create_hook("open_canvas_tab", 
        conversation_id="test", tab_name="entities")
    assert hook["type"] == "canvas_tab"
```

### Test Validation
```python
def test_validation():
    factory = get_hook_factory()
    with pytest.raises(HookValidationError):
        factory.create_hook("open_canvas_tab", 
            conversation_id="test")  # Missing tab_name
```

### Test Tool Hooks
```python
def test_tool_hooks():
    hooks = get_tool_hooks(my_tool)
    assert "my_hook" in hooks
```

## 📖 Documentation

- **Design**: Architecture and analysis
- **Implementation**: How to use the framework
- **Integration**: Step-by-step integration guide
- **Summary**: Executive summary
- **Examples**: Code examples and patterns

## 🎯 Next Steps

1. **Review** framework components
2. **Decorate** existing tools with `@creates_hook()`
3. **Update** prompts to use `PromptHookHelper`
4. **Add** tests for hook creation and validation
5. **Monitor** hook usage and deprecations

## 🆘 Troubleshooting

### Hook Not Found
```
HookValidationError: Unknown hook: my_hook
```
→ Register hook in `hook_definitions.py`

### Missing Parameter
```
HookValidationError: Missing required parameter: conversation_id
```
→ Check hook metadata and provide all required parameters

### Tool Hook Not Registered
```
ValueError: Tool 'my_tool' references unknown hook: my_hook
```
→ Register hook before decorating tool

## 📞 Support

1. Check the integration guide
2. Review code examples
3. Examine existing hook definitions
4. Run tests to validate setup

## ✅ Verification

All components tested and working:
- ✅ Registry initialization
- ✅ Hook creation with validation
- ✅ Parameter validation
- ✅ Tool decoration
- ✅ Prompt documentation generation
- ✅ Hook discovery and querying

Ready for integration into existing agents!

