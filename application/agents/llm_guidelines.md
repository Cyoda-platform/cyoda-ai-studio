## Agent Code Patterns & Organization (v1.1)

**Goal:** Modular, thin-registry architecture following the `environment` agent gold standard.

### 1. Structure & Size Limits

```text
agent_name/
├── agent.py (Max 300 lines)        # Agent definition & prompt loading
├── prompts.py                      # Template strings only
├── tools.py (Max 100 lines)        # Thin Registry: Imports implementations
└── tool_definitions/               # Implementation Root
    ├── STRUCTURE.md                # Local architecture docs
    ├── common/                     # models/, formatters/, utils/, constants/
    └── {domain}/                   # Domain grouping (e.g., 'k8s', 'git')
        ├── tools/                  # Public tool files (*_tool.py)
        └── helpers/                # Internal logic (_*.py)

```

| Component | Target Lines | Max Lines | Role |
| --- | --- | --- | --- |
| **agent.py** | 200 | 300 | Config & registration |
| **tools.py** | 80 | 100 | **Thin registry only** |
| **Tool file** | 50 | 150 | Single tool logic |
| **Helpers** | 150 | 400 | Complex shared logic |
| **Utils** | 100 | 200 | Reusable logic/decorators |

---

### 2. Core Implementation Patterns

#### A. Tool Implementation Template

```python
@require_authenticated_user
@handle_tool_errors
async def action_name(param: str, tool_context: ToolContext) -> str:
    """Docstring with Args/Returns."""
    # 1. Extract context/state
    user_id = tool_context.state.get("user_id")
    # 2. Call service layer
    result = await get_service().execute(user_id, param)
    # 3. Return via common/formatters
    return format_success_response(result)

```

#### B. Common Utilities (Don't Repeat Yourself)

* **Constants:** Move all magic strings (e.g., `"python"`, `".json"`) to `common/constants/constants.py`.
* **Config:** Use a `@dataclass` in `common/constants/config.py` for all `os.getenv` calls.
* **Formatters:** All human-readable strings or JSON structures go in `common/formatters/`.

---

### 3. Standards & Quality Checklist

| Category | Requirement |
| --- | --- |
| **Naming** | Tools: `{action}_tool.py`. Helpers: `_{name}.py`. Functions: `verb_noun`. |
| **Imports** | 1. Future 2. Stdlib 3. Third-party 4. Local App 5. Relative. |
| **Logic** | **SRP:** One tool = one task. Extract repeated logic to helpers. |
| **Error Handling** | Use `@handle_tool_errors` decorator. Return `str` error messages. |
| **Testing** | Min 75% coverage. Tests in `tests/unit/agents/{agent_name}/`. |
| **Docs** | `STRUCTURE.md` and `README.md` required in every agent folder. |

---
