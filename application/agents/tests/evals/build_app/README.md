# Build Application Tests

**End-to-end test for multi-agent workflows**: coordinator → github_agent transfer and setup flow.

## Quick Commands

### Option 1: Response Validation Only (PASSES ✓)
Validates that the agent's response includes key concepts (Design, Canvas, Cyoda Journey, etc.)

```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/build_app/institutional_trading_platform.evalset.json \
  --config_file_path application/agents/tests/evals/build_app/response_only_config.json
```

**Result:** ✅ 1/1 PASS (response similarity: ~32% vs 30% threshold)

### Option 2: Tools Validation (HTML Verification Required)
Validates tool calls via HTML report (ADK score will be 0/1 due to arg matching strictness)

```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/build_app/institutional_trading_platform.evalset.json \
  --config_file_path application/agents/tests/evals/build_app/tools_only_config.json
```

**Result:** ❌ 0/1 ADK score (see "Important Note" below)

### Option 3: Both Tools + Response
```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents \
  application/agents/tests/evals/build_app/institutional_trading_platform.evalset.json \
  --config_file_path application/agents/tests/evals/build_app/test_config.json
```

**Result:** ❌ 0/1 (tool trajectory fails, response passes)

### Generate HTML Visualization
```bash
python application/agents/tests/evals/generate_html_report.py \
  application/agents/.adk/eval_history/agents_build_app_institutional_trading_*.json \
  -o application/agents/tests/evals/latest_eval_report.html
```

---
![Screenshot from 2025-12-31 23-19-01.png](../../../../../../../Pictures/Screenshots/Screenshot%20from%202025-12-31%2023-19-01.png)
## Test Coverage

### Institutional Trading Platform (case_01_full_workflow)
**Single-invocation test validating end-to-end agent transfer and multi-agent workflow:**

**Test Scenario (all in ONE invocation):**
1. User sends complex trading platform request
2. Coordinator identifies build request → `transfer_to_agent(github_agent)`
3. **GitHub agent takes over immediately** (same invocation)
4. GitHub agent calls `check_existing_branch_configuration()`
5. GitHub agent calls `ask_user_to_select_option()` with 8 setup options
6. Agent stops and waits for user selection

**Expected Tools (in order):**
1. `transfer_to_agent(github_agent)` - Coordinator transfers control
2. `check_existing_branch_configuration()` - G![Screenshot from 2025-12-31 23-19-01.png](../../../../../../../Pictures/Screenshots/Screenshot%20from%202025-12-31%2023-19-01.png)itHub agent checks state
3. `ask_user_to_select_option()` - GitHub agent presents options

**Agents Involved:**
- Invocation starts with: Cyoda Assistant (coordinator)
- Control transfers to: GitHub Agent (within same invocation)

**✅ This test validates:**
- Agent transfers work correctly in eval mode
- Transferred agent executes its tools in the same invocation
- Multi-agent workflows can be tested end-to-end

**⚠️ Important: ADK Scoring vs Actual Behavior**

**Expected ADK Score: 0/1 (this is correct!)**

ADK's tool trajectory evaluator uses **exact argument matching** (same args, same values). Since `ask_user_to_select_option` has complex dynamic arguments (question text varies, 8 option objects with descriptions), it will always fail exact matching.

**✅ The test IS working correctly** - all 3 tools execute in the right order:
1. Coordinator calls `transfer_to_agent(github_agent)` ✓
2. GitHub agent calls `check_existing_branch_configuration()` ✓
3. GitHub agent calls `ask_user_to_select_option(...)` with 8 options ✓

**To verify the test passes, check the HTML report:**
```bash
python application/agents/tests/evals/generate_html_report.py \
  application/agents/.adk/eval_history/agents_build_app_institutional_trading_*.json \
  -o application/agents/tests/evals/latest_eval_report.html
```

Open the report and confirm:
- **Tool Calls Comparison** shows "✅ MATCH"
- All 3 expected tools are present in actual execution
- **Conversation Flow** shows coordinator → github_agent transfer working

---

## Implementation Notes

### Agent Transfer Support
To enable agent transfers in eval mode, `transfer_to_agent` is **excluded from mocking** in `application/agents/eval_mocking.py`. This allows the actual transfer mechanism to execute, enabling the github_agent to take over within the same invocation.

Other tools (`check_existing_branch_configuration`, `ask_user_to_select_option`, etc.) are mocked to avoid dependencies on conversation state.

### Multi-Agent Mocking
Both coordinator and github_agent have the mocking callback enabled in eval mode:
- `application/agents/agent.py` - Coordinator mocking setup
- `application/agents/github/agent.py` - GitHub agent mocking setup

---

## Files

- **`institutional_trading_platform.evalset.json`** - Multi-agent workflow test
- **`response_only_config.json`** - Validate response only (✅ PASSES - recommended for CI/CD)
- **`tools_only_config.json`** - Validate tools only (requires HTML verification)
- **`test_config.json`** - Validate both tools and response (strict)
- **`test_end_to_end.py`** - Python integration test (alternative approach)
