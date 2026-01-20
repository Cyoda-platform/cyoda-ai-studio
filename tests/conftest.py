"""Pytest configuration for tests.

Sets up Python path and fixtures for all tests.
"""

import sys
from pathlib import Path

import pytest

# Add project root to Python path so imports work correctly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def reset_circuit_breaker_before_test():
    """Reset circuit breaker state before each test to prevent OPEN state from affecting tests."""
    from application.agents.github.tool_definitions.code_generation.helpers import (
        reset_circuit_breaker,
    )

    reset_circuit_breaker()
    yield
    # Reset again after test to clean up
    reset_circuit_breaker()
