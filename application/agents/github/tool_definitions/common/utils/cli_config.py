"""CLI configuration utilities for GitHub agent tools.

This module provides utilities for determining CLI script paths and models
based on the configured CLI provider.
"""

from __future__ import annotations

import os
from pathlib import Path

from common.config.config import CLI_PROVIDER, AUGMENT_MODEL, CLAUDE_MODEL, GEMINI_MODEL

# Get module directory (github agent directory)
_MODULE_DIR = Path(__file__).parent.parent.parent.parent
_BUILD_MODE = os.getenv("BUILD_MODE", "production").lower()

# Determine CLI script paths based on provider and build mode
if _BUILD_MODE == "test":
    _DEFAULT_AUGGIE_SCRIPT = _MODULE_DIR.parent / "shared" / "augment_build_mock.sh"
    _DEFAULT_CLAUDE_SCRIPT = _MODULE_DIR.parent / "shared" / "augment_build_mock.sh"  # Use mock for testing
    _DEFAULT_GEMINI_SCRIPT = _MODULE_DIR.parent / "shared" / "augment_build_mock.sh"  # Use mock for testing
else:
    _DEFAULT_AUGGIE_SCRIPT = _MODULE_DIR.parent / "shared" / "augment_build.sh"
    _DEFAULT_CLAUDE_SCRIPT = _MODULE_DIR.parent / "shared" / "claude_build.sh"
    _DEFAULT_GEMINI_SCRIPT = _MODULE_DIR.parent / "shared" / "gemini_build.sh"

# Legacy env var for backward compatibility
AUGGIE_CLI_SCRIPT = os.getenv("AUGMENT_CLI_SCRIPT", str(_DEFAULT_AUGGIE_SCRIPT))


def get_cli_config(provider: str = None) -> tuple[Path, str]:
    """Get CLI script path and model based on provider.

    Args:
        provider: CLI provider ("augment", "claude", or "gemini").
                 If None, uses CLI_PROVIDER from config.

    Returns:
        Tuple of (script_path, model)
    """
    provider = provider or CLI_PROVIDER

    if provider == "claude":
        return _DEFAULT_CLAUDE_SCRIPT, CLAUDE_MODEL
    elif provider == "gemini":
        return _DEFAULT_GEMINI_SCRIPT, GEMINI_MODEL
    else:  # default to augment
        return _DEFAULT_AUGGIE_SCRIPT, AUGMENT_MODEL
