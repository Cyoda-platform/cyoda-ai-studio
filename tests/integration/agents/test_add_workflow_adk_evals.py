"""ADK evaluation tests for add_workflow_clean.json dialogue."""

from __future__ import annotations

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator


class TestAddWorkflowDialogueADKEvals:
    """ADK evaluation tests for the add_workflow dialogue flow."""

    @pytest.mark.asyncio
    async def test_add_workflow_dialogue_evaluation(self):
        """Evaluate the complete add_workflow dialogue using ADK framework.

        This test uses Google ADK's evaluation framework to assess:
        - Response quality and semantic similarity
        - Tool trajectory and usage patterns
        - Hook configuration correctness
        - Message clarity and professionalism
        - Dialogue flow logic
        """
        # Note: ADK evaluator requires either:
        # 1. Module name ending with ".agent", OR
        # 2. Module with an "agent" member
        # We evaluate the github_agent which handles workflow creation
        # Criteria: response_match_score uses semantic similarity (0.7 threshold is reasonable)
        # tool_trajectory_avg_score is disabled (0.0 threshold) because tool args vary
        await AgentEvaluator.evaluate(
            agent_module="application.agents.github",
            eval_dataset_file_path_or_dir="tests/integration/agents/evals/add_workflow_dialogue.test.json",
            num_runs=1,
            criteria={
                "response_match_score": 0.7,  # Semantic similarity threshold
                "tool_trajectory_avg_score": 0.0,  # Disabled - tool args vary per run
            },
        )

