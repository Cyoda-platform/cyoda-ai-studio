"""Wrapper for Google ADK Agent with Cyoda integration."""

import logging
from typing import Any, Dict, List, Optional

from google.adk.runners import RunConfig, Runner
from google.genai import types

from application.agents.shared.cyoda_response_plugin import CyodaResponsePlugin
from application.config.streaming_config import streaming_config
from application.services.assistant.session_manager import SessionManager
from application.services.cyoda_session_service import CyodaSessionService

logger = logging.getLogger(__name__)


class CyodaAssistantWrapper:
    """Wrapper for ADK agent handling session persistence and execution."""

    def __init__(self, adk_agent: Any, entity_service: Any):
        self.agent = adk_agent
        self.session_manager = SessionManager(entity_service)

        # Initialize Runner
        session_service = CyodaSessionService(entity_service)
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

    async def process_message(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        conversation_id: Optional[str] = None,
        adk_session_id: Optional[str] = None,
        user_id: str = "guest.anonymous",
    ) -> Dict[str, Any]:
        """Process user message."""
        session_id = conversation_id or "default"

        # Load and prepare session state
        session_state = {}
        if conversation_id:
            session_state = await self.session_manager.load_session_state(
                conversation_id
            )

        session_state.update(
            {
                "conversation_history": conversation_history,
                "user_id": user_id,
                "conversation_id": conversation_id,
            }
        )

        # Ensure session exists
        session, session_technical_id = await self._get_or_create_session(
            user_id, session_id, session_state, adk_session_id
        )

        # Execute run
        response_text = await self._execute_run(user_id, session_id, user_message)

        # Save state
        if conversation_id:
            final_session = await self.runner.session_service.get_session(
                app_name="cyoda-assistant", user_id=user_id, session_id=session_id
            )
            if final_session:
                await self.session_manager.save_session_state(
                    conversation_id, dict(final_session.state)
                )

        # Extract results
        final_state = dict(session.state) if session else {}
        return self._build_response(
            response_text,
            final_state,
            session_technical_id,
            conversation_id is not None,
        )

    async def _get_or_create_session(
        self,
        user_id: str,
        session_id: str,
        state: Dict[str, Any],
        technical_id: Optional[str],
    ) -> tuple[Any, Optional[str]]:
        """Get existing session or create new one."""
        session = None

        # Try fast path
        if technical_id and isinstance(
            self.runner.session_service, CyodaSessionService
        ):
            entity = await self.runner.session_service.get_session_by_technical_id(
                technical_id
            )
            if entity:
                session = self.runner.session_service._to_adk_session(entity)

        # Slow path / Create
        if not session:
            # Check existence first (implicitly done by create_session if logic supported,
            # but ADK separates get/create often)
            # Here assuming get_session returns existing or None?
            # ADK get_session usually returns existing.
            session = await self.runner.session_service.get_session(
                app_name="cyoda-assistant", user_id=user_id, session_id=session_id
            )

            if session:
                # Update state
                for k, v in state.items():
                    session.state[k] = v
                if not technical_id:
                    technical_id = session.state.get("__cyoda_technical_id__")
            else:
                # Create
                session = await self.runner.session_service.create_session(
                    app_name="cyoda-assistant",
                    user_id=user_id,
                    session_id=session_id,
                    state=state,
                )
                technical_id = session.state.get("__cyoda_technical_id__")

        return session, technical_id

    async def _execute_run(self, user_id: str, session_id: str, message: str) -> str:
        """Execute the agent run."""
        response_text = ""
        run_config = RunConfig(max_llm_calls=streaming_config.MAX_AGENT_TURNS)

        async for event in self.runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(parts=[types.Part(text=message)]),
            run_config=run_config,
        ):
            if hasattr(event, "content") and event.content and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_text += part.text
        return response_text

    def _build_response(
        self,
        text: str,
        state: Dict[str, Any],
        technical_id: Optional[str],
        persisted: bool,
    ) -> Dict[str, Any]:
        """Build the final response dictionary."""
        repo_info = None
        if all(
            k in state for k in ["repository_name", "repository_owner", "branch_name"]
        ):
            repo_info = {
                "repository_name": state.get("repository_name"),
                "repository_owner": state.get("repository_owner"),
                "repository_branch": state.get("branch_name"),
            }

        return {
            "response": text,
            "agent_used": self.agent.name,
            "requires_handoff": False,
            "metadata": {"session_persisted": persisted},
            "adk_session_id": technical_id,
            "ui_functions": state.get("ui_functions", []),
            "repository_info": repo_info,
            "build_task_id": state.get("build_task_id"),
        }
