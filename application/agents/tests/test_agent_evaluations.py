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


@pytest.mark.asyncio
async def test_guidelines_agent_design_principles():
    """Test guidelines agent's ability to provide design principle guidance."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.guidelines.agent",
        eval_dataset_file_path_or_dir="application/agents/guidelines/evals/design_principles.test.json",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_guidelines_agent_testing_guidelines():
    """Test guidelines agent's ability to provide testing guidance."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.guidelines.agent",
        eval_dataset_file_path_or_dir="application/agents/guidelines/evals/testing_guidelines.test.json",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_guidelines_agent_all_evals():
    """Test guidelines agent with all evaluation files."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.guidelines.agent",
        eval_dataset_file_path_or_dir="application/agents/guidelines/evals",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_canvas_agent_workflow_creation():
    """Test canvas agent's workflow creation with immediate save."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.canvas",
        eval_dataset_file_path_or_dir="application/agents/canvas/evals/workflow_creation_immediate_save.test.json",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_canvas_agent_entity_creation():
    """Test canvas agent's entity creation with immediate save."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.canvas",
        eval_dataset_file_path_or_dir="application/agents/canvas/evals/entity_creation_immediate_save.test.json",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_canvas_agent_requirements_creation():
    """Test canvas agent's requirements creation with immediate save."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.canvas",
        eval_dataset_file_path_or_dir="application/agents/canvas/evals/requirements_creation_immediate_save.test.json",
        num_runs=2,
    )


@pytest.mark.asyncio
async def test_canvas_agent_all_evals():
    """Test canvas agent with all evaluation files."""
    await AgentEvaluator.evaluate(
        agent_module="application.agents.canvas",
        eval_dataset_file_path_or_dir="application/agents/canvas/evals",
        num_runs=2,
    )



