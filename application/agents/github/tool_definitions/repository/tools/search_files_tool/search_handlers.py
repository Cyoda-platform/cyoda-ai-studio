"""Search handler functions for different search types.

This module provides search functions for content, filename, structure, and filetype searches.
"""

from __future__ import annotations

from pathlib import Path

from .command_execution import (
    execute_find_command,
    get_matching_lines,
    get_directory_contents,
    get_file_type,
)


async def search_content(
    repo_path: Path, search_pattern: str, file_pattern: str
) -> list[dict]:
    """Search file contents using grep.

    Args:
        repo_path: Repository path
        search_pattern: Regex pattern to search for
        file_pattern: File pattern to search in

    Returns:
        List of match dictionaries
    """
    success, file_paths = await execute_find_command(
        repo_path, "-name", file_pattern, "-type", "f"
    )

    if not success:
        return []

    matches = []
    for file_path in file_paths:
        rel_path = Path(file_path).relative_to(repo_path)

        # Get matching lines
        matching_lines = await get_matching_lines(file_path, search_pattern)

        if matching_lines:
            matches.append({"file": str(rel_path), "matches": matching_lines})

    return matches


async def search_filename(
    repo_path: Path, search_pattern: str
) -> list[dict]:
    """Search by filename pattern.

    Args:
        repo_path: Repository path
        search_pattern: Filename pattern

    Returns:
        List of file info dictionaries
    """
    success, file_paths = await execute_find_command(
        repo_path, "-name", search_pattern, "-type", "f"
    )

    if not success:
        return []

    matches = []
    for file_path in file_paths:
        rel_path = Path(file_path).relative_to(repo_path)
        file_info = {
            "file": str(rel_path),
            "size": Path(file_path).stat().st_size,
            "type": "file",
        }
        matches.append(file_info)

    return matches


async def search_structure(
    repo_path: Path, search_pattern: str
) -> list[dict]:
    """Search directory structure.

    Args:
        repo_path: Repository path
        search_pattern: Directory pattern

    Returns:
        List of directory info dictionaries
    """
    success, dir_paths = await execute_find_command(
        repo_path, "-name", search_pattern, "-type", "d"
    )

    if not success:
        return []

    matches = []
    for dir_path in dir_paths:
        rel_path = Path(dir_path).relative_to(repo_path)

        # List contents of directory
        contents = await get_directory_contents(dir_path)

        matches.append({"directory": str(rel_path), "contents": contents})

    return matches


async def search_filetype(
    repo_path: Path, search_pattern: str
) -> list[dict]:
    """Search by file type.

    Args:
        repo_path: Repository path
        search_pattern: File pattern

    Returns:
        List of file type info dictionaries
    """
    success, file_paths = await execute_find_command(
        repo_path, "-name", search_pattern, "-type", "f"
    )

    if not success:
        return []

    matches = []
    for file_path in file_paths:
        rel_path = Path(file_path).relative_to(repo_path)

        # Get file type
        file_type = await get_file_type(file_path)

        matches.append(
            {
                "file": str(rel_path),
                "file_type": file_type,
                "size": Path(file_path).stat().st_size,
            }
        )

    return matches


async def route_search(
    search_type: str,
    repo_path: Path,
    search_pattern: str,
    file_pattern: str,
) -> list[dict]:
    """Route search to appropriate function based on type.

    Args:
        search_type: Type of search (content, filename, structure, filetype)
        repo_path: Repository path
        search_pattern: Search pattern
        file_pattern: File pattern

    Returns:
        List of matches
    """
    if search_type == "content":
        return await search_content(repo_path, search_pattern, file_pattern)
    elif search_type == "filename":
        return await search_filename(repo_path, search_pattern)
    elif search_type == "structure":
        return await search_structure(repo_path, search_pattern)
    elif search_type == "filetype":
        return await search_filetype(repo_path, search_pattern)

    return []
