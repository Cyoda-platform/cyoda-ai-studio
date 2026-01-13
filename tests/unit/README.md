# Unit Tests Guide

This directory contains unit tests for the Cyoda AI Studio project. This guide explains how to run tests and check test coverage.

## Prerequisites

Install development dependencies:

```bash
pip install -e ".[dev]"
```

This installs pytest, pytest-cov, pytest-asyncio, and other testing tools defined in `pyproject.toml`.

## Running Tests

### Run all unit tests

```bash
pytest tests/unit
```

### Run tests for a specific module

```bash
# Run environment tools tests
pytest tests/unit/agents/test_environment_tools.py

# Run with verbose output
pytest tests/unit/agents/test_environment_tools.py -v

# Run specific test class
pytest tests/unit/agents/test_environment_tools.py::TestCheckEnvironmentExists

# Run specific test method
pytest tests/unit/agents/test_environment_tools.py::TestCheckEnvironmentExists::test_check_environment_exists_success
```

### Run tests with markers

```bash
# Run only unit tests (if marked)
pytest -m unit

# Skip slow tests
pytest -m "not slow"
```

## Checking Test Coverage

### Basic Coverage Report

Run tests with coverage for a specific file:

```bash
pytest tests/unit/agents/test_environment_tools.py \
  --cov=application.agents.environment.tools \
  --cov-report=term-missing
```

**Note:** Use dot notation (`.`) for the module path, not slashes (`/`).

This shows:
- Overall coverage percentage
- Line numbers that are NOT covered (missing)

### Coverage for Multiple Files

```bash
# Coverage for all agent tools
pytest tests/unit/agents/ \
  --cov=application/agents \
  --cov-report=term-missing

# Coverage for entire application
pytest tests/unit/ \
  --cov=application \
  --cov-report=term-missing
```

### HTML Coverage Report

Generate an interactive HTML report to explore coverage visually:

```bash
pytest tests/unit/agents/test_environment_tools.py \
  --cov=application.agents.environment.tools \
  --cov-report=html

# Open the report in your browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

The HTML report shows:
- File-by-file coverage breakdown
- Line-by-line highlighting of covered/uncovered code
- Branch coverage information

### Coverage Thresholds

To fail tests if coverage falls below a certain percentage:

```bash
pytest tests/unit/agents/test_environment_tools.py \
  --cov=application.agents.environment.tools \
  --cov-report=term-missing \
  --cov-fail-under=95
```

### Multiple Report Formats

Generate both terminal and HTML reports simultaneously:

```bash
pytest tests/unit/agents/test_environment_tools.py \
  --cov=application.agents.environment.tools \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml  # For CI/CD integration
```

## Coverage Configuration

Coverage settings are defined in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["cyoda_mcp", "common", "entity", "service", "workflow", "routes"]
omit = [
    "*/tests/*",
    "*/test_*",
    "proto/*",
    "*/__pycache__/*",
    "*/.*",
]
```

Lines excluded from coverage reporting:

- `pragma: no cover` comments
- `if __name__ == "__main__":` blocks
- Abstract methods
- Debug-only code

## Example: Environment Tools Coverage

The environment tools (`application/agents/environment/tools.py`) are tested by `test_environment_tools.py`.

### Check current coverage:

```bash
pytest tests/unit/agents/test_environment_tools.py \
  --cov=application.agents.environment.tools \
  --cov-report=term-missing
```

Example output (as of latest run):
```
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
application/agents/environment/tools.py    1243    588    53%   120-122, 167, 190-211, ...
```

**Current coverage: 53%** - There is significant room for improvement by adding tests for:
- Deployment functions (`deploy_cyoda_environment`, `deploy_user_application`)
- Error handling paths
- Additional edge cases

### Analyze uncovered lines:

```bash
# Generate HTML report for detailed analysis
pytest tests/unit/agents/test_environment_tools.py \
  --cov=application.agents.environment.tools \
  --cov-report=html

# Open htmlcov/index.html and click on tools.py
# Red lines = not covered
# Green lines = covered
```

## Writing Tests

### Test Structure

Tests are organized by the module they test:

