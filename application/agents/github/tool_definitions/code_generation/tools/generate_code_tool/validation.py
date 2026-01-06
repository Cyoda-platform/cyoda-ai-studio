"""Validation logic for code generation tool.

This module handles validation of context, repository, CLI configuration,
and invocation limits before starting code generation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from application.agents.github.tool_definitions.code_generation.helpers import (
    _extract_cli_context,
    _validate_cli_invocation_limit,
)
from application.agents.github.tool_definitions.common.utils import (
    detect_project_type,
    get_cli_config,
)
from common.config.config import CLI_PROVIDER

logger = logging.getLogger(__name__)

# Configuration constants
SUPPORTED_LANGUAGES = ["python", "java"]
AUGMENT_CLI_SUPPORTED_MODEL = "haiku4.5"


async def _validate_and_prepare_context(
    user_request: str, language: Optional[str], tool_context
) -> tuple[bool, str, object]:
    """Validate context and extract CLI context with language detection.

    Args:
        user_request: User's code generation request
        language: Programming language (optional)
        tool_context: Execution context

    Returns:
        Tuple of (success, error_msg, context)
    """
    success, error_msg, context = _extract_cli_context(
        user_request, language, None, None, tool_context
    )
    if not success:
        return False, error_msg, None

    # Auto-detect language if not provided
    if not language:
        project_info = detect_project_type(context.repository_path)
        context.language = project_info["type"]
        logger.info(f"Auto-detected project type: {context.language}")

    # Validate language
    if context.language not in SUPPORTED_LANGUAGES:
        supported = ", ".join(f"'{lang}'" for lang in SUPPORTED_LANGUAGES)
        return (
            False,
            f"ERROR: Unsupported language: {context.language}. "
            f"Must be one of: {supported}",
            None,
        )

    return True, "", context


async def _validate_repository_and_config(
    context, user_request: str
) -> tuple[bool, str, Optional[Path], Optional[str]]:
    """Validate repository, CLI config, and invocation limits.

    Args:
        context: CLI context
        user_request: User request for logging

    Returns:
        Tuple of (success, error_message, script_path, cli_model)
    """
    # Validate repository exists
    repo_path = Path(context.repository_path)
    if not repo_path.exists():
        return (
            False,
            f"ERROR: Repository directory does not exist: {context.repository_path}",
            None,
            None,
        )
    if not (repo_path / ".git").exists():
        return (
            False,
            f"ERROR: Directory exists but is not a git repository: {context.repository_path}",
            None,
            None,
        )

    logger.info(f"✅ Repository verified at: {context.repository_path}")

    # Check CLI invocation limit
    is_allowed, error_msg, cli_count = _validate_cli_invocation_limit(context.session_id)
    if not is_allowed:
        return False, error_msg, None, None

    # Get CLI configuration
    script_path, cli_model = get_cli_config()
    if not script_path.exists():
        return False, f"ERROR: CLI script not found at {script_path}", None, None

    provider_name = CLI_PROVIDER.capitalize()
    logger.info(f"🤖 Generating code with {provider_name} CLI in {context.repository_path}")
    logger.info(f"📝 User request: {user_request[:100]}...")
    logger.info(f"🎯 Model: {cli_model}")

    # Validate model for Augment CLI
    if CLI_PROVIDER == "augment" and cli_model != AUGMENT_CLI_SUPPORTED_MODEL:
        logger.error(f"Invalid model for Augment CLI: {cli_model}. Only {AUGMENT_CLI_SUPPORTED_MODEL} is supported.")
        return (
            False,
            f"ERROR: Augment CLI only supports {AUGMENT_CLI_SUPPORTED_MODEL} model. Current model: {cli_model}",
            None,
            None,
        )

    return True, "", script_path, cli_model
