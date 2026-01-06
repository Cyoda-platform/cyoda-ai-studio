# Coordinator Routing Tests

Tests for coordinator agent routing logic (10 test cases).

## Quick Commands

### Run Tests (Tools Only - Recommended)
```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/coordinator/coordinator_routing.evalset.json \
  --config_file_path application/agents/tests/evals/coordinator/tools_only_config.json
```
**Expected: 10/10 passing**

### Run Tests (With Response Matching)
```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/coordinator/coordinator_routing.evalset.json \
  --config_file_path application/agents/tests/evals/coordinator/test_config.json
```
**Expected: 8-10/10 passing**

### Generate HTML Visualization
```bash
python application/agents/tests/evals/generate_html_report.py \
  application/agents/.adk/eval_history/agents_coordinator_routing_comprehensive_*.json \
  -o application/agents/tests/evals/latest_eval_report.html
```

Then open `application/agents/tests/evals/latest_eval_report.html` in your browser.

---

## Test Coverage

| Query Type          | Expected Agent      | Tests   |
|---------------------|---------------------|---------|
| Build/generate apps | github_agent        | 5 tests |
| Explain concepts    | qa_agent            | 2 tests |
| Best practices      | qa_agent            | 1 test  |
| Deploy environment  | environment_agent   | 1 test  |
| Local setup         | setup_agent         | 1 test  |

## Files

- **`coordinator_routing.evalset.json`** - Main test suite (10 tests)
- **`case_01_only.evalset.json`** - Single test for quick iteration
- **`tools_only_config.json`** - Skip response matching (recommended)
- **`test_config.json`** - Include response matching (stricter)
