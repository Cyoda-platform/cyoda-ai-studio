"""Integration tests for agent evaluations using Google ADK evaluation framework."""

from __future__ import annotations

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


@pytest.mark.asyncio
async def test_setup_agent_validate_environment():
    """Test setup agent's environment validation capability."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.setup.agent",
        eval_dataset_file_path_or_dir="application/agents/setup/evals/validate_environment.test.json",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_setup_agent_check_project_structure():
    """Test setup agent's project structure validation capability."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.setup.agent",
        eval_dataset_file_path_or_dir="application/agents/setup/evals/check_project_structure.test.json",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_setup_agent_all_evals():
    """Test setup agent with all evaluation files."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.setup.agent",
        eval_dataset_file_path_or_dir="application/agents/setup/evals",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_qa_agent_cyoda_concepts():
    """Test QA agent's ability to explain Cyoda concepts."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.qa.agent",
        eval_dataset_file_path_or_dir="application/agents/qa/evals/cyoda_concepts.test.json",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_qa_agent_cyoda_patterns():
    """Test QA agent's ability to explain Cyoda design patterns."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.qa.agent",
        eval_dataset_file_path_or_dir="application/agents/qa/evals/cyoda_patterns.test.json",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_qa_agent_all_evals():
    """Test QA agent with all evaluation files."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.qa.agent",
        eval_dataset_file_path_or_dir="application/agents/qa/evals",
        num_runs=2,
    )









