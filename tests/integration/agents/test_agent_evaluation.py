"""
Agent Evaluation Tests using Google ADK Evaluation Framework

Tests individual agents and the coordinator using .test.json and .evalset.json files.
Follows patterns from: https://google.github.io/adk-docs/evaluate/

Run with:
    pytest tests/integration/agents/test_agent_evaluation.py -v
    
Or use ADK CLI:
    adk eval --eval-dataset tests/integration/agents/evals/
    
Or use ADK web UI:
    adk web
"""

import os
from pathlib import Path

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


# Base path for test files
TESTS_DIR = Path(__file__).parent / "evals"
EVALSET_FILE = Path(__file__).parent / "cyoda_assistant.evalset.json"


class TestQAAgent:
    """Unit tests for QA sub-agent."""
    
    pass

class TestGuidelinesAgent:
    """Unit tests for Guidelines sub-agent."""
    
    pass


class TestSetupAgent:
    """Unit tests for Setup sub-agent."""
    
    pass


class TestCoordinatorAgent:
    """Unit tests for Coordinator agent delegation."""
    pass


class TestCyodaAssistantIntegration:
    """Integration tests for multi-turn conversations."""
    
    pass


class TestAllAgents:
    """Run all agent evaluations together."""
    
    pass


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )


if __name__ == "__main__":
    # Allow running directly with: python test_agent_evaluation.py
    pytest.main([__file__, "-v", "-s"])

