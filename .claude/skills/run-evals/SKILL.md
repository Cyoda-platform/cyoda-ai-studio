---
name: run-evals
description: Use this skill when running ADK agent evaluations or creating new evaluation tests.
tags: [testing, evals, adk, quality-assurance]
---

# Run Evals Skill

## Purpose
Guide for running Google ADK agent evaluations and creating evaluation tests.

## When to Use This Skill
- Running agent evaluations
- Creating new evaluation tests
- Debugging failing evals
- Generating unified eval reports
- Setting up CI/CD evaluation pipelines

## Quick Start

### Run All Evaluations

```bash
# From project root
make test-eval

# Or manually
cd application/agents/tests/evals
bash run_all_evals.sh
```

### Run Specific Agent Evals

```bash
cd application/agents/tests/evals/{agent_name}
python -m google.adk.evals.run test_{agent_name}.py
```

### View Reports

```bash
# Open unified HTML report
make open-reports

# Or manually
xdg-open reports/eval/unified_report.html
```

## Creating Evaluation Tests

### 1. Basic Evaluation

```python
import pytest
from google.adk.evals import create_eval

@create_eval("test_agent_basic_response")
async def test_basic_response():
    """Test that agent responds to basic queries."""
    from application.agents.my_agent.agent import my_agent

    response = await my_agent.run("What is your purpose?")

    assert response is not None
    assert len(response) > 0
    assert "purpose" in response.lower()
```

### 2. Tool Usage Evaluation

```python
@create_eval("test_agent_uses_tool")
async def test_tool_usage():
    """Test that agent correctly uses provided tools."""
    from application.agents.my_agent.agent import my_agent

    # Query that should trigger tool usage
    response = await my_agent.run(
        "Search for entities with status=active"
    )

    # Assertions
    assert "entities" in response.lower() or "found" in response.lower()
    # Check that tool was called (logged or tracked)
```

### 3. Structured Output Evaluation

```python
from pydantic import BaseModel

class ExpectedOutput(BaseModel):
    status: str
    count: int
    items: list[str]

@create_eval("test_structured_output")
async def test_structured_output():
    """Test that agent returns properly structured data."""
    from application.agents.my_agent.agent import my_agent

    response = await my_agent.run("List active items")

    # Parse response as Pydantic model
    try:
        output = ExpectedOutput.parse_raw(response)
        assert output.status == "success"
        assert output.count > 0
    except Exception as e:
        pytest.fail(f"Invalid structure: {e}")
```

### 4. Multi-Turn Conversation Evaluation

```python
@create_eval("test_multi_turn_conversation")
async def test_conversation():
    """Test agent maintains context across turns."""
    from application.agents.my_agent.agent import my_agent

    # Turn 1
    response1 = await my_agent.run("Create an entity named 'TestEntity'")
    assert "created" in response1.lower() or "success" in response1.lower()

    # Turn 2 (should reference previous context)
    response2 = await my_agent.run("Now update it with status=active")
    assert "updated" in response2.lower() or "success" in response2.lower()
```

### 5. Error Handling Evaluation

```python
@create_eval("test_error_handling")
async def test_invalid_input_handling():
    """Test that agent handles invalid inputs gracefully."""
    from application.agents.my_agent.agent import my_agent

    # Invalid query
    response = await my_agent.run("")

    # Should not crash, should provide helpful message
    assert response is not None
    assert len(response) > 0
    # Should indicate issue with input
    assert "invalid" in response.lower() or "provide" in response.lower()
```

## Evaluation Best Practices

### 1. Use Descriptive Names

```python
# ✅ Good: Describes what is tested
@create_eval("test_coordinator_delegates_to_cyoda_agent")

# ❌ Bad: Vague name
@create_eval("test_1")
```

### 2. Test One Thing Per Eval

```python
# ✅ Good: Focused test
@create_eval("test_agent_creates_entity")
async def test_create():
    response = await agent.run("Create entity")
    assert "created" in response.lower()

# ❌ Bad: Tests multiple unrelated things
@create_eval("test_agent_everything")
async def test_all():
    # Tests create, read, update, delete all in one
    # Hard to debug when it fails
```

### 3. Use Mocking for External Dependencies

```python
from application.agents.eval_mocking import mock_cyoda_service

@create_eval("test_with_mocked_cyoda")
async def test_mocked():
    """Test agent behavior with mocked Cyoda service."""
    with mock_cyoda_service():
        response = await agent.run("Get entity 123")
        assert response is not None
```

### 4. Add Assertions with Messages

```python
# ✅ Good: Clear failure message
assert len(entities) > 0, f"Expected entities, got {len(entities)}"

# ❌ Bad: Generic failure
assert len(entities) > 0
```

