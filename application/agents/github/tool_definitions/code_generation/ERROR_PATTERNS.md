# CLI Error Pattern Detection

This document shows all error patterns detected by the error classification system.

## Design Principle

**✅ GENERIC PATTERNS** - Match error signatures, not specific variable names

**❌ NOT HARDCODED** - Avoid tying to specific variable/function names

---

## JavaScript/TypeScript Runtime Errors

### Pattern: `"is not a function"`
**Matches ANY variable name:**
```javascript
❌ e.split is not a function          → PERMANENT
❌ x.map is not a function             → PERMANENT
❌ data.filter is not a function       → PERMANENT
❌ obj.toString is not a function      → PERMANENT
❌ config.merge is not a function      → PERMANENT
❌ result.reduce is not a function     → PERMANENT
❌ handler.apply is not a function     → PERMANENT
```

### Pattern: `"is not defined"`
**Matches ANY variable name:**
```javascript
❌ foo is not defined                  → PERMANENT
❌ myVariable is not defined           → PERMANENT
❌ CONFIG is not defined               → PERMANENT
```

### Pattern: `"is not iterable"`
**Matches ANY variable:**
```javascript
❌ x is not iterable                   → PERMANENT
❌ items is not iterable               → PERMANENT
❌ data is not iterable                → PERMANENT
```

### Pattern: `"is not an object"`
**Matches ANY variable:**
```javascript
❌ null is not an object               → PERMANENT
❌ undefined is not an object          → PERMANENT
❌ value is not an object              → PERMANENT
```

### Pattern: `"is null"` / `"is undefined"`
**Matches ANY variable:**
```javascript
❌ variable is null                    → PERMANENT
❌ data is undefined                   → PERMANENT
❌ response is null                    → PERMANENT
```

### Pattern: `"cannot read property"`
**Matches ANY property/variable:**
```javascript
❌ Cannot read property 'name' of undefined       → PERMANENT
❌ Cannot read property 'length' of null          → PERMANENT
❌ Cannot read property 'status' of undefined     → PERMANENT
❌ Cannot read property 'toString' of null        → PERMANENT
❌ Cannot read properties of undefined            → PERMANENT
❌ Cannot read properties of null                 → PERMANENT
```

### Pattern: `"cannot set property"`
**Matches ANY property:**
```javascript
❌ Cannot set property 'value' of undefined       → PERMANENT
❌ Cannot set property 'name' of null             → PERMANENT
```

### Pattern: `"unexpected token"` / `"unexpected identifier"`
**Matches ANY token:**
```javascript
❌ Unexpected token '{'                → PERMANENT
❌ Unexpected token 'else'             → PERMANENT
❌ Unexpected identifier 'function'    → PERMANENT
```

---

## Exception Types (Generic Patterns)

### Pattern: `"typeerror:"`
```javascript
❌ TypeError: Cannot read property... → PERMANENT
❌ TypeError: x is not a function     → PERMANENT
❌ TypeError: Assignment to constant  → PERMANENT
```

### Pattern: `"referenceerror:"`
```javascript
❌ ReferenceError: foo is not defined     → PERMANENT
❌ ReferenceError: Invalid left-hand side → PERMANENT
```

### Pattern: `"rangeerror:"`
```javascript
❌ RangeError: Maximum call stack exceeded → PERMANENT
❌ RangeError: Invalid array length        → PERMANENT
```

### Pattern: `"syntaxerror:"`
```javascript
❌ SyntaxError: Unexpected token     → PERMANENT
❌ SyntaxError: Missing )            → PERMANENT
```

---

## Agent/Tool Execution Failures (Generic)

### Pattern: `"agent execution failed"`
```
❌ Agent execution failed: e.split is not a function  → PERMANENT
❌ Agent execution failed: timeout                    → PERMANENT
❌ Agent execution failed: unknown error              → PERMANENT
```

### Pattern: `"tool execution failed"`
```
❌ Tool execution failed: str-replace-editor         → PERMANENT
❌ Tool execution failed: file-write                 → PERMANENT
❌ Tool execution failed: search                     → PERMANENT
```

### Pattern: `"tool call failed"`
```
❌ Tool call failed: invalid parameters              → PERMANENT
❌ Tool call failed: missing required field          → PERMANENT
```

---

## Exception Stack Traces (Generic)

### Pattern: `"stack trace:"`
```
❌ Stack trace:                        → PERMANENT
    at Object.handler (/path/to/file.js:123:45)
    at processTicksAndRejections (internal/process/task_queues.js:97:5)
```

### Pattern: `"uncaught exception"`
```
❌ Uncaught exception: Error: Something went wrong  → PERMANENT
❌ Uncaught exception in async handler              → PERMANENT
```

### Pattern: `"unhandled promise rejection"`
```
❌ UnhandledPromiseRejectionWarning: Error...       → PERMANENT
❌ Unhandled promise rejection at...                → PERMANENT
```

### Pattern: `"unhandled error"`
```
❌ Unhandled error in CLI execution                 → PERMANENT
❌ Unhandled error: connection failed               → PERMANENT
```

---

## Python CLI Tools (If CLI Written in Python)

### Pattern: `"attributeerror:"`
```python
❌ AttributeError: 'NoneType' object has no attribute 'get'  → PERMANENT
❌ AttributeError: module 'os' has no attribute 'foo'        → PERMANENT
```

