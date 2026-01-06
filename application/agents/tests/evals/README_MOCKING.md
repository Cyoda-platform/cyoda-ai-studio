# Running Evaluations with Tool Mocking

## Overview

This guide explains how to run ADK evaluations with comprehensive tool mocking. Mocking prevents actual tool execution and allows testing agent behavior (tool selection, sequencing, responses) without side effects.

## Quick Start

Run evaluations with full mocking:

```bash
export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
adk eval application/agents application/agents/tests/evals/your-eval-file.evalset.json
```

## Environment Variables

### `DISABLE_MCP_TOOLSET=true`
- Disables GitHub MCP (Model Context Protocol) toolset initialization
- Prevents timeout issues during evaluation
- Uses custom tools only

### `MOCK_ALL_TOOLS=true`
- Enables comprehensive tool mocking via `before_tool_callback`
- All tool calls are intercepted and return mock responses
- No actual tool execution (no file writes, API calls, etc.)

## How It Works

### 1. Tool Mocking Implementation
Located in: `application/agents/eval_mocking.py`

The `mock_all_tools_callback()` function:
- Intercepts ALL tool calls before execution
- Logs the tool name and arguments (for tracking)
- Returns predefined mock responses
- Prevents actual tool execution

### 2. Mock Response Definitions
Mock responses are defined per tool in `eval_mocking.py`:

```python
mock_responses = {
    "transfer_to_agent": "Successfully transferred to {agent_name}",
    "clone_repository": {
        "success": True,
        "branch": "test-branch-uuid-12345",
        "path": "/tmp/mocked/repo/path"
    },
    "generate_application": {
        "success": True,
        "task_id": "build-task-12345",
        "status": "running"
    },
    # ... more tools
}
```

### 3. Integration
The root agent (`application/agents/agent.py`) checks for `MOCK_ALL_TOOLS` and applies the callback:

```python
if os.getenv("MOCK_ALL_TOOLS", "").lower() in ("true", "1", "yes"):
    from application.agents.eval_mocking import mock_all_tools_callback
    _before_tool_callback = mock_all_tools_callback
```

## Evaluation Results

Results are saved to: `application/agents/.adk/eval_history/`

Each evaluation produces:
- Test pass/fail counts
- Tool trajectory scoring
- Response match scoring
- Detailed execution logs

## Adding New Mock Responses

To add mocking for a new tool:

1. Open `application/agents/eval_mocking.py`
2. Add entry to `mock_responses` dict:

```python
"your_tool_name": {
    "success": True,
    "data": "your mock data"
}
```

3. Tools not in the dict get a generic success response

## Logging

Mock tool calls are logged with:
- `🎯 [EVAL MOCK] Tool called: {tool_name}` - Tool invocation
- `✅ [EVAL MOCK] Returning mock response` - Mock response returned
- `⚠️ [EVAL MOCK] No specific mock for tool` - Using generic mock

## Example Evaluation Run

```bash
$ export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \
  adk eval application/agents application/agents/tests/evals/example_dialogue_1.evalset.json

# Output:
# 🎭 Evaluation mode: All tools will be mocked
# 🎯 [EVAL MOCK] Tool called: transfer_to_agent with args: {'agent_name': 'github_agent'}
# ✅ [EVAL MOCK] Returning mock response for transfer_to_agent
# ...
# Eval Run Summary:
#   Tests passed: 1
#   Tests failed: 4
```

## Benefits of Mocking

1. **Fast execution** - No actual I/O or network calls
2. **No side effects** - No file writes, database changes, or API calls
3. **Reproducible** - Same mock responses every time
4. **Isolated testing** - Tests agent logic, not tool implementation
5. **Safe** - Can't accidentally modify production resources

## Troubleshooting

### MCP Timeout Errors
**Solution**: Use `DISABLE_MCP_TOOLSET=true`

### Tools Actually Executing
**Solution**: Verify `MOCK_ALL_TOOLS=true` is set and check logs for "🎭 Evaluation mode" message

### Missing Mock Response
**Solution**: Add tool to `mock_responses` dict in `eval_mocking.py` or use the generic response

## Files

- `application/agents/eval_mocking.py` - Mock callback implementation
- `application/agents/agent.py` - Root agent with mocking support
- `application/agents/github/agent.py` - GitHub agent with MCP disable support
- `application/agents/tests/evals/` - Evaluation files


Quickstart

export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && adk eval application/agents application/agents/tests/evals/coordinator_routing.evalset.json
--config_file_path application/agents/tests/evals/tools_only_config.json