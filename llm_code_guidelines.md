# LLM Engineering & Clean Code Standards

This document defines the architectural and stylistic standards for our codebase. We prioritize **narrative flow, modularity, and strict boundaries** to manage the complexity of LLM-based applications.

## 1. Architectural Philosophy

* **Dependency Rule:** High-level policy must not depend on low-level details. Dependencies must only point inward toward higher-level logic (e.g., Business logic should not know about `openai` or `langchain` specifics).
* **The "Newspaper" Rule:** Files should be organized from high-level summaries at the top to low-level implementation details at the bottom.
* **Command-Query Separation (CQS):** A function should either **do** something (Command/Side Effect) or **answer** something (Query/Return Data), but never both.

---

## 2. Structural Constraints

To maintain low cognitive load, we adhere to strict physical limits:

| Metric | Target | Hard Limit | Action if Exceeded |
| --- | --- | --- | --- |
| **Function Length** | 5–20 lines | 50 lines | Refactor/Extract Method |
| **File Length** | < 200 lines | 350 lines | Split into sub-modules |
| **Line Width** | 80-100 chars | 120 chars | Wrap or simplify logic |
| **Arguments** | 0–2 | 3 | Encapsulate in `Dataclass/Pydantic` |

---

## 3. Function Design & Logic

### Small & Atomic

* **Single Responsibility (SRP):** A function should do exactly one thing.
* **Indentation Depth:** If-statements and loops should contain only 1–2 lines, usually a single function call. This keeps the abstraction level consistent.
* **No Boolean Flags:** Instead of `process_data(data, save_to_db=True)`, split into `process_data(data)` and `process_and_save_data(data)`.

### Pure vs. Impure

* **Favor Purity:** Prioritize functions that map inputs to outputs without side effects. This is critical for testing LLM prompt logic.
* **Vertical Density:** Keep closely related code and variables physically close. Declare variables as close to their first usage as possible.

### Error Handling

* **Exceptions over Codes:** Use `try/except` blocks rather than returning error codes (e.g., `return -1`).
* **Fail Fast:** Validate LLM outputs against Pydantic models immediately upon receipt.

---

## 4. Naming & Formatting

Names must reveal intent without requiring comments.

* **Scope-Based Length:** Use short/single-letter names (e.g., `i`, `v`) **only** for local variables in very small scopes. Global or long-lived entities require descriptive names.
* **Standard Suffixes:**
* **Prompts:** `_prompt_template` (e.g., `extract_entities_prompt_template`)
* **Booleans:** `is_`, `has_`, `should_` (e.g., `has_token_limit`)



---

## 5. LLM-Specific Standards

LLM logic is non-deterministic and requires dedicated boundaries.

### Prompt Management

* **Externalize:** No long-form strings in Python logic. Use `.yaml` or `.jinja2` files in `application/agents/shared/prompts/`.
* **Abstraction:** Hide provider-specific logic (OpenAI, Anthropic) behind an **Adapter** layer.

### Token & Cost Control

* **Context Awareness:** Every LLM-calling function must support optional telemetry (logging tokens, latency, and cost).
* **Centralized Config:** Access API keys via a central `Config` object; never call `os.getenv()` inside business logic.

---

## 6. Code Review Checklist

1. **Abstraction Level:** Does every line in this function belong at the same level of detail?
2. **Vertical Flow:** Does the caller appear directly above the callee?
3. **Typed Signatures:** Are all inputs and outputs type-hinted? (`def call(q: str) -> str:`)
4. **Side Effects:** Is it clear which functions change state and which only return data?
5. **Dryness:** Is there any logic duplication that could be abstracted?
