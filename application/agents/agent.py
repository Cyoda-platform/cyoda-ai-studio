"""Cyoda AI Assistant root agent for Google ADK evaluation.

This module exposes the coordinator agent for ADK eval CLI.
For production use, use create_cyoda_assistant() from cyoda_assistant module.
"""

from __future__ import annotations

import logging
import os

from application.agents.coordinator.agent import root_agent as coordinator_agent

logger = logging.getLogger(__name__)

# Check if we should mock all tools for evaluation
_MOCK_ALL_TOOLS = os.getenv("MOCK_ALL_TOOLS", "").lower() in ("true", "1", "yes")

# Import mocking callback if needed
if _MOCK_ALL_TOOLS:
    from application.agents.eval_mocking import mock_all_tools_callback

    # Apply mocking callback to coordinator agent
    coordinator_agent.before_tool_callback = mock_all_tools_callback
    logger.info("🎭 Evaluation mode: All tools will be mocked")

# Use coordinator agent as root agent for evaluation
root_agent = coordinator_agent

logger.info("✓ Root agent created for ADK evaluation")
agent = root_agent