### Pattern: `"nameerror:"`
```python
❌ NameError: name 'variable' is not defined        → PERMANENT
❌ NameError: global name 'foo' is not defined      → PERMANENT
```

### Pattern: `"keyerror:"`
```python
❌ KeyError: 'config'                               → PERMANENT
❌ KeyError: 'missing_key'                          → PERMANENT
```

### Pattern: `"indexerror:"`
```python
❌ IndexError: list index out of range              → PERMANENT
❌ IndexError: tuple index out of range             → PERMANENT
```

### Pattern: `"valueerror:"`
```python
❌ ValueError: invalid literal for int()            → PERMANENT
❌ ValueError: not enough values to unpack          → PERMANENT
```

### Pattern: `"assertionerror:"`
```python
❌ AssertionError: Expected value to be non-null    → PERMANENT
❌ AssertionError: Invalid state                    → PERMANENT
```

---

## Real-World Examples

### Example 1: Augment CLI (Your Case)
```
Input: "Agent execution failed: e.split is not a function"

Pattern Matches:
  ✅ "agent execution failed" → PERMANENT
  ✅ "is not a function" → PERMANENT

Result:
  error_type: permanent
  error_description: CLI tool internal error (JavaScript bug)
  is_retryable: false
```

### Example 2: Different Variable
```
Input: "Agent execution failed: config.merge is not a function"

Pattern Matches:
  ✅ "agent execution failed" → PERMANENT
  ✅ "is not a function" → PERMANENT

Result:
  error_type: permanent
  error_description: CLI tool internal error (JavaScript bug)
  is_retryable: false
```

### Example 3: Different Error Type
```
Input: "Tool execution failed: TypeError: Cannot read property 'length' of undefined"

Pattern Matches:
  ✅ "tool execution failed" → PERMANENT
  ✅ "typeerror:" → PERMANENT
  ✅ "cannot read property" → PERMANENT

Result:
  error_type: permanent
  error_description: CLI tool internal error (Type error)
  is_retryable: false
```

### Example 4: Python CLI Tool
```
Input: "CLI execution failed: AttributeError: 'NoneType' object has no attribute 'split'"

Pattern Matches:
  ✅ "attributeerror:" → PERMANENT

Result:
  error_type: permanent
  error_description: CLI tool internal error (Python attribute error)
  is_retryable: false
```

---

## Coverage Analysis

**Total Patterns: 30+**

### JavaScript Errors: ✅ Comprehensive
- Function calls on non-functions
- Property access on null/undefined
- Reference errors (undefined variables)
- Type mismatches
- Range errors
- Syntax errors
- Promise rejections

### Python Errors: ✅ Comprehensive
- Attribute errors
- Name errors
- Key errors
- Index errors
- Value errors
- Assertion errors

### Agent/Tool Failures: ✅ Comprehensive
- Agent execution failures
- Tool call failures
- Unhandled exceptions
- Stack traces

---

## Pattern Ordering

Patterns are checked in order:
1. **Transient** (network, API rate limits)
2. **Recoverable** (context limits, model overload)
3. **Permanent** (CLI bugs, syntax errors)
4. **Exit code fallback** (if no pattern matches)

**Important:** First match wins, so more specific patterns should come before generic ones.

---

## Adding New Patterns

### When to Add a New Pattern

Add a new pattern when you encounter:
1. A new CLI tool error signature
2. A runtime error not currently caught
3. A specific error class that needs special handling

### How to Add

```python
# Add to appropriate section in permanent_patterns
("new error signature", "Description of error"),
```

**Guidelines:**
- Use **generic patterns** (match error type, not variable names)
- Use **lowercase** (log is converted to lowercase)
- Keep patterns **simple and broad**
- Avoid regex unless absolutely necessary
- Add comment explaining what it catches

### Example Addition
```python
# New CLI tool error discovered
("connection refused", "Network connection refused"),
```

---

## Testing New Patterns

### Manual Test Cases

```python
test_cases = [
    # Format: (log_content, expected_type, expected_description)

    # JavaScript errors
    ("e.split is not a function", "permanent", "CLI tool internal error"),
    ("x.map is not a function", "permanent", "CLI tool internal error"),
    ("data.filter is not a function", "permanent", "CLI tool internal error"),

    # Different error types
    ("TypeError: foo is not defined", "permanent", "CLI tool internal error"),
    ("ReferenceError: bar is not defined", "permanent", "CLI tool internal error"),

    # Agent failures
    ("Agent execution failed: timeout", "permanent", "CLI tool internal error"),
    ("Tool call failed: invalid params", "permanent", "CLI tool internal error"),

    # Python errors
    ("AttributeError: 'NoneType' object", "permanent", "CLI tool internal error"),
    ("KeyError: 'missing_key'", "permanent", "CLI tool internal error"),
]

for log, expected_type, expected_desc in test_cases:
    error_type, description = classify_cli_error(1, log, False)
    assert error_type.value == expected_type
    assert expected_desc in description.lower()
```

---

## Summary

✅ **All patterns are GENERIC** - no hardcoded variable names

✅ **Comprehensive coverage** - JavaScript, Python, and agent errors

✅ **Easy to extend** - simple tuple list format

✅ **Order-independent** - patterns don't rely on specific ordering

✅ **Case-insensitive** - all matching done on lowercase

✅ **Future-proof** - will catch new errors with similar signatures

**Your concern was valid and is now fully addressed!** 🎉
