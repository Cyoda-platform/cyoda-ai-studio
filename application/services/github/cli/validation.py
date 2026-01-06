"""Validation functions for CLI service."""

import logging
import os
from pathlib import Path
from typing import Optional

from common.config.config import CLI_PROVIDER

logger = logging.getLogger(__name__)


def _validate_cli_inputs(
    repository_path: str,
    branch_name: str,
    language: str,
    user_request: Optional[str] = None,
    requirements: Optional[str] = None
) -> None:
    """Validate required CLI inputs.

    Args:
        repository_path: Repository path
        branch_name: Git branch name
        language: Programming language
        user_request: User request for code generation
        requirements: Requirements for build

    Raises:
        ValueError: If any required input is missing
    """
    if not repository_path:
        raise ValueError("repository_path is required")
    if not branch_name:
        raise ValueError("branch_name is required")
    if not language:
        raise ValueError("language is required")

    # Check which field was provided and validate it
    if user_request is not None:
        if not user_request:
            raise ValueError("user_request is required")
    elif requirements is not None:
        if not requirements:
            raise ValueError("requirements are required")
    else:
        raise ValueError("user_request or requirements field is required")


def _validate_script_path(script_path: Path) -> None:
    """Validate that CLI script exists.

    Args:
        script_path: Path to CLI script

    Raises:
        FileNotFoundError: If script does not exist
    """
    if not script_path.exists():
        project_root = Path(os.getcwd())
        script_path = project_root / "application" / "agents" / "shared" / f"{CLI_PROVIDER}_build.sh"
        if CLI_PROVIDER == "augment":
            script_path = project_root / "application" / "agents" / "shared" / "augment_build.sh"

        if not script_path.exists():
            raise FileNotFoundError(
                f"CLI script not found at {script_path}. "
                f"Expected location: application/agents/shared/{CLI_PROVIDER}_build.sh"
            )


def _validate_cli_provider_config(provider: str, model: str) -> None:
    """Validate CLI provider and model compatibility.

    Args:
        provider: Provider name
        model: Model name

    Raises:
        ValueError: If provider/model combination is invalid
    """
    if provider == "augment" and model != "haiku4.5":
        raise ValueError(f"Augment CLI only supports haiku4.5. Current model: {model}")
