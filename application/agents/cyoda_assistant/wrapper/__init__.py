"""Wrapper subdirectory re-exports.

All implementation has been moved to focused modules.
This file maintains backward compatibility by re-exporting all components.
"""

from __future__ import annotations

import logging
from typing import Any

from .session_management import (
    _get_session_by_technical_id,
    _get_or_create_session,
    _load_session_state,
    _save_session_state,
    _verify_session_retrievable,
    _build_initial_session_state,
)
from .agent_processing import (
    _execute_agent_and_extract_response,
)
from .metadata_extraction import (
    _extract_metadata_from_session,
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
        from application.services.cyoda_session_service import CyodaSessionService
        from application.agents.shared.cyoda_response_plugin import CyodaResponsePlugin

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
        user_id: str,
        conversation_id: str | None = None,
        session_id: str | None = None,
        session_technical_id: str | None = None,
    ) -> dict[str, Any]:
        """Process a user message with session state management.

        Args:
            user_message: The user's message
            conversation_history: List of prior messages in conversation
            user_id: The user identifier
            conversation_id: Optional Cyoda conversation identifier
            session_id: Optional session identifier
            session_technical_id: Optional technical session identifier

        Returns:
            Dict containing response, metadata, and session information
        """
        try:
            # Build initial session state
            session_state = await self._build_initial_session_state(
                conversation_history, user_id, conversation_id
            )

            # Get or create session
            session, technical_id = await self._get_or_create_session(
                session_id or str(conversation_id) if conversation_id else "default",
                user_id,
                session_state,
            )

            # Execute agent
            response = await self._execute_agent_and_extract_response(
                user_id, session.id, user_message
            )

            # Save session state
            if conversation_id:
                await self._save_session_state(conversation_id, session_state)

            # Verify session persistence
            if technical_id:
                await self._verify_session_retrievable(session.id, technical_id)

            # Extract metadata
            metadata = self._extract_metadata_from_session(session_state)

            return {
                "response": response,
                "metadata": metadata,
                "session_id": session.id,
                "technical_id": technical_id,
            }

        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            raise


__all__ = [
    # Session management
    "_get_session_by_technical_id",
    "_get_or_create_session",
    "_load_session_state",
    "_save_session_state",
    "_verify_session_retrievable",
    "_build_initial_session_state",
    # Agent processing
    "_execute_agent_and_extract_response",
    # Metadata extraction
    "_extract_metadata_from_session",
    # Main class
    "CyodaAssistantWrapper",
]
