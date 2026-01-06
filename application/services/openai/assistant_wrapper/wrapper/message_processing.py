"""Message processing operations for OpenAI Assistant."""

import importlib
import logging
from typing import Any

from application.config.streaming_config import streaming_config

logger = logging.getLogger(__name__)

# Import OpenAI agents module directly to avoid namespace collision with local 'agents' package
_openai_agents = importlib.import_module("agents")
Agent = _openai_agents.Agent
Runner = _openai_agents.Runner


def extract_hooks_from_result(result: Any) -> list[dict[str, Any]]:
    """Extract UI hooks from the agent result.

    Hooks are stored in the result's context by tools during execution.
    This method looks for hooks that were added to the context.

    Args:
        result: The RunResult or RunResultStreaming from the agent

    Returns:
        List of hook dictionaries, or empty list if none found
    """
    hooks = []
    try:
        # OpenAI SDK stores context in context_wrapper.context
        if hasattr(result, "context_wrapper") and result.context_wrapper:
            context_wrapper = result.context_wrapper
            context = context_wrapper.context

            # Context can be any object, check if it has state or is a dict
            if context:
                if isinstance(context, dict):
                    # Check for last_tool_hook (single hook)
                    if "last_tool_hook" in context:
                        hook = context["last_tool_hook"]
                        if hook:
                            hooks.append(hook)
                            logger.info(
                                f"Extracted hook from context: {hook.get('type', 'unknown')}"
                            )

                    # Check for ui_functions (list of hooks)
                    if "ui_functions" in context:
                        ui_functions = context["ui_functions"]
                        if isinstance(ui_functions, list):
                            hooks.extend(ui_functions)
                            logger.info(
                                f"Extracted {len(ui_functions)} UI functions from context"
                            )
                elif hasattr(context, "state") and isinstance(context.state, dict):
                    # Context is an object with a state dict (like MockToolContext)
                    state = context.state

                    # Check for last_tool_hook (single hook)
                    if "last_tool_hook" in state:
                        hook = state["last_tool_hook"]
                        if hook:
                            hooks.append(hook)
                            logger.info(
                                f"Extracted hook from context.state: {hook.get('type', 'unknown')}"
                            )

                    # Check for ui_functions (list of hooks)
                    if "ui_functions" in state:
                        ui_functions = state["ui_functions"]
                        if isinstance(ui_functions, list):
                            hooks.extend(ui_functions)
                            logger.info(
                                f"Extracted {len(ui_functions)} UI functions from context.state"
                            )
    except Exception as e:
        logger.debug(f"Could not extract hooks from result: {e}")

    return hooks


async def process_message(
    agent: Agent,
    user_message: str,
    full_prompt: str,
    context: dict,
) -> tuple[str, list[dict[str, Any]]]:
    """Process a user message using the OpenAI agent.

    Args:
        agent: The OpenAI Agent
        user_message: User's message/question
        full_prompt: Full prompt with conversation history
        context: Context dict for tools

    Returns:
        Tuple of (response_text, hooks)
    """
    logger.debug(f"Running agent: {agent.name}")
    result = await Runner.run(
        agent, full_prompt, context=context, max_turns=streaming_config.MAX_AGENT_TURNS
    )

    # Extract response
    response_text = result.final_output or ""
    logger.debug(f"Agent response length: {len(response_text)} characters")

    # Extract hooks from result context if available
    hooks = extract_hooks_from_result(result)
    if hooks:
        logger.info(f"Found {len(hooks)} hook(s) in result")

    return response_text, hooks
