"""Cyoda AI Assistant supporting both Google ADK and OpenAI Agents SDK."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Union

from application.agents.canvas.agent import root_agent as canvas_agent
from application.agents.cyoda_data_agent.agent import root_agent as cyoda_data_agent
from application.agents.environment.agent import root_agent as environment_agent
from application.agents.environment_mcp.agent import root_agent as environment_mcp_agent
from application.agents.github.agent import root_agent as github_agent
from application.agents.guidelines.agent import root_agent as guidelines_agent
from application.agents.qa.agent import root_agent as qa_agent
from application.agents.setup.agent import root_agent as setup_agent
from application.agents.shared.cyoda_response_plugin import CyodaResponsePlugin
from application.agents.shared.prompts import create_instruction_provider
from application.entity.conversation import Conversation
from application.services.sdk_factory import get_sdk_name, is_using_openai_sdk
from common.service.service import EntityServiceError

logger = logging.getLogger(__name__)


def create_cyoda_assistant(
    google_adk_service: Any, entity_service: Any
) -> Any:
    """Create the Cyoda AI Assistant using configured SDK (Google ADK or OpenAI).

    Selects SDK based on AI_SDK environment variable:
    - "google" (default): Uses Google ADK with Coordinator/Dispatcher pattern
    - "openai": Uses OpenAI Agents SDK

    Args:
        google_adk_service: Google ADK service (not used - agents use their own client)
        entity_service: Cyoda entity service for session persistence

    Returns:
        CyodaAssistantWrapper (Google ADK) or OpenAIAssistantWrapper (OpenAI)
    """
    sdk_name = get_sdk_name()
    logger.info(f"Creating Cyoda Assistant with {sdk_name.upper()} SDK")

    if is_using_openai_sdk():
        return _create_openai_assistant(entity_service)
    else:
        return _create_google_adk_assistant(entity_service)


def _create_google_adk_assistant(entity_service: Any) -> "CyodaAssistantWrapper":
    """Create Cyoda Assistant using Google ADK SDK.

    Args:
        entity_service: Cyoda entity service for session persistence

    Returns:
        CyodaAssistantWrapper with Google ADK agent
    """
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from application.agents.shared import get_model_config
    from application.services.cyoda_session_service import CyodaSessionService
    from common.config.config import AI_MODEL

    logger.info("Initializing Google ADK Assistant")

    # Get model configuration with retry support
    model_config = get_model_config()
    logger.info(f"Using model: {AI_MODEL} with retry support")

    # Import get_user_info tool
    from application.agents.setup.tools import get_user_info

    # Create coordinator agent with sub-agents
    coordinator = LlmAgent(
        name="cyoda_assistant",
        model=model_config,
        description="Cyoda AI Assistant - helps users build and edit event-driven applications naturally",
        instruction=create_instruction_provider("coordinator"),
        tools=[get_user_info],
        sub_agents=[qa_agent, guidelines_agent, setup_agent, environment_agent, canvas_agent, github_agent, cyoda_data_agent],
    )

    logger.info("✓ Cyoda Assistant created with QA, Guidelines, Setup, Environment, Canvas, GitHub, and Cyoda Data sub-agents")
    logger.info("✓ Using Google ADK with sub_agents pattern")

    # Wrap in Cyoda-specific wrapper
    wrapper = CyodaAssistantWrapper(
        adk_agent=coordinator, entity_service=entity_service
    )
    return wrapper


def _create_openai_assistant(entity_service: Any) -> Any:
    """Create Cyoda Assistant using OpenAI Agents SDK.

    Args:
        entity_service: Cyoda entity service for session persistence

    Returns:
        OpenAIAssistantWrapper with OpenAI agent
    """
    from application.services.openai_assistant_wrapper import OpenAIAssistantWrapper
    from application.agents.openai_agents import create_openai_coordinator_agent

    logger.info("Initializing OpenAI Agents Assistant")

    # Create coordinator agent with handoffs to all sub-agents
    coordinator = create_openai_coordinator_agent()

    logger.info("✓ Cyoda Assistant created with OpenAI Agents SDK")
    logger.info("✓ Using OpenAI Agents with coordinator pattern and handoffs")

    # Wrap in Cyoda-specific wrapper
    wrapper = OpenAIAssistantWrapper(
        agent=coordinator, entity_service=entity_service
    )
    return wrapper


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

    async def _load_session_state(self, conversation_id: str) -> dict[str, Any]:
        """Load ADK session state from Cyoda Conversation.workflow_cache.

        Args:
          conversation_id: Cyoda Conversation technical ID

        Returns:
          Session state dictionary (empty if not found)
        """
        try:
            response = await self.entity_service.get_by_id(
                entity_id=conversation_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if not response:
                return {}

            conversation_data = response.data if hasattr(response, "data") else response
            conversation = Conversation(**conversation_data)

            return conversation.workflow_cache.get("adk_session_state", {})

        except Exception as e:
            logger.warning(f"Failed to load session state: {e}")
            return {}

    async def _save_session_state(
        self, conversation_id: str, session_state: dict[str, Any]
    ) -> None:
        """Save ADK session state to Cyoda Conversation.workflow_cache.
        Includes retry logic for version conflict errors.

        Args:
          conversation_id: Cyoda Conversation technical ID
          session_state: Session state dictionary to save
        """
        max_retries = 5
        base_delay = 0.1  # 100ms base delay

        for attempt in range(max_retries):
            try:
                response = await self.entity_service.get_by_id(
                    entity_id=conversation_id,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )

                if not response:
                    logger.warning(
                        f"Conversation {conversation_id} not found for state save"
                    )
                    return

                conversation_data = (
                    response.data if hasattr(response, "data") else response
                )
                conversation = Conversation(**conversation_data)

                # Update workflow_cache with session state
                conversation.workflow_cache["adk_session_state"] = session_state

                # Save back to Cyoda
                entity_data = conversation.model_dump(by_alias=False)
                await self.entity_service.update(
                    entity_id=conversation_id,
                    entity=entity_data,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )

                logger.debug(
                    f"✓ Saved session state for conversation {conversation_id}"
                )
                if attempt > 0:
                    logger.info(
                        f"Successfully saved session state after {attempt + 1} attempts"
                    )
                return  # Success

            except EntityServiceError as e:
                error_str = str(e).lower()
                is_version_conflict = (
                    "422" in error_str
                    or "500" in error_str
                    or "version mismatch" in error_str
                    or "earliestupdateaccept" in error_str
                    or "was changed by another transaction" in error_str
                    or "update operation returned no entity id" in error_str
                )

                if is_version_conflict and attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    logger.warning(
                        f"Version conflict saving session state for {conversation_id} "
                        f"(attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {delay:.3f}s... Error: {str(e)[:100]}"
                    )
                    await asyncio.sleep(delay)
                    continue  # Retry
                else:
                    # Non-retryable error or max retries reached
                    logger.error(
                        f"Failed to save session state after {attempt + 1} attempts: {e}"
                    )
                    return  # Don't crash, just log the error

            except Exception as e:
                logger.error(f"Failed to save session state: {e}")
                return  # Don't crash on unexpected errors

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

        # Load persistent session state from Cyoda
        session_state = {}
        if conversation_id:
            session_state = await self._load_session_state(conversation_id)

        # Add conversation history, user_id, and conversation_id to session state
        session_state["conversation_history"] = conversation_history
        session_state["user_id"] = user_id
        session_state["conversation_id"] = conversation_id

        logger.info(
            f"Processing message for session_id={session_id}, user_id={user_id}, "
            f"conversation_id={conversation_id}, adk_session_id={adk_session_id}"
        )
        logger.info(f"Session state user_id set to: {session_state.get('user_id')}")

        # Get or create session in the Runner's session service
        session = None
        if adk_session_id and isinstance(
            self.runner.session_service, CyodaSessionService
        ):
            # Fast path: get by technical ID (only available in CyodaSessionService)
            logger.debug(f"Getting session by technical_id: {adk_session_id}")
            adk_session_entity = (
                await self.runner.session_service.get_session_by_technical_id(
                    adk_session_id
                )
            )
            if adk_session_entity:
                session = self.runner.session_service._to_adk_session(
                    adk_session_entity
                )
                logger.info(f"Session retrieved by technical_id: {adk_session_id}")

        if not session:
            # Slow path: search by session_id or create new
            logger.debug(f"Checking if session {session_id} exists...")
            session = await self.runner.session_service.get_session(
                app_name="cyoda-assistant",
                user_id=user_id,
                session_id=session_id,
            )

        # Track the adk_session technical_id for returning to caller
        session_technical_id = adk_session_id  # Use provided ID if available

        if session:
            logger.info(f"Session {session_id} exists, updating state")
            # Update existing session state
            for key, value in session_state.items():
                session.state[key] = value
            # Get the technical_id from session state if not already provided
            if not session_technical_id:
                session_technical_id = session.state.get("__cyoda_technical_id__")
                if session_technical_id:
                    logger.info(
                        f"Retrieved technical_id from session state: {session_technical_id}"
                    )
        else:
            logger.info(f"Session {session_id} does not exist, creating new session")
            # Session doesn't exist, create it
            try:
                created_session = await self.runner.session_service.create_session(
                    app_name="cyoda-assistant",
                    user_id=user_id,
                    session_id=session_id,
                    state=session_state,
                )
                logger.info(f"Session created: {created_session.id}")

                # Get the technical_id from the created session state
                session_technical_id = created_session.state.get(
                    "__cyoda_technical_id__"
                )
                if session_technical_id:
                    logger.info(f"AdkSession technical_id: {session_technical_id}")
                else:
                    logger.warning(
                        "Created session does not have technical_id in state!"
                    )

                # Verify the session is retrievable using fast path (get_by_id)
                if session_technical_id and isinstance(
                    self.runner.session_service, CyodaSessionService
                ):
                    logger.debug(
                        f"Verifying session by technical_id: {session_technical_id}"
                    )
                    adk_session_entity = (
                        await self.runner.session_service.get_session_by_technical_id(
                            session_technical_id
                        )
                    )
                    if adk_session_entity:
                        session = self.runner.session_service._to_adk_session(
                            adk_session_entity
                        )
                        logger.info(
                            f"Session {session_id} verified as retrievable by technical_id"
                        )
                    else:
                        logger.error(
                            f"Session {session_id} was created but is not retrievable by technical_id!"
                        )
                else:
                    logger.warning(
                        "Cannot verify session - no technical_id or not using CyodaSessionService"
                    )

            except Exception as create_error:
                logger.error(
                    f"Failed to create session {session_id}: {create_error}",
                    exc_info=True,
                )
                raise ValueError(
                    f"Failed to create session: {create_error}"
                ) from create_error

        # Use Runner to execute the agent with max_llm_calls to prevent infinite loops
        logger.info(f"Calling runner.run_async for session {session_id}")
        response_text = ""
        try:
            from google.genai import types
            from google.adk.runners import RunConfig
            from application.config.streaming_config import streaming_config

            # Create run config with max_llm_calls limit
            run_config = RunConfig(max_llm_calls=streaming_config.MAX_AGENT_TURNS)

            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(parts=[types.Part(text=user_message)]),
                run_config=run_config,
            ):
                # Extract text from events
                if hasattr(event, "content") and event.content:
                    if event.content.parts:
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                response_text += part.text
            logger.info(f"Runner completed successfully for session {session_id}")
        except Exception as e:
            logger.error(f"Error in runner.run_async: {e}", exc_info=True)
            raise

        # Get final session state and save to Cyoda
        session = await self.runner.session_service.get_session(
            app_name="cyoda-assistant",
            user_id=user_id,
            session_id=session_id,
        )
        final_session_state = dict(session.state) if session else {}

        if conversation_id and final_session_state:
            await self._save_session_state(conversation_id, final_session_state)

        # Extract UI functions from session state (if any tools added them)
        ui_functions = final_session_state.get("ui_functions", [])
        if ui_functions:
            logger.info(f"Found {len(ui_functions)} UI function(s) in session state")

        # Extract repository info from session state (set by build agent tools)
        repository_info = None
        if final_session_state.get("repository_name") and final_session_state.get("repository_owner") and final_session_state.get("branch_name"):
            repository_info = {
                "repository_name": final_session_state.get("repository_name"),
                "repository_owner": final_session_state.get("repository_owner"),
                "repository_branch": final_session_state.get("branch_name"),
            }
            logger.info(f"📦 Repository info from session state: {repository_info}")

        # Extract build task ID from session state (set by build agent)
        build_task_id = final_session_state.get("build_task_id")
        if build_task_id:
            logger.info(f"📋 Build task ID from session state: {build_task_id}")

        return {
            "response": response_text,
            "agent_used": self.agent.name,
            "requires_handoff": False,
            "metadata": {"session_persisted": conversation_id is not None},
            "adk_session_id": session_technical_id,  # Return for storing in Conversation
            "ui_functions": ui_functions,  # Return UI functions to be added to conversation
            "repository_info": repository_info,  # Return repository info for conversation update
            "build_task_id": build_task_id,  # Return build task ID for conversation update
        }
