"""Agent processing operations for CyodaAssistantWrapper.

Handles agent execution and response extraction from ADK events.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def _execute_agent_and_extract_response(
    runner, user_id: str, session_id: str, user_message: str
) -> str:
    """Execute agent and extract text response from events.

    Args:
        runner: ADK Runner instance
        user_id: User ID for the run
        session_id: Session ID for the run
        user_message: The user's message to process

    Returns:
        Combined response text from all events
    """
    from google.genai import types
    from google.adk.runners import RunConfig
    from application.config.streaming_config import streaming_config

    response_text = ""
    try:
        # Create run config with max_llm_calls limit
        run_config = RunConfig(max_llm_calls=streaming_config.MAX_AGENT_TURNS)

        async for event in runner.run_async(
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

    return response_text
