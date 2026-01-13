"""Wrapper for Google ADK Agent with Cyoda session persistence.

All implementation has been moved to subdirectory.
This file maintains backward compatibility by re-exporting all components.
"""

from __future__ import annotations

import logging
from typing import Any

from .wrapper import (
    _build_initial_session_state,
    _execute_agent_and_extract_response,
    _extract_metadata_from_session,
    _get_or_create_session,
    _get_session_by_technical_id,
    _load_session_state,
    _save_session_state,
    _verify_session_retrievable,
)

logger = logging.getLogger(__name__)


class CyodaAssistantWrapper:
    """Wrapper for Google ADK Agent with Cyoda session persistence.

    Manages:
    - Session state persistence to Cyoda Conversation.workflow_cache
    - ADK Runner lifecycle
    - Event processing and response extraction
    """

    def __init__(self, adk_agent: Any, entity_service: Any):
        """Initialize the wrapper.

        Args:
            adk_agent: The Google ADK LlmAgent (coordinator)
            entity_service: Cyoda entity service for persistence
        """
        from google.adk.runners import Runner

        from application.agents.shared.cyoda_response_plugin import CyodaResponsePlugin
        from application.services.cyoda_session_service import CyodaSessionService

        self.agent = adk_agent
        self.entity_service = entity_service

        # Create ADK Runner with Cyoda-backed session service for persistence
        session_service = CyodaSessionService(entity_service)

        # Create plugins for response validation and quality
        plugins = [
            CyodaResponsePlugin(
                name="cyoda_response_plugin",
                provide_tool_summary=True,
                default_message="Task completed successfully.",
            )
        ]

        self.runner = Runner(
            app_name="cyoda-assistant",
            agent=adk_agent,
            session_service=session_service,
            plugins=plugins,
        )

        logger.info(
            f"✓ CyodaAssistantWrapper initialized with agent: {adk_agent.name} and persistent sessions"
        )
        logger.info(f"✓ Plugins enabled: {[p.name for p in plugins]}")

    async def _get_session_by_technical_id(self, technical_id: str) -> Any:
        return await _get_session_by_technical_id(self.runner, technical_id)

    async def _get_or_create_session(
        self,
        session_id: str,
        user_id: str,
        session_state: dict[str, Any],
    ) -> tuple[Any, str | None]:
        return await _get_or_create_session(
            self.runner, session_id, user_id, session_state
        )

    async def _execute_agent_and_extract_response(
        self, user_id: str, session_id: str, user_message: str
    ) -> str:
        return await _execute_agent_and_extract_response(
            self.runner, user_id, session_id, user_message
        )

    def _extract_metadata_from_session(
        self, final_session_state: dict[str, Any]
    ) -> dict[str, Any]:
        return _extract_metadata_from_session(final_session_state)

    async def _build_initial_session_state(
        self,
        conversation_history: list[dict[str, str]],
        user_id: str,
        conversation_id: str | None,
    ) -> dict[str, Any]:
        return await _build_initial_session_state(
            self.entity_service, conversation_history, user_id, conversation_id
        )

    async def _load_session_state(self, conversation_id: str) -> dict[str, Any]:
        return await _load_session_state(self.entity_service, conversation_id)

    async def _save_session_state(
        self, conversation_id: str, session_state: dict[str, Any]
    ) -> None:
        await _save_session_state(self.entity_service, conversation_id, session_state)

    async def _verify_session_retrievable(
        self, session_id: str, session_technical_id: str
    ) -> None:
        await _verify_session_retrievable(self.runner, session_id, session_technical_id)

    async def process_message(
        self,
        user_message: str,
        conversation_history: list[dict[str, str]],
        conversation_id: str | None = None,
        adk_session_id: str | None = None,
        user_id: str = "guest.anonymous",
    ) -> dict[str, Any]:
        """Process a user message using the ADK agent with persistent session.

        Args:
          user_message: User's message/question
          conversation_history: Previous messages in the conversation
          conversation_id: Cyoda Conversation technical ID (for persistence)
          adk_session_id: Cyoda AdkSession technical ID (for fast retrieval)
          user_id: User ID from authentication (for deployment and other user-specific operations)

        Returns:
          Response dictionary with:
            - response: AI response text
            - agent_used: Name of the agent that processed the message
            - requires_handoff: Always False (no handoffs in this pattern)
            - metadata: Additional metadata
            - adk_session_id: Technical ID of the AdkSession (for storing in Conversation)
        """
        session_id = conversation_id or "default"

        logger.info(
            f"Processing message for session_id={session_id}, user_id={user_id}, "
            f"conversation_id={conversation_id}, adk_session_id={adk_session_id}"
        )

        # Build initial session state with conversation context
        session_state = await self._build_initial_session_state(
            conversation_history, user_id, conversation_id
        )
        logger.info(f"Session state user_id set to: {session_state.get('user_id')}")

        # Get or create session
        session_technical_id = adk_session_id  # Use provided ID if available
        if adk_session_id:
            session = await self._get_session_by_technical_id(adk_session_id)
            if session:
                logger.info(f"Session retrieved by technical_id: {adk_session_id}")

        # Get or create session using standard flow
        session, retrieved_technical_id = await self._get_or_create_session(
            session_id, user_id, session_state
        )
        if not session_technical_id:
            session_technical_id = retrieved_technical_id

        # Verify session creation
        if session and session_technical_id:
            await self._verify_session_retrievable(session_id, session_technical_id)

        # Execute agent and get response
        logger.info(f"Calling runner.run_async for session {session_id}")
        response_text = await self._execute_agent_and_extract_response(
            user_id, session_id, user_message
        )

        # Get final session state and save to Cyoda
        final_session = await self.runner.session_service.get_session(
            app_name="cyoda-assistant",
            user_id=user_id,
            session_id=session_id,
        )
        final_session_state = dict(final_session.state) if final_session else {}

        if conversation_id and final_session_state:
            await self._save_session_state(conversation_id, final_session_state)

        # Extract metadata from final session state
        metadata = self._extract_metadata_from_session(final_session_state)

        return {
            "response": response_text,
            "agent_used": self.agent.name,
            "requires_handoff": False,
            "metadata": {"session_persisted": conversation_id is not None},
            "adk_session_id": session_technical_id,
            "ui_functions": metadata["ui_functions"],
            "repository_info": metadata["repository_info"],
            "build_task_id": metadata["build_task_id"],
        }


__all__ = [
    "CyodaAssistantWrapper",
]
