"""Cyoda Assistant Agent - Entry point that uses the coordinator."""

from __future__ import annotations

import logging

from application.agents.coordinator.agent import root_agent as coordinator_agent

logger = logging.getLogger(__name__)

# Use the coordinator agent as the root agent for cyoda_assistant
root_agent = coordinator_agent

logger.info("✓ Cyoda Assistant loaded (using Coordinator agent)")

agent = root_agent
