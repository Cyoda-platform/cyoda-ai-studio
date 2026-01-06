# Setup Agent Evaluations

## ⚠️ Important: Setup Agent is a Sub-Agent

The setup agent is registered as a **sub-agent** of the coordinator and has access to `transfer_to_agent` only when called through the coordinator. It cannot be tested standalone.

To test the setup agent, use the coordinator agent path:
```bash
adk eval application/agents
```

## Quick Start

Run the setup assistant evaluation tests through the coordinator:

```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/setup/evalset5fcfa8.evalset.json \
  --config_file_path application/agents/tests/evals/setup/tools_only_config.json
```

**Expected Result:** High pass rate (8-10/10 tests passing)

---

## Test Files

- **`setup_assistant.evalset.json`** - Main setup agent test suite (10 test cases)
- **`tools_only_config.json`** - Tool trajectory evaluation only (recommended)
- **`test_config.json`** - Full evaluation with response matching

---

## Test Cases Covered

| Test ID | Scenario | Expected Tools |
|---------|----------|---------------|
| case_01 | Launch setup assistant | `show_setup_options` |
| case_02 | How to run app locally | `transfer_to_agent` (→ environment_agent) |
| case_03 | How to get credentials | `transfer_to_agent` (→ environment_agent) |
| case_04 | Get env variables | `transfer_to_agent` (→ environment_agent) |
| case_05 | Check environment status | `transfer_to_agent` (→ environment_agent) |
| case_06 | Show setup menu | `show_setup_options` |

**Note:** Setup agent is a **lightweight router** that only:
1. Shows UI menu options via `show_setup_options`
2. Delegates all actual work via `transfer_to_agent`

---

## Running Tests

### 1. Tools Only (Recommended) ⭐

Evaluates only tool selection, skips response matching:

```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/setup/setup_assistant.evalset.json \
  --config_file_path application/agents/tests/evals/setup/tools_only_config.json
```

**Criteria:**
- Tool trajectory score: 0.8 minimum

---

### 2. Full Evaluation (Tools + Response)

Evaluates both tool selection and response matching:

```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/setup/setup_assistant.evalset.json \
  --config_file_path application/agents/tests/evals/setup/test_config.json
```

**Criteria:**
- Tool trajectory score: 0.8 minimum
- Response match score: 0.7 minimum

---

### 3. Detailed Output

Add `--print_detailed_results` for verbose console output:

```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/setup/setup_assistant.evalset.json \
  --config_file_path application/agents/tests/evals/setup/tools_only_config.json \
  --print_detailed_results
```

---

## Generating Reports

### 1. HTML Report (Best for Visualization) 🎨

Generate interactive HTML report:

```bash
# Run evaluation first
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/setup/setup_assistant.evalset.json \
  --config_file_path application/agents/tests/evals/setup/tools_only_config.json

# Generate HTML report from latest results
python application/agents/tests/evals/generate_html_report.py \
  application/agents/.adk/eval_history/agents_evalset5fcfa8_1767726007.9775038.evalset_result.json \
  -o application/agents/tests/evals/setup/setup_eval_report.html

# Open in browser
open application/agents/tests/evals/setup/setup_eval_report.html
```

---

### 2. Python Analysis

Detailed comparison and analysis:

```bash
python application/agents/tests/evals/analyze_eval_results.py \
  application/agents/.adk/eval_history/agents_evalset5fcfa8_1767725308.9409945.evalset_result.json
```

---

## Interactive Testing (ADK Web UI)

### Launch ADK Web UI

```bash
adk web --port 8086

adk run path/to/your/agent
```

**Access at:** http://127.0.0.1:8080

**Features:**
- Interactive chat interface
- Real-time tool execution (mocked)
- Test individual scenarios
- Debug agent responses

---

## Environment Variables

### Required
```bash
export DISABLE_MCP_TOOLSET=true  # Skip GitHub MCP (prevents timeout)
export MOCK_ALL_TOOLS=true       # Mock all tool executions
```

### Optional
```bash
export AI_MODEL="openai/gpt-5-mini"  # Override model (default from .env)
```



## Support

**Debugging Steps:**
1. Check evaluation results in `.adk/eval_history/`
2. Use `analyze_eval_results.py` for detailed comparison
3. Review setup agent prompt template
4. Verify tool definitions in `setup/tools.py`
5. Check ADK web UI for interactive testing
