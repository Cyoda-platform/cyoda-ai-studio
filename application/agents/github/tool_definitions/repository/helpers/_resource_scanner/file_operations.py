"""File operations for resource scanning.

This module provides utilities for finding and parsing JSON files in repository directories.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from ....common.constants import EXT_JSON

logger = logging.getLogger(__name__)


def find_json_file_in_directory(
    directory: Path, expected_name: str
) -> Optional[Path]:
    """Find JSON file in directory using flexible matching strategy.

    This function searches for JSON files using:
    1. Exact match: expected_name.json
    2. Case-insensitive match: any .json file matching expected_name
    3. Single file fallback: if only one .json file exists, use it

    Args:
        directory: Directory to search
        expected_name: Expected base name (without extension)

    Returns:
        Path to JSON file if found, None otherwise
    """
    # Try exact match first
    exact_match = directory / f"{expected_name}{EXT_JSON}"
    if exact_match.exists():
        return exact_match

    # Get all JSON files
    json_files = list(directory.glob(f"*{EXT_JSON}"))
    if not json_files:
        return None

    # Try case-insensitive match
    for json_file in json_files:
        if json_file.stem.lower() == expected_name.lower():
            return json_file

    # Fallback: use single JSON file if only one exists
    if len(json_files) == 1:
        logger.info(
            f"Using JSON file {json_files[0].name} for {expected_name}"
        )
        return json_files[0]

    return None


def parse_json_file(file_path: Path) -> Optional[dict]:
    """Parse JSON file and return content.

    Args:
        file_path: Path to JSON file

    Returns:
        Parsed JSON content or None if parsing fails
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to parse JSON file {file_path}: {e}")
        return None
