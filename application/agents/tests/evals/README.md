# Cyoda AI Assistant - Agent Evaluations

Google  ADK evaluation suite for testing multi-agent workflows with 90%+ pass rate.

---

## Quick Start

### Run All Evaluations (Single Command) ⭐

```bash
./application/agents/tests/evals/run_all_evals.sh
```

This will:
1. Run all evalsets (coordinator, setup, build_app)
2. Generate unified HTML report
3. Display summary in terminal
4. Auto-open report in browser

### Run Individual Test Suites

```bash
# Coordinator routing tests (10 tests)
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/environment/evals/*.evalset.json \
  --config_file_path application/agents/tests/evals/test_config.json

# Setup agent tests (6 tests)
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/setup/evals/*.evalset.json \
  --config_file_path application/agents/tests/evals/test_config.json

# GitHub/Build app tests (4 tests)
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/github/evals/*.evalset.json \
  --config_file_path application/agents/tests/evals/test_config.json
```

### Run Multiple Evalsets at Once

```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/coordinator/evals/*.evalset.json \
  application/agents/setup/evals/*.evalset.json \
  application/agents/github/evals/*.evalset.json \
  --config_file_path application/agents/tests/evals/test_config.json \
  --print_detailed_results
```

---

## Directory Structure

Evalsets are co-located with their agents for better organization:

```
application/agents/
├── coordinator/
│   └── evals/                           # Coordinator routing tests
│       ├── coordinator.evalset.json
│       └── coordinator_routing.evalset.json
├── setup/
│   └── evals/                           # Setup agent tests
│       ├── setup.evalset.json
│       └── launch_setup_agent_initial.evalset.json
├── github/
│   └── evals/                           # Build app workflow tests
│       ├── institutional_trading_platform.evalset.json
│       ├── build_app_initial_request.evalset.json
│       ├── build_app_design_functional_requirements.evalset.json
│       └── build_app_repo_setup.evalset.json
└── tests/evals/                         # Shared evaluation utilities
    ├── test_config.json                 # Shared evaluation config
    ├── run_all_evals.sh                 # Master test runner ⭐
    ├── generate_html_report.py          # HTML report generator
    ├── analyze_eval_results.py          # Detailed comparison tool
    ├── update_expected_values.py        # Update golden datasets
    └── launch_web_ui.sh                 # Interactive testing UI
```


## Environment Variables

### Required
```bash
export DISABLE_MCP_TOOLSET=true  # Skip GitHub MCP (prevents timeout)
export MOCK_ALL_TOOLS=true       # Mock all tool executions
```

### Optional
```bash
export AI_MODEL="openai/gpt-5-mini"  # Override default model
```

## Generating Reports

### 1. HTML Report (Recommended) 🎨

```bash
# Generate unified report from all test runs
python application/agents/tests/evals/generate_html_report.py \
  application/agents/.adk/eval_history/*.evalset_result.json \
  -o application/agents/tests/evals/unified_report.html

# Open in browser
open application/agents/tests/evals/unified_report.html
```

### 2. Detailed Console Output

```bash
adk eval application/agents \
  application/agents/coordinator/evals/*.evalset.json \
  --config_file_path application/agents/tests/evals/test_config.json \
  --print_detailed_results
```

### 3. Python Analysis Tool

```bash
python application/agents/tests/evals/analyze_eval_results.py \
  application/agents/.adk/eval_history/agents_coordinator_routing_*.json
```

---

## Interactive Testing

### Launch ADK Web UI

```bash
./application/agents/tests/evals/launch_web_ui.sh
```

**Access at:** http://127.0.0.1:8080

**Features:**
- Interactive chat interface
- Real-time tool execution (mocked)
- Test individual scenarios
- Save sessions as eval sets
- Debug agent responses

---

## Tool Mocking

All tool calls are intercepted and return mock responses (configured in `application/agents/eval_mocking.py`):

- `transfer_to_agent` → Actual transfer (not mocked - enables multi-agent testing)
- `generate_application` → `{"success": true}`
- `check_existing_branch_configuration` → Mock branch data
- GitHub MCP tools → Empty/mock data
- All other tools → Safe mock responses

**Benefit:** No actual execution, 100% safe, fast evaluation

---
