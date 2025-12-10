# Hook Framework Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     HOOK FRAMEWORK SYSTEM                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    HOOK DEFINITIONS LAYER                         │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  hook_definitions.py                                       │  │
│  │  - Centralized hook metadata                               │  │
│  │  - HookMetadata objects with parameters                    │  │
│  │  - register_all_hooks() initialization                     │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────┐
│                    HOOK REGISTRY LAYER                            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  hook_registry.py                                          │  │
│  │  - Single source of truth                                  │  │
│  │  - Metadata storage and indexing                           │  │
│  │  - Query by name, type, or tool                            │  │
│  │  - Deprecation tracking                                    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
         ↙                    ↓                    ↘
    ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐
    │   FACTORY   │   │  DECORATOR   │   │  PROMPT HELPER   │
    └─────────────┘   └──────────────┘   └──────────────────┘
         ↓                    ↓                    ↓
    ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐
    │ Validation  │   │ Tool Marking │   │ Documentation    │
    │ Creation    │   │ Discovery    │   │ Generation       │
    │ Parameters  │   │ Mapping      │   │ Integration      │
    └─────────────┘   └──────────────┘   └──────────────────┘
         ↓                    ↓                    ↓
    ┌─────────────────────────────────────────────────────────┐
    │              AGENT TOOLS & PROMPTS                       │
    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
    │  │ Environment  │  │    Setup     │  │    GitHub    │  │
    │  │    Agent     │  │    Agent     │  │    Agent     │  │
    │  └──────────────┘  └──────────────┘  └──────────────┘  │
    └─────────────────────────────────────────────────────────┘
         ↓                    ↓                    ↓
    ┌─────────────────────────────────────────────────────────┐
    │                  STREAMING SERVICE                       │
    │  - Hook extraction from tool_context                     │
    │  - Hook normalization                                    │
    │  - SSE streaming to frontend                             │
    └─────────────────────────────────────────────────────────┘
         ↓
    ┌─────────────────────────────────────────────────────────┐
    │                   FRONTEND UI                            │
    │  - Hook rendering as buttons/options                     │
    │  - User interaction handling                             │
    │  - Canvas refresh on code changes                        │
    └─────────────────────────────────────────────────────────┘
```

## Component Relationships

### Hook Registry
```
HookRegistry
├── _hooks: Dict[str, HookMetadata]
├── _tool_to_hooks: Dict[str, List[str]]
├── _type_to_hooks: Dict[str, List[str]]
└── Methods:
    ├── register(metadata)
    ├── get_hook(name)
    ├── get_hooks_by_tool(tool_name)
    ├── get_hooks_by_type(hook_type)
    └── list_all() / list_active()
```

### Hook Factory
```
HookFactory
├── registry: HookRegistry
└── Methods:
    ├── create_hook(name, **params)
    ├── validate_parameters(name, params)
    ├── get_hook_documentation(name)
    └── list_hooks_for_tool(tool_name)
```

### Hook Decorator
```
@creates_hook(*hook_names)
├── Stores hook names on function
├── Enables tool discovery
├── Supports stacking
└── Functions:
    ├── get_tool_hooks(func)
    ├── get_tools_with_hooks(tools)
    ├── validate_tool_hooks(tools)
    └── generate_tool_hook_documentation(tools)
```

### Prompt Helper
```
PromptHookHelper
├── registry: HookRegistry
├── factory: HookFactory
└── Methods:
    ├── get_available_hooks()
    ├── get_hook_instructions(name)
    ├── get_hooks_for_tool(tool_name)
    ├── generate_hook_reference_section()
    ├── generate_tool_hook_mapping()
    └── generate_hook_usage_guide()
```

## Data Flow

### Hook Creation Flow
```
Tool Implementation
    ↓
@creates_hook("hook_name")
    ↓
factory.create_hook("hook_name", **params)
    ↓
HookFactory.validate_parameters()
    ↓
HookRegistry.get_hook()
    ↓
Create Hook Object
    ↓
wrap_response_with_hook(message, hook)
    ↓
tool_context.state["last_tool_hook"] = hook
    ↓
Streaming Service extracts hook
    ↓
SSE sends to Frontend
    ↓
Frontend renders as UI element
```

### Hook Discovery Flow
```
Agent Tools
    ↓
@creates_hook() decorators
    ↓
get_tool_hooks(tool)
    ↓
get_tools_with_hooks(tools)
    ↓
Tool-Hook Mapping
    ↓
PromptHookHelper.generate_tool_hook_mapping()
    ↓
Auto-generated Prompt Documentation
```

### Hook Validation Flow
```
Tool Definition
    ↓
@creates_hook("hook_name")
    ↓
validate_tool_hooks(tools)
    ↓
HookRegistry.validate_hook_exists()
    ↓
✓ Valid or ✗ Error
    ↓
Early Detection of Issues
```

## Integration Points

### With Tools
- Tools decorated with `@creates_hook()`
- Tools call `factory.create_hook()`
- Tools return `wrap_response_with_hook()`

### With Prompts
- Prompts use `PromptHookHelper`
- Auto-generated hook reference sections
- Tool-hook mapping documentation
- Hook usage examples

### With Streaming
- Hooks extracted from `tool_context.state`
- Hooks normalized and validated
- Hooks sent via SSE to frontend
- Frontend renders hooks as UI elements

### With Testing
- Hook creation independently testable
- Parameter validation testable
- Tool-hook mapping verifiable
- No tight coupling to implementation

## Design Patterns Used

### 1. Registry Pattern
- Centralized metadata storage
- Query by multiple criteria
- Extensible without modification

### 2. Factory Pattern
- Validated object creation
- Parameter checking
- Error handling

### 3. Decorator Pattern
- Mark tools with metadata
- Enable auto-discovery
- Support stacking

### 4. Helper Pattern
- Encapsulate complex operations
- Provide convenient methods
- Generate documentation

### 5. Singleton Pattern
- Global registry instance
- Global factory instance
- Global helper instance

## SOLID Compliance

### Single Responsibility
- Registry: Store and query metadata
- Factory: Create and validate hooks
- Decorator: Mark tools with hooks
- Helper: Generate documentation

### Open/Closed
- Add new hooks without modifying core
- Extend with new hook types
- Add new query methods to registry

### Liskov Substitution
- All hooks follow same interface
- All hook types compatible
- Consistent parameter structure

### Interface Segregation
- Tools only depend on factory
- Prompts only depend on helper
- Registry independent of usage

### Dependency Inversion
- Tools depend on abstractions
- Prompts depend on abstractions
- No circular dependencies

## Performance Characteristics

- **Registry Lookup**: O(1) by name, O(n) by type/tool
- **Hook Creation**: O(1) with validation
- **Tool Discovery**: O(n) where n = number of tools
- **Documentation Generation**: O(n) where n = number of hooks

## Extensibility

### Add New Hook Type
1. Add to `hook_definitions.py`
2. Register in `register_all_hooks()`
3. Reference in tools and prompts

### Add New Query Method
1. Add to `HookRegistry`
2. Update indexing in `register()`
3. Document in integration guide

### Add New Validation Rule
1. Add to `HookFactory._validate_parameters()`
2. Update error messages
3. Add tests

## Security Considerations

- Parameter validation prevents injection
- Hook names validated against registry
- Tool names validated against registry
- No arbitrary code execution
- Clear error messages for debugging

