"""Command execution utilities for repository file searching.

This module provides utilities for executing Linux commands (find, grep, ls, file).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional


async def execute_find_command(repo_path: Path, *args: str) -> tuple[bool, list[str]]:
    """Execute find command and return file paths.

    Args:
        repo_path: Repository path
        *args: Additional arguments for find command

    Returns:
        Tuple of (success, list of file paths)
    """
    cmd = ["find", str(repo_path)] + list(args)

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(repo_path),
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0 or not stdout:
        return False, []

    file_paths = [f for f in stdout.decode().strip().split("\n") if f]
    return True, file_paths


async def get_matching_lines(file_path: str, pattern: str) -> list[dict]:
    """Get matching lines from file with line numbers.

    Args:
        file_path: Path to file
        pattern: Regex pattern to search for

    Returns:
        List of match dictionaries with line_number and content
    """
    grep_cmd = ["grep", "-n", "-E", pattern, file_path]
    grep_process = await asyncio.create_subprocess_exec(
        *grep_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    grep_stdout, _ = await grep_process.communicate()

    matches = []
    if grep_stdout:
        for line in grep_stdout.decode().split("\n"):
            if line.strip():
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    matches.append(
                        {"line_number": int(parts[0]), "content": parts[2].strip()}
                    )

    return matches


async def get_directory_contents(dir_path: str) -> list[dict]:
    """Get contents of directory using ls.

    Args:
        dir_path: Directory path

    Returns:
        List of content dictionaries
    """
    ls_cmd = ["ls", "-la", dir_path]
    ls_process = await asyncio.create_subprocess_exec(
        *ls_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    ls_stdout, _ = await ls_process.communicate()

    contents = []
    if ls_stdout:
        # Skip total line and header
        for line in ls_stdout.decode().split("\n")[1:]:
            if line.strip() and not line.startswith("total"):
                parts = line.split()
                if len(parts) >= 9:
                    contents.append(
                        {
                            "name": parts[-1],
                            "type": "directory" if line.startswith("d") else "file",
                            "permissions": parts[0],
                            "size": parts[4] if not line.startswith("d") else None,
                        }
                    )

    return contents


async def get_file_type(file_path: str) -> str:
    """Get file type using file command.

    Args:
        file_path: Path to file

    Returns:
        File type string
    """
    file_cmd = ["file", "-b", file_path]
    file_process = await asyncio.create_subprocess_exec(
        *file_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    file_stdout, _ = await file_process.communicate()

    return file_stdout.decode().strip() if file_stdout else "unknown"