### 5. Clean Up After Tests

```python
@create_eval("test_with_cleanup")
async def test_cleanup():
    """Test with proper cleanup."""
    entity_id = None

    try:
        # Create test data
        response = await agent.run("Create test entity")
        entity_id = extract_id_from_response(response)

        # Run test
        assert entity_id is not None

    finally:
        # Clean up
        if entity_id:
            await cleanup_entity(entity_id)
```

## Eval Report Structure

### Unified Report Includes

1. **Summary Statistics**
   - Total evals run
   - Pass/fail counts
   - Execution time
   - Success rate

2. **Per-Agent Results**
   - Agent name
   - Eval count
   - Pass/fail breakdown
   - Individual test results

3. **Failure Details**
   - Failed test name
   - Error message
   - Stack trace
   - Input query

### Interpreting Results

```bash
# Example output
=== Eval Report ===
Agent: cyoda_assistant
  Total: 15
  Passed: 13
  Failed: 2
  Success Rate: 86.67%

Failed Tests:
  1. test_complex_workflow_export
     Error: Timeout after 30s
  2. test_edge_case_handling
     Error: AssertionError: Expected 'success' in response
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/evals.yml
name: Run ADK Evaluations

on: [push, pull_request]

jobs:
  evals:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"

      - name: Run evaluations
        run: make test-eval
        env:
          CYODA_CLIENT_ID: ${{ secrets.CYODA_CLIENT_ID }}
          CYODA_CLIENT_SECRET: ${{ secrets.CYODA_CLIENT_SECRET }}
          CYODA_HOST: ${{ secrets.CYODA_HOST }}

      - name: Upload eval report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: eval-report
          path: reports/eval/unified_report.html
```

## Debugging Failing Evals

### 1. Check Mock Data

```python
# Verify mock data is set up correctly
from application.agents.eval_mocking import get_mock_data

mock_data = get_mock_data()
print(f"Mock entities: {mock_data['entities']}")
```

### 2. Enable Verbose Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)

@create_eval("test_with_logging")
async def test_debug():
    logger = logging.getLogger(__name__)
    logger.debug("Starting test...")

    response = await agent.run("Query")
    logger.debug(f"Response: {response}")

    assert response is not None
```

### 3. Run Single Eval in Isolation

```bash
# Run specific test file
python -m google.adk.evals.run test_my_agent.py

# Run specific test function
python -m google.adk.evals.run test_my_agent.py::test_specific_function
```

### 4. Check Environment Variables

```python
import os

@create_eval("test_env_check")
async def test_env():
    """Verify environment is configured correctly."""
    assert os.getenv("CYODA_CLIENT_ID"), "CYODA_CLIENT_ID not set"
    assert os.getenv("CYODA_CLIENT_SECRET"), "CYODA_CLIENT_SECRET not set"
    assert os.getenv("CYODA_HOST"), "CYODA_HOST not set"
```

## Eval Validation Script

The project includes a validation script:

```bash
# Validate all evals before running
python application/agents/validate_evals.py

# Shows:
# - Evals with missing docstrings
# - Evals without assertions
# - Duplicate eval names
# - Performance issues
```

## Performance Benchmarking

```python
import time

@create_eval("test_performance")
async def test_response_time():
    """Test that agent responds within acceptable time."""
    start = time.time()

    response = await agent.run("Simple query")

    elapsed = time.time() - start

    assert response is not None
    assert elapsed < 5.0, f"Took {elapsed:.2f}s, expected < 5s"
```

## Checklist

- [ ] Eval file created in `application/agents/tests/evals/{agent}/`
- [ ] Test functions use `@create_eval` decorator
- [ ] Descriptive test names used
- [ ] Docstrings added to each eval
- [ ] Assertions include error messages
- [ ] Mocking configured for external services
- [ ] Cleanup logic added (if needed)
- [ ] Environment variables checked
- [ ] Tests pass locally (`make test-eval`)
- [ ] Unified report generated and reviewed

## Reference Files

- `application/agents/tests/evals/` - Eval test directory
- `application/agents/tests/evals/run_all_evals.sh` - Run all script
- `application/agents/eval_mocking.py` - Mock utilities
- `application/agents/validate_evals.py` - Validation script
- `Makefile` - Build commands (see `make test-eval`)

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'google.adk.evals'` | ADK not installed | `pip install google-adk` |
| `Eval timeout` | Query takes too long | Increase timeout or optimize agent |
| `No evals found` | Missing `@create_eval` decorator | Add decorator to test functions |
| `Mock data not found` | Mocking not configured | Check `eval_mocking.py` setup |

---

**Quick Command:** `make test-eval && make open-reports`
