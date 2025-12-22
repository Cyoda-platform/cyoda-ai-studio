"""Canvas Agent tools for workflow, entity, and requirements creation."""

from __future__ import annotations

import json
import logging
from typing import Optional

from google.adk.tools.tool_context import ToolContext
from pydantic import ValidationError

# Make ToolContext available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve ToolContext in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext"]

from application.agents.shared.hook_decorator import creates_hook
from application.agents.canvas.models import WorkflowSchema, EntitySchema

logger = logging.getLogger(__name__)


async def validate_workflow_schema(
    workflow_json: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Validate workflow JSON against Cyoda schema.
    
    Args:
        workflow_json: Workflow JSON as string
        tool_context: ADK tool context
        
    Returns:
        Validation result with any errors
    """
    try:
        # Validate against Pydantic model
        WorkflowSchema.model_validate_json(workflow_json)
        return json.dumps({"valid": True, "message": "Workflow schema is valid"})
        
    except ValidationError as e:
        return json.dumps({
            "valid": False,
            "errors": [f"Validation error: {str(e)}"]
        })
    except Exception as e:
        logger.error(f"Error validating workflow schema: {e}", exc_info=True)
        return json.dumps({
            "valid": False,
            "errors": [f"Validation error: {str(e)}"]
        })


async def validate_entity_schema(
    entity_json: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Validate entity JSON against Cyoda schema.
    
    Args:
        entity_json: Entity JSON as string
        tool_context: ADK tool context
        
    Returns:
        Validation result with any errors
    """
    try:
        # Validate against Pydantic model
        EntitySchema.model_validate_json(entity_json)
        return json.dumps({"valid": True, "message": "Entity schema is valid"})
        
    except ValidationError as e:
        return json.dumps({
            "valid": False,
            "errors": [f"Validation error: {str(e)}"]
        })
    except Exception as e:
        logger.error(f"Error validating entity schema: {e}", exc_info=True)
        return json.dumps({
            "valid": False,
            "errors": [f"Validation error: {str(e)}"]
        })


@creates_hook("code_changes")
async def create_canvas_refresh_hook(
    conversation_id: Optional[str] = None,
    repository_name: Optional[str] = None,
    branch_name: Optional[str] = None,
    repository_url: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Create a canvas_open hook to display resources on canvas.

    Args:
        conversation_id: Conversation ID for context
        repository_name: Repository name (owner/repo)
        branch_name: Branch name
        repository_url: Full GitHub URL to the branch
        tool_context: ADK tool context

    Returns:
        Success message with hook attached for SSE streaming
    """
    try:
        from application.agents.shared.hook_utils import (
            create_canvas_open_hook as create_hook,
            wrap_response_with_hook,
        )

        if not tool_context:
            return "ERROR: Tool context not available"

        # Get values from tool_context if not provided
        if not conversation_id:
            conversation_id = tool_context.state.get("conversation_id")
        if not repository_name:
            repository_name = tool_context.state.get("repository_name")
        if not branch_name:
            branch_name = tool_context.state.get("branch_name")
        if not repository_url:
            owner = tool_context.state.get("repository_owner")
            repo = tool_context.state.get("repository_name")
            branch = tool_context.state.get("branch_name")
            if owner and repo and branch:
                repository_url = f"https://github.com/{owner}/{repo}/tree/{branch}"

        hook = create_hook(
            conversation_id=conversation_id or "unknown",
            repository_name=repository_name or "unknown",
            branch_name=branch_name or "unknown",
            repository_url=repository_url or "unknown",
        )

        # Store hook in context for SSE streaming
        tool_context.state["last_tool_hook"] = hook

        message = "✅ Opening Canvas to view your artifacts..."
        logger.info(f"🎨 Created canvas refresh hook for conversation {conversation_id}")
        return wrap_response_with_hook(message, hook)

    except Exception as e:
        logger.error(f"Error creating canvas_open hook: {e}", exc_info=True)
        return f"ERROR: Failed to create canvas hook: {str(e)}"