```
tests/unit/
├── agents/
│   ├── test_environment_tools.py  # Tests for application/agents/environment/tools.py
│   ├── test_cyoda_assistant.py    # Tests for application/agents/cyoda_assistant.py
│   └── github/
│       └── test_*.py
├── routes/
│   └── test_*.py
└── services/
    └── test_*.py
```

### Test Class Naming

- Test class: `TestFunctionName` or `TestClassName`
- Test method: `test_specific_behavior`

Example:
```python
class TestCheckEnvironmentExists:
    """Test check_environment_exists function."""

    @pytest.mark.asyncio
    async def test_check_environment_exists_success(self, mock_tool_context):
        """Test successful environment existence check."""
        # Arrange
        mock_response = MagicMock()
        mock_response.json.return_value = {"exists": True}

        # Act
        result = await tools.check_environment_exists(mock_tool_context, "dev")

        # Assert
        assert "exists" in result
```

### Fixtures

Common fixtures are defined in `conftest.py` or within test files:

```python
@pytest.fixture
def mock_tool_context():
    """Create mock tool context."""
    context = MagicMock()
    context.state = {
        "user_id": "test-user",
        "conversation_id": "test-conversation-123",
        "auth_token": "test-auth-token"
    }
    return context
```

### Async Tests

Use `@pytest.mark.asyncio` for async functions:

```python
@pytest.mark.asyncio
async def test_async_function(self, mock_context):
    result = await some_async_function(mock_context)
    assert result is not None
```

### Mocking

Use `unittest.mock` for mocking:

```python
from unittest.mock import AsyncMock, MagicMock, patch

# Mock async functions
with patch("application.agents.environment.tools._get_cloud_manager_auth_token",
           new_callable=AsyncMock) as mock_auth:
    mock_auth.return_value = "test-token"
    result = await function_under_test()

# Mock environment variables
with patch.dict(os.environ, {"VAR_NAME": "value"}):
    result = function_that_uses_env_vars()
```

## Coverage Best Practices

1. **Aim for 95%+ coverage** for critical business logic
2. **Test edge cases**: guest users, missing parameters, errors
3. **Test success and failure paths** for each function
4. **Use descriptive test names** that explain what is being tested
5. **Mock external dependencies** (HTTP clients, databases, file I/O)
6. **Test error handling** with `pytest.raises`

```python
@pytest.mark.asyncio
async def test_function_with_missing_param(self, mock_context):
    """Test function fails with missing required parameter."""
    result = await function(mock_context, required_param=None)
    assert "ERROR" in result
    assert "required" in result.lower()
```

## Continuous Integration

In CI/CD pipelines, you can enforce coverage requirements:

```yaml
# .github/workflows/test.yml
- name: Run tests with coverage
  run: |
    pytest tests/unit \
      --cov=application \
      --cov-report=term-missing \
      --cov-report=xml \
      --cov-fail-under=90

- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Troubleshooting

### Tests are slow
```bash
# Profile test execution time
pytest tests/unit --durations=10

# Skip slow tests
pytest tests/unit -m "not slow"
```

### Import errors
```bash
# Ensure package is installed in development mode
pip install -e ".[dev]"

# Check PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Coverage not tracking files
```bash
# Ensure source paths are correct in pyproject.toml
# Check [tool.coverage.run] source setting
# Verify files are not in omit list
```

### Mock not working
```bash
# Ensure you're patching the right import path
# Patch where it's used, not where it's defined
# Example: If tools.py does "import httpx", patch "httpx.AsyncClient"
#          If tools.py does "from httpx import AsyncClient", patch "application.agents.environment.tools.AsyncClient"
```

## Additional Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Python unittest.mock guide](https://docs.python.org/3/library/unittest.mock.html)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)

## Quick Reference

```bash
# Run all unit tests
pytest tests/unit

# Run with coverage for all application code
pytest tests/unit --cov=application --cov-report=term-missing

# Run specific test file with verbose output
pytest tests/unit/agents/test_environment_tools.py -v

# Run specific module with coverage (use dot notation!)
pytest tests/unit/agents/test_environment_tools.py \
  --cov=application.agents.environment.tools \
  --cov-report=term-missing

# Generate HTML coverage report
pytest tests/unit --cov=application --cov-report=html

# Run and fail if coverage < 95%
pytest tests/unit --cov=application --cov-fail-under=95

# Watch mode (requires pytest-watch)
ptw tests/unit -- --cov=application
```
