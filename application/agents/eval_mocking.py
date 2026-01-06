"""Tool mocking utilities for ADK evaluations.

This module provides comprehensive mocking of all tool calls during evaluations.
Instead of executing real tools, it logs the calls and returns mock responses.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def mock_all_tools_callback(tool, args: dict[str, Any], tool_context) -> Optional[dict]:
    """Mock callback that intercepts ALL tool calls during evaluation.

    This prevents actual tool execution and returns predefined success responses.
    The goal is to verify tool selection and sequencing, not actual execution.

    Special case: transfer_to_agent is NOT mocked, allowing agent transfers to work
    normally during evaluation so multi-agent workflows can be tested.

    Args:
        tool: The tool being called
        args: The arguments passed to the tool
        tool_context: The tool execution context

    Returns:
        Dict with mocked response, or None to let tool execute normally
    """
    tool_name = tool.name if hasattr(tool, 'name') else str(tool)
    tool_args = args or {}

    # Log the tool call for tracking
    logger.info(f"🎯 [EVAL MOCK] Tool called: {tool_name} with args: {tool_args}")

    # IMPORTANT: Do not mock transfer_to_agent - let it execute normally
    # This allows agent transfers to actually work during evaluation
    if tool_name == "transfer_to_agent":
        logger.info(f"🔄 [EVAL MOCK] Allowing transfer_to_agent to execute normally")
        return None  # None means "let the tool execute normally"

    # Define mock responses for each tool
    mock_responses = {
        # Agent transfer tools
        "transfer_to_agent": f"Successfully transferred to {tool_args.get('agent_name', 'unknown_agent')}",

        # Repository configuration
        "set_repository_config": f"Repository configuration set to {tool_args.get('repository_type', 'unknown')}",
        "generate_branch_uuid": "test-branch-uuid-12345",
        "check_existing_branch_configuration": "No branch configuration found in conversation",

        # Repository operations
        "clone_repository": {
            "success": True,
            "branch": "test-branch-uuid-12345",
            "path": "/tmp/mocked/repo/path",
            "message": "Repository cloned successfully (mocked)"
        },
        "save_file_to_repository": {
            "success": True,
            "file_path": tool_args.get("file_path", "/mocked/file/path"),
            "message": "File saved successfully (mocked)"
        },
        "commit_and_push_changes": {
            "success": True,
            "commit_sha": "abc123def456",
            "message": "Changes committed and pushed successfully (mocked)"
        },
        "pull_repository_changes": {
            "success": True,
            "message": "Repository changes pulled successfully (mocked)"
        },
        "get_repository_diff": {
            "diff": "mocked diff output",
            "files_changed": 3
        },

        # Path helpers
        "get_requirements_path": "/workspace/requirements.md",
        "get_workflow_path": "/workspace/workflow.json",
        "get_entity_path": "/workspace/entity.json",

        # Workflow tools
        "load_workflow_schema": {"schema": "mocked_schema"},
        "load_workflow_example": {"example": "mocked_example"},
        "load_workflow_prompt": {"prompt": "mocked_prompt"},
        "validate_workflow_against_schema": {
            "valid": True,
            "message": "Workflow is valid (mocked)"
        },

        # Code generation
        "generate_application": {
            "success": True,
            "task_id": "build-task-12345",
            "message": "Application generation started (mocked)",
            "status": "running"
        },
        "generate_code_with_cli": {
            "success": True,
            "message": "Code generation completed (mocked)"
        },

        # Repository analysis
        "analyze_repository_structure": {
            "structure": "mocked repository structure",
            "files": ["file1.py", "file2.py"]
        },
        "analyze_repository_structure_agentic": {
            "structure": "mocked agentic repository structure",
            "analysis": "Repository contains Python application"
        },

        # Unix command execution
        "execute_unix_command": {
            "stdout": "mocked command output",
            "stderr": "",
            "exit_code": 0,
            "success": True
        },

        # UI tools
        "ask_user_to_select_option": (
            f"{tool_args.get('question', 'Please select an option')}\n\n"
            "Please select your choice(s) using the options below."
        ),

        # File management
        "retrieve_and_save_conversation_files": {
            "success": True,
            "files_saved": 3,
            "message": "Conversation files retrieved and saved (mocked)"
        },
        "save_files_to_branch": {
            "success": True,
            "files_saved": 5,
            "message": "Files saved to branch (mocked)"
        },

        # Environment tools
        "check_user_environment_status": {
            "status": "ready",
            "environment_exists": True,
            "message": "Environment is ready (mocked)"
        },
        "deploy_cyoda_environment": {
            "success": True,
            "deployment_id": "deployment-12345",
            "status": "deployed",
            "message": "Environment deployed successfully (mocked)"
        },

        # MCP tools
        "get_file_contents": {
            "content": "# Mocked file content\n\nThis is mocked.",
            "path": tool_args.get("path", "/mocked/path")
        },
        "search_code": {
            "results": [],
            "total_count": 0
        },
        "list_commits": {
            "commits": [
                {"sha": "abc123", "message": "Mocked commit 1"},
                {"sha": "def456", "message": "Mocked commit 2"}
            ]
        },
        "get_commit": {
            "sha": tool_args.get("sha", "abc123"),
            "message": "Mocked commit message"
        },
        "list_issues": {"issues": []},
        "get_issue": {"issue": {"id": 1, "title": "Mocked issue"}},
        "list_pull_requests": {"prs": []},
        "get_pull_request": {"pr": {"id": 1, "title": "Mocked PR"}},

        # QA tools
        "search_cyoda_concepts": f"Mocked search result for: {tool_args.get('query', 'unknown')}",

        # Data agent tools
        "query_cyoda_data": {
            "results": [],
            "count": 0,
            "message": "Query executed successfully (mocked)"
        },
    }

    # Get mock response or use generic success response
    if tool_name in mock_responses:
        mock_output = mock_responses[tool_name]
    else:
        # Generic success response for unknown tools
        mock_output = {
            "success": True,
            "message": f"Tool {tool_name} executed successfully (mocked)",
            "mocked": True
        }
        logger.warning(f"⚠️ [EVAL MOCK] No specific mock for tool: {tool_name}, using generic response")

    logger.info(f"✅ [EVAL MOCK] Returning mock response for {tool_name}")

    return mock_output
