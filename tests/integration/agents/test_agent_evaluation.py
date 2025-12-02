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
    
    @pytest.mark.asyncio
    async def test_qa_agent_basic_functionality(self):
        """Test QA agent with basic Cyoda platform questions."""
        result = await AgentEvaluator.evaluate(
            agent_module="application.agents.qa",
            eval_dataset_file_path_or_dir=str(TESTS_DIR / "qa_agent.test.json"),
        )
        
        # Verify evaluation completed
        assert result is not None
        print(f"\n✓ QA Agent Evaluation Results:\n{result}")


class TestGuidelinesAgent:
    """Unit tests for Guidelines sub-agent."""
    
    @pytest.mark.asyncio
    async def test_guidelines_agent_basic_functionality(self):
        """Test Guidelines agent with Cyoda best practices questions."""
        result = await AgentEvaluator.evaluate(
            agent_module="application.agents.guidelines",
            eval_dataset_file_path_or_dir=str(TESTS_DIR / "guidelines_agent.test.json"),
        )
        
        # Verify evaluation completed
        assert result is not None
        print(f"\n✓ Guidelines Agent Evaluation Results:\n{result}")


class TestSetupAgent:
    """Unit tests for Setup sub-agent."""
    
    @pytest.mark.asyncio
    async def test_setup_agent_basic_functionality(self):
        """Test Setup agent with Cyoda project setup questions."""
        result = await AgentEvaluator.evaluate(
            agent_module="application.agents.setup",
            eval_dataset_file_path_or_dir=str(TESTS_DIR / "setup_agent.test.json"),
        )
        
        # Verify evaluation completed
        assert result is not None
        print(f"\n✓ Setup Agent Evaluation Results:\n{result}")


class TestCoordinatorAgent:
    """Unit tests for Coordinator agent delegation."""
    
    @pytest.mark.asyncio
    async def test_coordinator_delegation(self):
        """Test coordinator's ability to delegate to appropriate sub-agents."""
        result = await AgentEvaluator.evaluate(
            agent_module="application.agents.cyoda_assistant",
            eval_dataset_file_path_or_dir=str(TESTS_DIR / "coordinator.test.json"),
        )
        
        # Verify evaluation completed
        assert result is not None
        print(f"\n✓ Coordinator Delegation Evaluation Results:\n{result}")


class TestCyodaAssistantIntegration:
    """Integration tests for multi-turn conversations."""
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversations(self):
        """Test Cyoda Assistant with multi-turn conversation scenarios."""
        result = await AgentEvaluator.evaluate(
            agent_module="application.agents.cyoda_assistant",
            eval_dataset_file_path_or_dir=str(EVALSET_FILE),
        )
        
        # Verify evaluation completed
        assert result is not None
        print(f"\n✓ Multi-Turn Integration Evaluation Results:\n{result}")


class TestAllAgents:
    """Run all agent evaluations together."""
    
    @pytest.mark.asyncio
    async def test_all_agents_comprehensive(self):
        """Run comprehensive evaluation of all agents using directory scan."""
        result = await AgentEvaluator.evaluate(
            agent_module="application.agents.cyoda_assistant",
            eval_dataset_file_path_or_dir=str(TESTS_DIR),
        )
        
        # Verify evaluation completed
        assert result is not None
        print(f"\n✓ Comprehensive Agent Evaluation Results:\n{result}")


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

