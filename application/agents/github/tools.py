"""Tools for GitHub agent - repository operations and canvas integration."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation by Google ADK
# This is needed because 'from __future__ import annotations' makes all annotations strings,
# and typing.get_type_hints() needs to resolve ToolContext in the module's globals
# Must be done BEFORE any function definitions so it's in the module's namespace
__all__ = ["ToolContext"]

from application.agents.shared.hook_decorator import creates_hook
from application.agents.shared.prompt_loader import load_template
from application.entity.conversation import Conversation
from application.services.github.github_service import GitHubService
from services.services import get_entity_service

logger = logging.getLogger(__name__)

# Resource paths from environment
PYTHON_RESOURCES_PATH = os.getenv("PYTHON_RESOURCES_PATH", "application/resources")
JAVA_RESOURCES_PATH = os.getenv("JAVA_RESOURCES_PATH", "src/main/resources")

# Error suffix to instruct LLM to stop on errors
STOP_ON_ERROR = " STOP: Do not retry this operation. Report this error to the user and wait for instructions."

# Augment CLI configuration for GitHub agent
_MODULE_DIR = Path(__file__).parent
_DEFAULT_AUGGIE_SCRIPT = _MODULE_DIR.parent / "shared" / "augment_build.sh"
AUGGIE_CLI_SCRIPT = os.getenv("AUGMENT_CLI_SCRIPT", str(_DEFAULT_AUGGIE_SCRIPT))


async def _get_github_service_from_context(tool_context: ToolContext) -> GitHubService:
    """Get GitHubService instance from tool context.

    Uses installation_id from Conversation entity if available,
    otherwise falls back to environment variable.
    """
    conversation_id = tool_context.state.get("conversation_id")
    if not conversation_id:
        raise ValueError("conversation_id not found in tool context")

    # Get repository info from conversation
    entity_service = get_entity_service()
    conversation_response = await entity_service.get_by_id(
        entity_id=conversation_id,
        entity_class=Conversation.ENTITY_NAME,
        entity_version=str(Conversation.ENTITY_VERSION),
    )

    if not conversation_response:
        raise ValueError(f"Conversation {conversation_id} not found")

    # Handle conversation data (can be dict or object)
    conversation_data = conversation_response.data
    if isinstance(conversation_data, dict):
        # It's a dictionary - access directly
        installation_id_str = conversation_data.get('installation_id')
    else:
        # It's an object - use attribute access
        installation_id_str = getattr(conversation_data, 'installation_id', None)

    # Fallback to environment variable if not in conversation
    if not installation_id_str:
        installation_id_str = os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID")
    if not installation_id_str:
        raise ValueError(
            "installation_id not found in Conversation entity or GITHUB_PUBLIC_REPO_INSTALLATION_ID environment variable"
        )

    installation_id = int(installation_id_str)
    logger.info(f"Using GitHub installation ID: {installation_id}")

    return GitHubService(installation_id=installation_id)


def _detect_project_type(repo_path: str) -> Dict[str, str]:
    """Detect project type (Python or Java) and return resource paths."""
    repo_path_obj = Path(repo_path)

    # Check for Python project
    if (repo_path_obj / "application").exists():
        return {
            "type": "python",
            "resources_path": PYTHON_RESOURCES_PATH,
            "entities_path": f"{PYTHON_RESOURCES_PATH}/entity",
            "workflows_path": f"{PYTHON_RESOURCES_PATH}/workflow",
            "requirements_path": f"{PYTHON_RESOURCES_PATH}/functional_requirements",
        }

    # Check for Java project
    if (repo_path_obj / "src" / "main").exists():
        return {
            "type": "java",
            "resources_path": JAVA_RESOURCES_PATH,
            "entities_path": f"{JAVA_RESOURCES_PATH}/entity",
            "workflows_path": f"{JAVA_RESOURCES_PATH}/workflow",
            "requirements_path": f"{JAVA_RESOURCES_PATH}/functional_requirements",
        }

    raise ValueError(f"Could not detect project type in {repo_path}")


def _scan_versioned_resources(resources_dir: Path, resource_type: str, repo_path_obj: Path) -> List[Dict[str, Any]]:
    """
    Generic scanner for versioned resources (entities, workflows, etc.).

    This function automatically detects the structure and scans for:
    1. Direct files: resource_name.json
    2. Versioned directories: resource_name/version_N/resource_name.json

    The scanner intelligently finds JSON files using:
    - Exact match: resource_name.json
    - Case-insensitive match: any .json file matching resource_name (e.g., CustomerWorkflow.json for customerworkflow)
    - Single file fallback: if only one .json file exists in the directory, use it

    This allows for flexible naming conventions (e.g., customerworkflow/version_1/CustomerWorkflow.json).

    Args:
        resources_dir: Path to the resource directory (e.g., .../entity, .../workflow)
        resource_type: Type of resource for logging ("entity", "workflow", etc.)
        repo_path_obj: Repository root path for relative path calculation

    Returns:
        List of resource dictionaries with name, version, path, and content
    """
    resources = []

    if not resources_dir.exists():
        logger.info(f"📁 {resource_type.title()} directory not found: {resources_dir}")
        return resources

    logger.info(f"📁 Scanning {resource_type} directory: {resources_dir}")

    for item in sorted(resources_dir.iterdir()):
        if item.name.startswith("_"):
            continue  # Skip hidden/private directories

        if item.is_file() and item.suffix == ".json":
            # Direct JSON file (no versioning)
            try:
                with open(item, "r") as f:
                    content = json.load(f)

                resource_dict = {
                    "name": item.stem,
                    "version": None,  # No version for direct files
                    "path": str(item.relative_to(repo_path_obj)),
                    "content": content,
                }

                # For workflows, try to extract entity name from the workflow content
                if resource_type == "workflow" and isinstance(content, dict):
                    entity_name = content.get("entity_name") or content.get("entityName")
                    if entity_name:
                        resource_dict["entity_name"] = entity_name
                        logger.info(f"   - Workflow {item.stem} associated with entity: {entity_name}")

                resources.append(resource_dict)

                logger.info(f"✅ Parsed {resource_type}: {item.stem} (direct file)")

            except Exception as e:
                logger.warning(f"Failed to parse {resource_type} {item}: {e}")

        elif item.is_dir():
            # Directory - check for versioned structure
            resource_name = item.name
            logger.info(f"🔍 Found {resource_type} directory: {resource_name}")

            # Look for version directories
            version_dirs = [d for d in item.iterdir()
                            if d.is_dir() and d.name.startswith("version_")]

            if version_dirs:
                # Versioned resource - scan all versions
                def version_sort_key(version_dir):
                    try:
                        return int(version_dir.name.split("_")[1])
                    except (IndexError, ValueError):
                        return 0

                for version_dir in sorted(version_dirs, key=version_sort_key):
                    version_name = version_dir.name

                    # Try to find JSON file intelligently:
                    # 1. Exact match: resource_name.json
                    # 2. Case-insensitive match: any .json file matching resource_name
                    # 3. Any .json file in the directory (fallback)
                    resource_file = None

                    # Try exact match first
                    exact_match = version_dir / f"{resource_name}.json"
                    if exact_match.exists():
                        resource_file = exact_match
                    else:
                        # Try case-insensitive match
                        json_files = list(version_dir.glob("*.json"))
                        if json_files:
                            # Look for case-insensitive match
                            for json_file in json_files:
                                if json_file.stem.lower() == resource_name.lower():
                                    resource_file = json_file
                                    break

                            # If no case-insensitive match, use the first JSON file
                            if not resource_file and len(json_files) == 1:
                                resource_file = json_files[0]
                                logger.info(f"Using JSON file {resource_file.name} for {resource_type} {resource_name}")

                    if resource_file and resource_file.exists():
                        try:
                            with open(resource_file, "r") as f:
                                content = json.load(f)

                            resource_dict = {
                                "name": resource_name,
                                "version": version_name,
                                "path": str(resource_file.relative_to(repo_path_obj)),
                                "content": content,
                            }

                            # For workflows, try to extract entity name from the workflow content
                            # Workflows may have an entity_name field in their JSON
                            if resource_type == "workflow" and isinstance(content, dict):
                                # Check if workflow content has entity_name field
                                entity_name = content.get("entity_name") or content.get("entityName")
                                if entity_name:
                                    resource_dict["entity_name"] = entity_name
                                    logger.info(f"   - Workflow {resource_name} associated with entity: {entity_name}")

                            resources.append(resource_dict)

                            logger.info(f"✅ Parsed {resource_type}: {resource_name} {version_name}")

                        except Exception as e:
                            logger.warning(f"Failed to parse {resource_type} {resource_file}: {e}")
                    else:
                        logger.warning(f"{resource_type.title()} file not found in {version_dir}")

            else:
                # Directory without version structure - check for direct JSON file
                # Try to find JSON file intelligently (same logic as versioned)
                direct_file = None

                # Try exact match first
                exact_match = item / f"{resource_name}.json"
                if exact_match.exists():
                    direct_file = exact_match
                else:
                    # Try case-insensitive match
                    json_files = list(item.glob("*.json"))
                    if json_files:
                        # Look for case-insensitive match
                        for json_file in json_files:
                            if json_file.stem.lower() == resource_name.lower():
                                direct_file = json_file
                                break

                        # If no case-insensitive match, use the first JSON file
                        if not direct_file and len(json_files) == 1:
                            direct_file = json_files[0]
                            logger.info(f"Using JSON file {direct_file.name} for {resource_type} {resource_name}")

                if direct_file and direct_file.exists():
                    try:
                        with open(direct_file, "r") as f:
                            content = json.load(f)

                        resource_dict = {
                            "name": resource_name,
                            "version": None,
                            "path": str(direct_file.relative_to(repo_path_obj)),
                            "content": content,
                        }

                        # For workflows, try to extract entity name from the workflow content
                        if resource_type == "workflow" and isinstance(content, dict):
                            entity_name = content.get("entity_name") or content.get("entityName")
                            if entity_name:
                                resource_dict["entity_name"] = entity_name
                                logger.info(f"   - Workflow {resource_name} associated with entity: {entity_name}")

                        resources.append(resource_dict)

                        logger.info(f"✅ Parsed {resource_type}: {resource_name} (directory file)")

                    except Exception as e:
                        logger.warning(f"Failed to parse {resource_type} {direct_file}: {e}")
                else:
                    logger.warning(f"No {resource_type} files found in directory: {item}")

    return resources


async def get_entity_path(entity_name: str, version: int, project_type: str) -> str:
    """
    Get the correct path for an entity file.

    Args:
        entity_name: Name of the entity (e.g., "order", "customer")
        version: Version number (e.g., 1)
        project_type: "python" or "java"

    Returns:
        Correct path for the entity file

    Examples:
        get_entity_path("order", 1, "python") -> "application/resources/entity/order/version_1/order.json"
        get_entity_path("customer", 1, "java") -> "src/main/resources/entity/customer/version_1/customer.json"
    """
    if project_type == "python":
        return f"{PYTHON_RESOURCES_PATH}/entity/{entity_name}/version_{version}/{entity_name}.json"
    elif project_type == "java":
        return f"{JAVA_RESOURCES_PATH}/entity/{entity_name}/version_{version}/{entity_name}.json"
    else:
        raise ValueError(f"Unsupported project type: {project_type}")


async def get_workflow_path(workflow_name: str, project_type: str, version: int = 1) -> str:
    """
    Get the correct path for a workflow file in versioned folder structure.

    Args:
        workflow_name: Name of the workflow (e.g., "OrderProcessing", "CustomerOnboarding")
        project_type: "python" or "java"
        version: Version number (defaults to 1)

    Returns:
        Correct path for the workflow file in versioned folder

    Examples:
        get_workflow_path("OrderProcessing", "python", 1) -> "application/resources/workflow/orderprocessing/version_1/OrderProcessing.json"
        get_workflow_path("CustomerOnboarding", "java", 1) -> "src/main/resources/workflow/customeronboarding/version_1/CustomerOnboarding.json"
    """
    # Convert workflow name to lowercase for folder name (following entity pattern)
    folder_name = workflow_name.lower()

    if project_type == "python":
        return f"{PYTHON_RESOURCES_PATH}/workflow/{folder_name}/version_{version}/{workflow_name}.json"
    elif project_type == "java":
        return f"{JAVA_RESOURCES_PATH}/workflow/{folder_name}/version_{version}/{workflow_name}.json"
    else:
        raise ValueError(f"Unsupported project type: {project_type}")


async def search_repository_files(
    search_pattern: str,
    file_pattern: str = "*",
    search_type: str = "content",
    tool_context: ToolContext = None
) -> str:
    """
    Search repository files using Linux tools and regular expressions.

    This is an agentic tool that allows flexible repository exploration using:
    - find: Locate files by name/path patterns
    - grep: Search file contents with regex
    - ls: List directory contents
    - file: Identify file types

    Args:
        search_pattern: Search pattern (regex for content, glob for files)
        file_pattern: File pattern to search in (e.g., "*.json", "*.md", "**/version_*/*")
        search_type: Type of search - "content", "filename", "structure", "filetype"
        tool_context: Execution context

    Returns:
        JSON string with search results

    Examples:
        # Find all entity files
        search_repository_files("*", "**/entity/**/*.json", "filename")

        # Search for specific content in workflows
        search_repository_files("OrderProcessing", "**/*workflow*/*.json", "content")

        # Find all version directories
        search_repository_files("version_*", "*", "structure")

        # Find all JSON files
        search_repository_files("*.json", "*", "filetype")
    """
    try:
        if not tool_context:
            return json.dumps({"error": "Tool context not available"})

        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return json.dumps({"error": "Repository path not found in context"})

        repo_path = Path(repository_path)
        if not repo_path.exists():
            return json.dumps({"error": f"Repository path does not exist: {repository_path}"})

        import subprocess
        import asyncio

        results = {
            "search_type": search_type,
            "search_pattern": search_pattern,
            "file_pattern": file_pattern,
            "repository_path": str(repository_path),
            "matches": [],
            "summary": {}
        }

        if search_type == "content":
            # Use grep to search file contents with regex
            cmd = [
                "find", str(repo_path),
                "-name", file_pattern,
                "-type", "f",
                "-exec", "grep", "-l", "-E", search_pattern, "{}", ";"
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(repo_path)
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0 and stdout:
                file_paths = stdout.decode().strip().split('\n')
                for file_path in file_paths:
                    if file_path:
                        rel_path = Path(file_path).relative_to(repo_path)

                        # Get matching lines
                        grep_cmd = ["grep", "-n", "-E", search_pattern, file_path]
                        grep_process = await asyncio.create_subprocess_exec(
                            *grep_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        grep_stdout, _ = await grep_process.communicate()

                        matches = []
                        if grep_stdout:
                            for line in grep_stdout.decode().split('\n'):
                                if line.strip():
                                    parts = line.split(':', 2)
                                    if len(parts) >= 3:
                                        matches.append({
                                            "line_number": int(parts[0]),
                                            "content": parts[2].strip()
                                        })

                        results["matches"].append({
                            "file": str(rel_path),
                            "matches": matches
                        })

        elif search_type == "filename":
            # Use find to search by filename pattern
            cmd = ["find", str(repo_path), "-name", search_pattern, "-type", "f"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0 and stdout:
                file_paths = stdout.decode().strip().split('\n')
                for file_path in file_paths:
                    if file_path:
                        rel_path = Path(file_path).relative_to(repo_path)
                        file_info = {
                            "file": str(rel_path),
                            "size": Path(file_path).stat().st_size,
                            "type": "file"
                        }
                        results["matches"].append(file_info)

        elif search_type == "structure":
            # Use find to explore directory structure
            cmd = ["find", str(repo_path), "-name", search_pattern, "-type", "d"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0 and stdout:
                dir_paths = stdout.decode().strip().split('\n')
                for dir_path in dir_paths:
                    if dir_path:
                        rel_path = Path(dir_path).relative_to(repo_path)

                        # List contents of directory
                        ls_cmd = ["ls", "-la", dir_path]
                        ls_process = await asyncio.create_subprocess_exec(
                            *ls_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        ls_stdout, _ = await ls_process.communicate()

                        contents = []
                        if ls_stdout:
                            for line in ls_stdout.decode().split('\n')[1:]:  # Skip total line
                                if line.strip() and not line.startswith('total'):
                                    parts = line.split()
                                    if len(parts) >= 9:
                                        contents.append({
                                            "name": parts[-1],
                                            "type": "directory" if line.startswith('d') else "file",
                                            "permissions": parts[0],
                                            "size": parts[4] if not line.startswith('d') else None
                                        })

                        results["matches"].append({
                            "directory": str(rel_path),
                            "contents": contents
                        })

        elif search_type == "filetype":
            # Use file command to identify file types
            cmd = ["find", str(repo_path), "-name", search_pattern, "-type", "f"]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0 and stdout:
                file_paths = stdout.decode().strip().split('\n')
                for file_path in file_paths:
                    if file_path:
                        rel_path = Path(file_path).relative_to(repo_path)

                        # Get file type
                        file_cmd = ["file", "-b", file_path]
                        file_process = await asyncio.create_subprocess_exec(
                            *file_cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        file_stdout, _ = await file_process.communicate()

                        file_type = file_stdout.decode().strip() if file_stdout else "unknown"

                        results["matches"].append({
                            "file": str(rel_path),
                            "file_type": file_type,
                            "size": Path(file_path).stat().st_size
                        })

        # Generate summary
        results["summary"] = {
            "total_matches": len(results["matches"]),
            "search_completed": True
        }

        logger.info(f"🔍 Search completed: {len(results['matches'])} matches for '{search_pattern}' ({search_type})")

        return json.dumps(results, indent=2)

    except Exception as e:
        logger.error(f"Error in repository search: {e}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "search_type": search_type,
            "search_pattern": search_pattern
        })


async def _validate_command_security(command: str, repo_path: str) -> Dict[str, Any]:
    """
    Comprehensive security validation for Unix commands.

    This function implements multiple layers of security to ensure only safe,
    read-only operations are allowed within the repository directory.

    Args:
        command: The command to validate
        repo_path: The repository path (for path validation)

    Returns:
        Dict with 'safe' (bool) and 'reason' (str) keys
    """
    import re
    import shlex

    try:
        # Parse command safely
        try:
            command_parts = shlex.split(command)
        except ValueError as e:
            return {"safe": False, "reason": f"Invalid command syntax: {e}"}

        if not command_parts:
            return {"safe": False, "reason": "Empty command"}

        base_command = command_parts[0]

        # 1. Whitelist of allowed commands (read-only operations)
        allowed_commands = {
            # File system exploration
            'find', 'ls', 'tree', 'du', 'stat', 'file',
            # Text processing and viewing
            'cat', 'head', 'tail', 'less', 'more', 'grep', 'egrep', 'fgrep',
            # Text manipulation (read-only)
            'sort', 'uniq', 'cut', 'awk', 'sed', 'tr', 'wc', 'nl',
            # Path utilities
            'basename', 'dirname', 'realpath', 'readlink',
            # Archive viewing (read-only)
            'tar', 'gzip', 'gunzip', 'zcat',
            # JSON/data processing
            'jq'
        }

        if base_command not in allowed_commands:
            return {
                "safe": False,
                "reason": f"Command '{base_command}' is not in the allowed list of read-only commands"
            }

        # 2. Blacklist of dangerous patterns
        dangerous_patterns = [
            # File modification/deletion
            r'\brm\b', r'\bmv\b', r'\bcp\b', r'\btouch\b', r'\bmkdir\b', r'\brmdir\b',
            # Permission changes
            r'\bchmod\b', r'\bchown\b', r'\bchgrp\b',
            # System/privilege escalation
            r'\bsudo\b', r'\bsu\b', r'\bsudo\s', r'\bsu\s',
            # Output redirection (can overwrite files)
            r'>', r'>>', r'\btee\b',
            # Process control
            r'\bkill\b', r'\bkillall\b', r'\bpkill\b',
            # Network operations
            r'\bcurl\b', r'\bwget\b', r'\bssh\b', r'\bscp\b', r'\brsync\b',
            # System modification
            r'\bmount\b', r'\bumount\b', r'\bfdisk\b', r'\bdd\b',
            # Package management
            r'\bapt\b', r'\byum\b', r'\bpip\b', r'\bnpm\b',
            # Dangerous file operations
            r'\bshred\b', r'\bwipe\b', r'\btruncate\b'
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return {
                    "safe": False,
                    "reason": f"Command contains dangerous pattern: {pattern}"
                }

        # 3. Path validation - ensure operations stay within repository
        # Check for path traversal attempts
        path_traversal_patterns = [
            r'\.\./\.\.',  # ../..
            r'/\.\./\.\.',  # /../..
            r'~/',  # Home directory
            r'/tmp',  # Temp directory
            r'/var',  # System directories
            r'/etc',  # System config
            r'/usr',  # System binaries
            r'/bin',  # System binaries
            r'/sbin',  # System binaries
            r'/root',  # Root directory
        ]

        for pattern in path_traversal_patterns:
            if re.search(pattern, command):
                return {
                    "safe": False,
                    "reason": f"Command contains path traversal or system directory access"
                }

        # 4. Command length validation (prevent command injection)
        if len(command) > 1000:
            return {
                "safe": False,
                "reason": "Command is too long (max 1000 characters)"
            }

        # 5. Environment variable validation
        env_var_patterns = [
            r'\$\{[^}]*\}',  # ${VAR}
            r'\$[A-Z_][A-Z0-9_]*',  # $VAR
        ]

        for pattern in env_var_patterns:
            if re.search(pattern, command):
                return {
                    "safe": False,
                    "reason": "Environment variable usage is not allowed for security"
                }

        # If all checks pass, command is safe
        return {"safe": True, "reason": "Command passed all security checks"}

    except Exception as e:
        return {
            "safe": False,
            "reason": f"Security validation error: {str(e)}"
        }


async def execute_unix_command(
    command: str,
    tool_context: ToolContext = None
) -> str:
    """
    Execute any Unix command in the repository directory.

    This is a powerful agentic tool that allows the AI to use any Linux/Unix command
    for repository analysis, including:
    - find: Search for files and directories
    - grep: Search file contents with regex
    - ls: List directory contents
    - cat: Read file contents
    - head/tail: Read parts of files
    - wc: Count lines/words/characters
    - sort: Sort output
    - awk/sed: Text processing
    - file: Identify file types
    - tree: Show directory structure
    - And any other Unix command

    Args:
        command: Unix command to execute (e.g., "find . -name '*.json' | head -10")
        tool_context: Execution context

    Returns:
        JSON string with command output and metadata

    Examples:
        # Find all JSON files
        execute_unix_command("find . -name '*.json'")

        # Search for specific content
        execute_unix_command("grep -r 'OrderProcessing' --include='*.json' .")

        # Show directory structure
        execute_unix_command("find . -type d | head -20")

        # Count entity versions
        execute_unix_command("find . -path '*/entity/*/version_*' -type d | wc -l")

        # List workflow files with details
        execute_unix_command("find . -path '*/workflow*' -name '*.json' -exec ls -la {} \\;")

        # Search for version patterns
        execute_unix_command("find . -name 'version_*' -type d | sort")

        # Get file types
        execute_unix_command("find . -name '*.json' -exec file {} \\; | head -5")
    """
    try:
        if not tool_context:
            return json.dumps({"error": "Tool context not available"})

        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return json.dumps({"error": "Repository path not found in context"})

        repo_path = Path(repository_path)
        if not repo_path.exists():
            return json.dumps({"error": f"Repository path does not exist: {repository_path}"})

        import subprocess
        import asyncio
        import shlex

        # Parse command for later use
        try:
            command_parts = shlex.split(command)
        except ValueError:
            command_parts = []

        # Enhanced Security: Comprehensive command validation
        security_result = await _validate_command_security(command, str(repo_path))
        if not security_result["safe"]:
            return json.dumps({
                "error": security_result["reason"],
                "command": command,
                "allowed_commands": [
                    "find", "grep", "ls", "cat", "head", "tail", "wc", "sort", "uniq",
                    "cut", "awk", "sed", "file", "tree", "du", "stat", "basename", "dirname"
                ],
                "security_note": "Only read-only operations within repository directory are allowed"
            })

        logger.info(f"🔧 Executing Unix command: {command}")

        # Execute command in repository directory
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(repo_path)
        )

        stdout, stderr = await process.communicate()

        # Prepare results
        result = {
            "command": command,
            "repository_path": str(repository_path),
            "exit_code": process.returncode,
            "stdout": stdout.decode('utf-8', errors='replace') if stdout else "",
            "stderr": stderr.decode('utf-8', errors='replace') if stderr else "",
            "success": process.returncode == 0
        }

        # Add summary information
        if result["success"]:
            stdout_lines = result["stdout"].strip().split('\n') if result["stdout"].strip() else []
            result["summary"] = {
                "output_lines": len(stdout_lines),
                "has_output": bool(result["stdout"].strip()),
                "command_type": command_parts[0] if command_parts else "unknown"
            }
            logger.info(f"✅ Command executed successfully: {len(stdout_lines)} lines of output")
        else:
            result["summary"] = {
                "error": True,
                "stderr_lines": len(result["stderr"].strip().split('\n')) if result["stderr"].strip() else 0
            }
            logger.warning(f"⚠️ Command failed with exit code {process.returncode}")

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error executing Unix command '{command}': {e}", exc_info=True)
        return json.dumps({
            "error": str(e),
            "command": command
        })


async def get_requirements_path(requirements_name: str, project_type: str) -> str:
    """
    Get the correct path for a functional requirements file.

    Args:
        requirements_name: Name of the requirements file (e.g., "order_management", "user_authentication")
        project_type: "python" or "java"

    Returns:
        Correct path for the requirements file

    Examples:
        get_requirements_path("order_management", "python") -> "application/resources/functional_requirements/order_management.md"
        get_requirements_path("user_auth", "java") -> "src/main/resources/functional_requirements/user_auth.md"
    """
    if project_type == "python":
        return f"{PYTHON_RESOURCES_PATH}/functional_requirements/{requirements_name}.md"
    elif project_type == "java":
        return f"{JAVA_RESOURCES_PATH}/functional_requirements/{requirements_name}.md"
    else:
        raise ValueError(f"Unsupported project type: {project_type}")


async def analyze_repository_structure_agentic(tool_context: ToolContext) -> str:
    """
    Agentic repository analysis using Unix commands.

    This function demonstrates how to use execute_unix_command for intelligent
    repository analysis. The AI can use this as a template and create its own
    custom analysis commands.

    Args:
        tool_context: Execution context

    Returns:
        JSON string with comprehensive repository analysis
    """
    try:
        if not tool_context:
            return json.dumps({"error": "Tool context not available"})

        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return json.dumps({"error": "Repository path not found in context"})

        logger.info("🤖 Starting agentic repository analysis using Unix commands...")

        # Use Unix commands to analyze the repository
        analysis_results = {
            "analysis_type": "agentic_unix_based",
            "repository_path": repository_path,
            "commands_executed": [],
            "entities": [],
            "workflows": [],
            "requirements": [],
            "structure": {},
            "summary": {}
        }

        # 1. Find all JSON files (entities and workflows)
        json_files_result = await execute_unix_command(
            "find . -name '*.json' -type f | sort",
            tool_context
        )
        json_data = json.loads(json_files_result)
        analysis_results["commands_executed"].append({
            "command": "find . -name '*.json' -type f | sort",
            "purpose": "Find all JSON files",
            "success": json_data.get("success", False)
        })

        if json_data.get("success"):
            json_files = [f.strip() for f in json_data["stdout"].split('\n') if f.strip()]

            # 2. Analyze entity files
            entity_files = [f for f in json_files if '/entity/' in f]
            for entity_file in entity_files:
                # Extract entity info from path
                path_parts = entity_file.split('/')
                if 'entity' in path_parts:
                    entity_idx = path_parts.index('entity')
                    if entity_idx + 1 < len(path_parts):
                        entity_name = path_parts[entity_idx + 1]
                        version = None
                        if entity_idx + 2 < len(path_parts) and path_parts[entity_idx + 2].startswith('version_'):
                            version = path_parts[entity_idx + 2]

                        # Read entity content
                        cat_result = await execute_unix_command(f"cat '{entity_file}'", tool_context)
                        cat_data = json.loads(cat_result)

                        if cat_data.get("success"):
                            try:
                                entity_content = json.loads(cat_data["stdout"])
                                analysis_results["entities"].append({
                                    "name": entity_name,
                                    "version": version,
                                    "path": entity_file,
                                    "content": entity_content
                                })
                            except json.JSONDecodeError:
                                logger.warning(f"Invalid JSON in entity file: {entity_file}")

            # 3. Analyze workflow files
            workflow_files = [f for f in json_files if '/workflow' in f]
            for workflow_file in workflow_files:
                # Extract workflow info from path
                path_parts = workflow_file.split('/')
                workflow_name = Path(workflow_file).stem
                version = None

                if 'version_' in workflow_file:
                    for part in path_parts:
                        if part.startswith('version_'):
                            version = part
                            break

                # Read workflow content
                cat_result = await execute_unix_command(f"cat '{workflow_file}'", tool_context)
                cat_data = json.loads(cat_result)

                if cat_data.get("success"):
                    try:
                        workflow_content = json.loads(cat_data["stdout"])
                        analysis_results["workflows"].append({
                            "name": workflow_name,
                            "version": version,
                            "path": workflow_file,
                            "content": workflow_content
                        })
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in workflow file: {workflow_file}")

        # 4. Find requirements files
        req_files_result = await execute_unix_command(
            "find . -name '*.md' -path '*/functional_requirements/*' | sort",
            tool_context
        )
        req_data = json.loads(req_files_result)
        analysis_results["commands_executed"].append({
            "command": "find . -name '*.md' -path '*/functional_requirements/*' | sort",
            "purpose": "Find requirements files",
            "success": req_data.get("success", False)
        })

        if req_data.get("success"):
            req_files = [f.strip() for f in req_data["stdout"].split('\n') if f.strip()]
            for req_file in req_files:
                req_name = Path(req_file).stem

                # Read requirements content
                cat_result = await execute_unix_command(f"cat '{req_file}'", tool_context)
                cat_data = json.loads(cat_result)

                if cat_data.get("success"):
                    analysis_results["requirements"].append({
                        "name": req_name,
                        "path": req_file,
                        "content": cat_data["stdout"]
                    })

        # 5. Generate structure overview
        structure_result = await execute_unix_command(
            "find . -type d | grep -E '(entity|workflow|functional_requirements)' | sort",
            tool_context
        )
        struct_data = json.loads(structure_result)
        analysis_results["commands_executed"].append({
            "command": "find . -type d | grep -E '(entity|workflow|functional_requirements)' | sort",
            "purpose": "Analyze directory structure",
            "success": struct_data.get("success", False)
        })

        if struct_data.get("success"):
            directories = [d.strip() for d in struct_data["stdout"].split('\n') if d.strip()]
            analysis_results["structure"]["directories"] = directories

        # Generate summary
        unique_entities = set()
        unique_workflows = set()
        for entity in analysis_results["entities"]:
            unique_entities.add(entity["name"])
        for workflow in analysis_results["workflows"]:
            unique_workflows.add(workflow["name"])

        analysis_results["summary"] = {
            "unique_entities": len(unique_entities),
            "total_entity_versions": len(analysis_results["entities"]),
            "unique_workflows": len(unique_workflows),
            "total_workflow_versions": len(analysis_results["workflows"]),
            "requirements_files": len(analysis_results["requirements"]),
            "commands_executed": len(analysis_results["commands_executed"])
        }

        logger.info(f"🤖 Agentic analysis complete: {len(unique_entities)} entities, {len(unique_workflows)} workflows, {len(analysis_results['requirements'])} requirements")

        return json.dumps(analysis_results, indent=2)

    except Exception as e:
        logger.error(f"Error in agentic repository analysis: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


async def analyze_repository_structure(tool_context: ToolContext) -> str:
    """Analyze repository structure and return entities, workflows, and requirements.

    Auto-detects Python vs Java project and returns structured JSON with:
    - Project type (python/java)
    - List of entities with their JSON content
    - List of workflows with their JSON content
    - List of functional requirements (markdown files)

    Args:
        tool_context: The ADK tool context

    Returns:
        JSON string with repository structure
    """
    try:
        conversation_id = tool_context.state.get("conversation_id")
        if not conversation_id:
            return f"ERROR: conversation_id not found in context.{STOP_ON_ERROR}"

        # FIRST: Try to get repository info from tool_context.state (agent's thinking stream)
        # This is the most up-to-date source and avoids race conditions
        repository_name = tool_context.state.get("repository_name")
        repository_branch = tool_context.state.get("branch_name")
        repository_owner = tool_context.state.get("repository_owner")

        # FALLBACK: If not in context state, get from Conversation entity
        if not repository_name or not repository_branch:
            entity_service = get_entity_service()
            conversation_response = await entity_service.get_by_id(
                entity_id=conversation_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if not conversation_response:
                return f"ERROR: Conversation {conversation_id} not found.{STOP_ON_ERROR}"

            # Handle conversation data (can be dict or object)
            conversation_data = conversation_response.data
            if isinstance(conversation_data, dict):
                repository_name = repository_name or conversation_data.get('repository_name')
                repository_branch = repository_branch or conversation_data.get('repository_branch')
                repository_owner = repository_owner or conversation_data.get('repository_owner')
            else:
                repository_name = repository_name or getattr(conversation_data, 'repository_name', None)
                repository_branch = repository_branch or getattr(conversation_data, 'repository_branch', None)
                repository_owner = repository_owner or getattr(conversation_data, 'repository_owner', None)

        if not repository_name or not repository_branch:
            return f"ERROR: No repository configured for this conversation.{STOP_ON_ERROR}"

        # Get repository path from context (should be set by build agent)
        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return f"ERROR: repository_path not found in context. Repository must be cloned first.{STOP_ON_ERROR}"

        # Detect project type and paths
        try:
            paths = _detect_project_type(repository_path)
        except ValueError as e:
            return f"ERROR: {str(e)}"

        result: Dict[str, Any] = {
            "project_type": paths["type"],
            "repository": {
                "owner": repository_owner or "unknown",
                "name": repository_name,
                "branch": repository_branch,
            },
            "entities": [],
            "workflows": [],
            "requirements": [],
        }

        repo_path_obj = Path(repository_path)

        # Use generic scanner for entities and workflows
        logger.info("🔍 Starting comprehensive resource scan...")

        # Scan entities (supports all versions automatically) - run in thread pool
        entities_dir = repo_path_obj / paths["entities_path"]
        loop = asyncio.get_event_loop()
        result["entities"] = await loop.run_in_executor(
            None, _scan_versioned_resources, entities_dir, "entity", repo_path_obj
        )

        # Scan workflows (supports all versions automatically) - run in thread pool
        workflows_dir = repo_path_obj / paths["workflows_path"]
        result["workflows"] = await loop.run_in_executor(
            None, _scan_versioned_resources, workflows_dir, "workflow", repo_path_obj
        )

        # Parse functional requirements - run in thread pool
        requirements_dir = repo_path_obj / paths["requirements_path"]

        def _read_requirements():
            requirements = []
            if requirements_dir.exists():
                for req_file in requirements_dir.glob("*.md"):
                    try:
                        with open(req_file, "r") as f:
                            content = f.read()
                        requirements.append(
                            {
                                "name": req_file.stem,
                                "path": str(req_file.relative_to(repo_path_obj)),
                                "content": content,
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to read requirement {req_file}: {e}")
            return requirements

        result["requirements"] = await loop.run_in_executor(None, _read_requirements)

        # Count unique resources and total versions
        def count_resources(resources, resource_type):
            unique_resources = set()
            resource_versions = {}
            for resource in resources:
                resource_name = resource['name']
                unique_resources.add(resource_name)
                if resource_name not in resource_versions:
                    resource_versions[resource_name] = []
                version = resource['version'] or 'direct'
                resource_versions[resource_name].append(version)
            return unique_resources, resource_versions

        unique_entities, entity_versions = count_resources(result['entities'], 'entity')
        unique_workflows, workflow_versions = count_resources(result['workflows'], 'workflow')

        logger.info(
            f"✅ Repository analysis complete: "
            f"{len(unique_entities)} unique entities ({len(result['entities'])} total versions), "
            f"{len(unique_workflows)} unique workflows ({len(result['workflows'])} total versions), "
            f"{len(result['requirements'])} requirements"
        )

        # Log detailed version information
        if entity_versions:
            logger.info("📋 Entity versions found:")
            for entity_name, versions in sorted(entity_versions.items()):
                clean_versions = [v for v in versions if v != 'direct']
                direct_files = [v for v in versions if v == 'direct']
                version_info = []
                if clean_versions:
                    version_info.extend(sorted(clean_versions))
                if direct_files:
                    version_info.append('(direct file)')
                logger.info(f"   - {entity_name}: {', '.join(version_info)}")
        else:
            logger.info("📋 No entities found in repository")

        if workflow_versions:
            logger.info("📋 Workflow versions found:")
            for workflow_name, versions in sorted(workflow_versions.items()):
                clean_versions = [v for v in versions if v != 'direct']
                direct_files = [v for v in versions if v == 'direct']
                version_info = []
                if clean_versions:
                    version_info.extend(sorted(clean_versions))
                if direct_files:
                    version_info.append('(direct file)')
                logger.info(f"   - {workflow_name}: {', '.join(version_info)}")
        else:
            logger.info("📋 No workflows found in repository")

        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Error analyzing repository structure: {e}", exc_info=True)
        return f"ERROR: {str(e)}"


async def save_file_to_repository(
    file_path: str, content: str, tool_context: ToolContext
) -> str:
    """Save a file to the repository (no path restrictions).

    Args:
        file_path: Relative path from repository root (e.g., "application/entity/order/version_1/order.json")
        content: File content to save
        tool_context: The ADK tool context

    Returns:
        Success or error message with canvas tab hook if applicable
    """
    try:
        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return f"ERROR: repository_path not found in context. Repository must be cloned first.{STOP_ON_ERROR}"

        # Construct full path
        full_path = Path(repository_path) / file_path

        # Create parent directories and write file (run in thread pool for async)
        def _write_file():
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, "w") as f:
                f.write(content)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_file)

        logger.info(f"Saved file: {file_path}")

        # Detect resource type from file path and create appropriate canvas hook
        from application.agents.shared.hook_utils import (
            create_open_canvas_tab_hook,
            wrap_response_with_hook,
        )

        file_lower = file_path.lower()
        tab_name = None

        # Detect resource type from file path
        if "/entity/" in file_lower:
            tab_name = "entities"
        elif "/workflow/" in file_lower:
            tab_name = "workflows"
        elif "requirement" in file_lower:
            tab_name = "requirements"

        # If we detected a canvas resource, create and return hook
        if tab_name:
            conversation_id = tool_context.state.get("conversation_id")
            if conversation_id:
                hook = create_open_canvas_tab_hook(
                    conversation_id=conversation_id,
                    tab_name=tab_name,
                )

                # Store hook in context for SSE streaming
                tool_context.state["last_tool_hook"] = hook

                message = f"✅ File saved to {file_path}\n\n📂 Opening Canvas {tab_name.title()} tab to view your changes."
                return wrap_response_with_hook(message, hook)

        return f"SUCCESS: File saved to {file_path}"

    except Exception as e:
        logger.error(f"Error saving file {file_path}: {e}", exc_info=True)
        return f"ERROR: {str(e)}{STOP_ON_ERROR}"


@creates_hook("code_changes")
async def commit_and_push_changes(
    commit_message: str, tool_context: ToolContext
) -> str:
    """Commit and push all changes to the conversation's repository branch.

    Args:
        commit_message: Commit message describing the changes
        tool_context: The ADK tool context

    Returns:
        Success or error message with optional canvas analysis hook
    """
    try:
        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return f"ERROR: repository_path not found in context. Repository must be cloned first.{STOP_ON_ERROR}"

        conversation_id = tool_context.state.get("conversation_id")
        if not conversation_id:
            return f"ERROR: conversation_id not found in context.{STOP_ON_ERROR}"

        # FIRST: Try to get branch and repository from tool_context.state (agent's thinking stream)
        # This is the most up-to-date source and avoids race conditions
        branch_name = tool_context.state.get("branch_name")
        repository_name = tool_context.state.get("repository_name")
        repository_owner = tool_context.state.get("repository_owner")

        # FALLBACK: If not in context state, get from Conversation entity
        # This handles cases where the tool is called in a new session
        if not branch_name or not repository_name:
            entity_service = get_entity_service()
            conversation_response = await entity_service.get_by_id(
                entity_id=conversation_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if not conversation_response:
                return f"ERROR: Conversation {conversation_id} not found.{STOP_ON_ERROR}"

            # Handle conversation data (can be dict or object)
            conversation_data = conversation_response.data
            if isinstance(conversation_data, dict):
                branch_name = branch_name or conversation_data.get('repository_branch')
                repository_name = repository_name or conversation_data.get('repository_name')
                repository_owner = repository_owner or conversation_data.get('repository_owner')
            else:
                branch_name = branch_name or getattr(conversation_data, 'repository_branch', None)
                repository_name = repository_name or getattr(conversation_data, 'repository_name', None)
                repository_owner = repository_owner or getattr(conversation_data, 'repository_owner', None)

        if not branch_name:
            return f"ERROR: No branch configured for this conversation.{STOP_ON_ERROR}"
        if not repository_name:
            return f"ERROR: No repository configured for this conversation.{STOP_ON_ERROR}"

        # Get GitHub service
        github_service = await _get_github_service_from_context(tool_context)

        # Use direct git operations with the actual repository path
        import subprocess
        import asyncio

        # Change to repository directory
        original_cwd = os.getcwd()
        changed_files = []
        try:
            os.chdir(repository_path)

            # Get list of changed files before committing
            status_process = await asyncio.create_subprocess_exec(
                'git', 'status', '--porcelain',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            status_stdout, _ = await status_process.communicate()

            if status_process.returncode == 0:
                # Parse git status output to get changed files
                for line in status_stdout.decode().splitlines():
                    if len(line) > 3:
                        # Format: "XY filename" where XY is status code
                        changed_files.append(line[3:].strip())

            # Add all changes
            add_process = await asyncio.create_subprocess_exec(
                'git', 'add', '.',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await add_process.communicate()

            if add_process.returncode != 0:
                logger.error(f"Git add failed: {stderr.decode()}")
                return f"ERROR: Failed to add files: {stderr.decode()}{STOP_ON_ERROR}"

            # Commit changes
            commit_process = await asyncio.create_subprocess_exec(
                'git', 'commit', '-m', commit_message,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await commit_process.communicate()

            if commit_process.returncode != 0:
                # Check if it's just "nothing to commit" (message can be in stdout OR stderr)
                combined_output = (stdout.decode() + stderr.decode()).lower()
                if "nothing to commit" in combined_output or "working tree clean" in combined_output:
                    logger.info("No changes to commit - working tree is clean")
                    return "SUCCESS: No changes to commit. The file was already saved and committed previously. Task complete - STOP, do not call any more tools."
                else:
                    logger.error(f"Git commit failed: stdout={stdout.decode()}, stderr={stderr.decode()}")
                    return f"ERROR: Failed to commit: {stderr.decode() or stdout.decode()}{STOP_ON_ERROR}"

            # Update remote URL with fresh authentication token before pushing
            # This is critical because GitHub App tokens expire after 1 hour
            repository_type = tool_context.state.get("repository_type")
            user_repository_url = tool_context.state.get("user_repository_url")
            installation_id = tool_context.state.get("installation_id")
            language = tool_context.state.get("language", "python")

            if repository_type in ["public", "private"]:
                # Determine the repository URL to use
                if repository_type == "private" and user_repository_url and installation_id:
                    repo_url_to_use = user_repository_url
                    installation_id_to_use = installation_id
                    logger.info(f"🔐 Refreshing authentication for private repository: {repo_url_to_use}")
                elif repository_type == "public":
                    # For public repos, use the configured public repository URL from .env
                    from common.config.config import PYTHON_PUBLIC_REPO_URL, JAVA_PUBLIC_REPO_URL, GITHUB_PUBLIC_REPO_INSTALLATION_ID
                    if language.lower() == "python":
                        repo_url_to_use = PYTHON_PUBLIC_REPO_URL
                    elif language.lower() == "java":
                        repo_url_to_use = JAVA_PUBLIC_REPO_URL
                    else:
                        repo_url_to_use = None
                    installation_id_to_use = GITHUB_PUBLIC_REPO_INSTALLATION_ID
                    logger.info(f"🔐 Refreshing authentication for public repository: {repo_url_to_use}")
                else:
                    repo_url_to_use = None
                    installation_id_to_use = None

                # Update the remote URL with fresh authentication
                if repo_url_to_use and installation_id_to_use:
                    try:
                        from application.agents.shared.repository_tools import _get_authenticated_repo_url_sync
                        authenticated_url = await _get_authenticated_repo_url_sync(repo_url_to_use, installation_id_to_use)

                        # Update the origin remote URL
                        set_url_process = await asyncio.create_subprocess_exec(
                            "git",
                            "remote",
                            "set-url",
                            "origin",
                            authenticated_url,
                            cwd=repository_path,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                        stdout, stderr = await set_url_process.communicate()

                        if set_url_process.returncode != 0:
                            error_msg = stderr.decode("utf-8") if stderr else "Unknown error"
                            logger.warning(f"⚠️ Failed to update remote URL: {error_msg}")
                        else:
                            logger.info(f"✅ Successfully refreshed remote authentication")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to refresh authentication: {e}")

            # Push changes
            push_process = await asyncio.create_subprocess_exec(
                'git', 'push', 'origin', branch_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await push_process.communicate()

            if push_process.returncode != 0:
                logger.error(f"Git push failed: {stderr.decode()}")
                return f"ERROR: Failed to push: {stderr.decode()}{STOP_ON_ERROR}"

        finally:
            os.chdir(original_cwd)

        logger.info(
            f"Committed and pushed changes to branch {branch_name}: {commit_message}"
        )

        # Detect if canvas-relevant resources were changed
        from application.agents.shared.hook_utils import (
            create_code_changes_hook,
            detect_canvas_resources,
            wrap_response_with_hook,
        )

        canvas_resources = detect_canvas_resources(changed_files)

        if canvas_resources and changed_files:
            # Create code changes hook for UI
            hook = create_code_changes_hook(
                conversation_id=conversation_id,
                repository_name=repository_name,
                branch_name=branch_name,
                changed_files=changed_files,
                commit_message=commit_message,
                resources=canvas_resources,
                repository_owner=repository_owner,
            )

            # Store hook in context for SSE streaming
            tool_context.state["last_tool_hook"] = hook

            # Return response with hook
            message = f"✅ Changes committed and pushed to branch {branch_name}\n\n📊 Canvas resources updated - click 'Open Canvas' to view changes."
            return wrap_response_with_hook(message, hook)
        else:
            return f"SUCCESS: Changes committed and pushed to branch {branch_name}"

    except Exception as e:
        logger.error(f"Error committing and pushing changes: {e}", exc_info=True)
        return f"ERROR: {str(e)}"


async def pull_repository_changes(tool_context: ToolContext) -> str:
    """Pull latest changes from the remote repository.

    Fetches and merges the latest changes from the remote branch into the local repository.
    This is useful for syncing with changes made by other developers or through the GitHub UI.

    Args:
        tool_context: The ADK tool context

    Returns:
        Success message with pulled changes summary, or error message
    """
    import subprocess
    import asyncio

    try:
        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return f"ERROR: repository_path not found in context. Repository must be cloned first.{STOP_ON_ERROR}"

        # Get conversation to get branch info
        conversation_id = tool_context.state.get("conversation_id")
        if not conversation_id:
            return f"ERROR: conversation_id not found in context.{STOP_ON_ERROR}"

        # FIRST: Try to get branch from tool_context.state (agent's thinking stream)
        # This is the most up-to-date source and avoids race conditions
        branch_name = tool_context.state.get("branch_name")

        # FALLBACK: If not in context state, get from Conversation entity
        if not branch_name:
            entity_service = get_entity_service()
            conversation_response = await entity_service.get_by_id(
                entity_id=conversation_id,
                entity_class=Conversation.ENTITY_NAME,
                entity_version=str(Conversation.ENTITY_VERSION),
            )

            if not conversation_response:
                return f"ERROR: Conversation {conversation_id} not found.{STOP_ON_ERROR}"

            # Extract branch name
            conversation_data = conversation_response.data
            if isinstance(conversation_data, dict):
                branch_name = conversation_data.get('repository_branch')
            else:
                branch_name = getattr(conversation_data, 'repository_branch', None)

        if not branch_name:
            return f"ERROR: No branch configured for this conversation.{STOP_ON_ERROR}"

        logger.info(f"🔄 Pulling changes from origin/{branch_name} in {repository_path}")

        # Execute git pull using subprocess directly (not execute_unix_command which is read-only)
        process = await asyncio.create_subprocess_exec(
            "git", "pull", "origin", branch_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repository_path
        )

        stdout, stderr = await process.communicate()
        stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
        stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""

        if process.returncode != 0:
            logger.error(f"❌ Git pull failed: {stderr_text}")
            return f"ERROR: Failed to pull changes: {stderr_text}"

        # Check if already up to date
        if "Already up to date" in stdout_text or "Already up-to-date" in stdout_text:
            logger.info("✅ Repository already up to date")
            return "✅ Repository is already up to date. No changes to pull."

        logger.info(f"✅ Successfully pulled changes:\n{stdout_text}")
        return f"✅ Successfully pulled changes from remote repository.\n\n{stdout_text}"

    except Exception as e:
        logger.error(f"Error pulling repository changes: {e}", exc_info=True)
        return f"ERROR: {str(e)}"


async def get_repository_diff(tool_context: ToolContext) -> str:
    """Get diff of uncommitted changes in the repository.

    Returns a summary of what files have been modified, added, or deleted
    since the last commit.

    Args:
        tool_context: The ADK tool context

    Returns:
        JSON string with diff information
    """
    try:
        repository_path = tool_context.state.get("repository_path")
        if not repository_path:
            return "ERROR: repository_path not found in context. Repository must be cloned first."

        # Use git to get status
        import subprocess

        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository_path,
            capture_output=True,
            text=True,
            check=True,
        )

        changes: Dict[str, List[str]] = {
            "modified": [],
            "added": [],
            "deleted": [],
            "untracked": [],
        }

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            status = line[:2]
            file_path = line[3:]

            if status.strip() == "M":
                changes["modified"].append(file_path)
            elif status.strip() == "A":
                changes["added"].append(file_path)
            elif status.strip() == "D":
                changes["deleted"].append(file_path)
            elif status.strip() == "??":
                changes["untracked"].append(file_path)

        total_changes = sum(len(v) for v in changes.values())
        logger.info(f"Repository has {total_changes} uncommitted changes")

        return json.dumps(changes, indent=2)

    except Exception as e:
        logger.error(f"Error getting repository diff: {e}", exc_info=True)
        return f"ERROR: {str(e)}"


async def _commit_and_push_changes(
    repository_path: str, branch_name: str
) -> Dict[str, Any]:
    """
    Commit and push all changes in the repository.
    Logs all files and GitHub status.
    Internal helper for monitoring tasks.

    Args:
        repository_path: Path to repository
        branch_name: Branch name

    Returns:
        Dict with status and message
    """
    try:
        repo_path = Path(repository_path)

        # Get list of all files in repository before staging
        logger.info(f"📁 Repository contents in {repository_path}:")
        all_files = []
        for root, dirs, files in os.walk(repo_path):
            # Skip .git and other hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.'):
                    file_path = os.path.relpath(os.path.join(root, file), repo_path)
                    all_files.append(file_path)
                    logger.info(f"  📄 {file_path}")

        logger.info(f"📊 Total files in repository: {len(all_files)}")

        # Get git status before staging
        status_process = await asyncio.create_subprocess_exec(
            "git", "status", "--porcelain",
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        status_stdout, status_stderr = await status_process.communicate()
        status_output = status_stdout.decode('utf-8', errors='replace')

        if status_output:
            logger.info(f"📝 Git status (changes to commit):")
            for line in status_output.strip().split('\n'):
                if line:
                    logger.info(f"  {line}")
        else:
            logger.info("✅ No changes to commit")

        # Stage all changes
        process = await asyncio.create_subprocess_exec(
            "git", "add", ".",
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()

        # Commit changes
        commit_msg = f"Code generation progress on {branch_name}"
        process = await asyncio.create_subprocess_exec(
            "git", "commit", "-m", commit_msg,
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        commit_stdout, commit_stderr = await process.communicate()
        commit_output = commit_stdout.decode('utf-8', errors='replace')

        if process.returncode == 0:
            logger.info(f"✅ Commit successful: {commit_output.strip()}")
        else:
            logger.info(f"ℹ️ No changes to commit (exit code: {process.returncode})")

        # Push changes with -u flag to create branch on remote if needed
        logger.info(f"🚀 Pushing to origin/{branch_name}...")
        process = await asyncio.create_subprocess_exec(
            "git", "push", "-u", "origin", branch_name,
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        push_stdout, push_stderr = await process.communicate()
        push_output = push_stdout.decode('utf-8', errors='replace')
        push_error = push_stderr.decode('utf-8', errors='replace')

        if process.returncode == 0:
            logger.info(f"✅ Push successful to origin/{branch_name}")
            logger.info(f"📤 Push output: {push_output.strip()}")

            # Log GitHub status
            logger.info(f"🔗 GitHub branch: origin/{branch_name}")
            logger.info(f"📊 Files pushed: {len(all_files)}")

            return {"status": "success", "message": "Changes committed and pushed"}
        else:
            logger.error(f"❌ Push failed: {push_error}")
            return {"status": "error", "message": f"Push failed: {push_error}"}

    except Exception as e:
        logger.error(f"❌ Failed to commit/push: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


async def _stream_process_output(
    process: Any,
    task_id: Optional[str] = None,
) -> None:
    """
    Stream process output chunks as they arrive.
    Reads from stdout and stderr, updates BackgroundTask with output.

    Args:
        process: The asyncio subprocess
        task_id: BackgroundTask ID for storing output
    """
    try:
        from services.services import get_task_service

        task_service = get_task_service()
        accumulated_output = []
        chunk_size = 1024  # Read 1KB at a time
        last_update_time = asyncio.get_event_loop().time()
        update_interval = 2  # Update every 2 seconds or 5KB

        while True:
            try:
                # Read from stdout with timeout
                chunk = await asyncio.wait_for(
                    process.stdout.read(chunk_size),
                    timeout=0.5
                )
                if chunk:
                    output_str = chunk.decode('utf-8', errors='replace')
                    accumulated_output.append(output_str)
                    logger.debug(f"📤 Output chunk: {output_str[:100]}...")

                    current_time = asyncio.get_event_loop().time()
                    accumulated_size = sum(len(s) for s in accumulated_output)

                    # Update task with accumulated output every 5KB or every 2 seconds
                    if (accumulated_size > 5120 or (current_time - last_update_time) > update_interval) and task_id:
                        try:
                            full_output = ''.join(accumulated_output)
                            # Get current task to preserve existing metadata
                            current_task = await task_service.get_task(task_id)
                            existing_metadata = current_task.metadata if current_task else {}

                            # Merge existing metadata with new output
                            updated_metadata = {**existing_metadata, "output": full_output[-10000:]}  # Keep last 10KB

                            await task_service.update_task_status(
                                task_id=task_id,
                                metadata=updated_metadata,
                            )
                            logger.info(f"📤 Updated task {task_id} with {accumulated_size} bytes of output")
                            accumulated_output = []
                            last_update_time = current_time
                        except Exception as e:
                            logger.debug(f"Could not update task output: {e}")
                else:
                    # EOF reached
                    break
            except asyncio.TimeoutError:
                # No data available, check if we should update anyway
                current_time = asyncio.get_event_loop().time()
                if accumulated_output and (current_time - last_update_time) > update_interval and task_id:
                    try:
                        full_output = ''.join(accumulated_output)
                        current_task = await task_service.get_task(task_id)
                        existing_metadata = current_task.metadata if current_task else {}
                        updated_metadata = {**existing_metadata, "output": full_output[-10000:]}
                        await task_service.update_task_status(
                            task_id=task_id,
                            metadata=updated_metadata,
                        )
                        logger.debug(f"📤 Periodic output update: {len(full_output)} characters")
                        accumulated_output = []
                        last_update_time = current_time
                    except Exception as e:
                        logger.debug(f"Could not update task output: {e}")
            except Exception as e:
                logger.debug(f"Error reading stdout: {e}")
                break

        # Update task with any remaining output when process completes
        if accumulated_output and task_id:
            try:
                full_output = ''.join(accumulated_output)
                # Get current task to preserve existing metadata
                current_task = await task_service.get_task(task_id)
                existing_metadata = current_task.metadata if current_task else {}

                # Merge existing metadata with final output
                updated_metadata = {**existing_metadata, "output": full_output[-10000:]}  # Keep last 10KB

                await task_service.update_task_status(
                    task_id=task_id,
                    metadata=updated_metadata,
                )
                logger.info(f"📤 Final output update: {len(full_output)} characters")
            except Exception as e:
                logger.debug(f"Could not update final task output: {e}")

    except Exception as e:
        logger.warning(f"Error streaming process output: {e}")


async def _monitor_code_generation_process(
    process: Any,
    repository_path: str,
    branch_name: str,
    user_request: str,
    timeout_seconds: int = 3600,
    tool_context: Optional[ToolContext] = None,
) -> None:
    """
    Monitor code generation process with periodic checks and git commits.
    Updates BackgroundTask entity every 30 seconds with progress.
    Streams output chunks as they arrive.

    Args:
        process: The asyncio subprocess
        repository_path: Path to repository
        branch_name: Branch name
        user_request: User's code generation request
        timeout_seconds: Maximum time to wait (default: 1 hour)
        tool_context: Tool context with task_id
    """
    pid = process.pid
    start_time = asyncio.get_event_loop().time()
    elapsed_time = 0
    check_interval = 10  # Check every 10 seconds

    logger.info(f"🔍 [{branch_name}] Monitoring code generation task started for PID {pid}")
    logger.info(f"🔍 [{branch_name}] User request: {user_request[:100]}...")

    # Get task_id from context
    task_id = tool_context.state.get("background_task_id") if tool_context else None
    logger.info(f"🔍 [{branch_name}] background_task_id: {task_id}")

    # Start streaming output in background
    output_stream_task = asyncio.create_task(
        _stream_process_output(process=process, task_id=task_id)
    )
    logger.info(f"📤 Started output streaming for PID {pid}")

    # Send initial commit immediately when process starts
    if tool_context:
        try:
            logger.info(f"🔍 [{branch_name}] Sending initial commit...")
            commit_result = await _commit_and_push_changes(
                repository_path=repository_path,
                branch_name=branch_name,
            )
            logger.info(f"🔍 [{branch_name}] Initial commit result: {commit_result.get('status', 'unknown')}")
            logger.info(f"✅ [{branch_name}] Initial commit completed - progress tracked in BackgroundTask")
        except Exception as e:
            logger.error(f"❌ [{branch_name}] Failed to send initial commit: {e}", exc_info=True)

    while elapsed_time < timeout_seconds:
        try:
            # Wait for process to complete or timeout
            remaining_time = min(check_interval, timeout_seconds - elapsed_time)
            await asyncio.wait_for(process.wait(), timeout=remaining_time)

            # Process completed normally
            logger.info(f"✅ Process {pid} completed normally")

            # Update BackgroundTask to completed
            if task_id:
                try:
                    from services.services import get_task_service

                    task_service = get_task_service()

                    # Get diff to show what was generated
                    changed_files = []
                    if tool_context:
                        try:
                            diff_result = await get_repository_diff(tool_context)
                            diff_data = json.loads(diff_result)
                            for category in ["modified", "added", "untracked"]:
                                changed_files.extend(diff_data.get(category, []))
                        except Exception as e:
                            logger.warning(f"Could not get diff: {e}")

                    files_summary = f"{len(changed_files)} files changed" if changed_files else "No files changed"

                    # Get current task to preserve existing metadata (especially CLI output)
                    current_task = await task_service.get_task(task_id)
                    existing_metadata = current_task.metadata if current_task else {}

                    # Merge existing metadata with new changed_files
                    updated_metadata = {**existing_metadata, "changed_files": changed_files[:20]}

                    await task_service.update_task_status(
                        task_id=task_id,
                        status="completed",
                        message=f"Code generation completed - {files_summary}",
                        progress=100,
                        metadata=updated_metadata,
                    )
                    logger.info(f"✅ Updated BackgroundTask {task_id} to completed")

                    # Commit final changes
                    try:
                        await _commit_and_push_changes(
                            repository_path=repository_path,
                            branch_name=branch_name,
                        )
                        logger.info(f"✅ [{branch_name}] Final commit completed")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to commit final changes: {e}")

                except Exception as e:
                    logger.warning(f"⚠️ Failed to update BackgroundTask: {e}")

            logger.info("✅ Code generation completed - status tracked in BackgroundTask entity")
            return

        except asyncio.TimeoutError:
            # Check if process is still running
            try:
                os.kill(pid, 0)  # Signal 0 checks if process exists
                # Process is still running
                elapsed_time += remaining_time
                logger.debug(f"🔍 Process {pid} still running after {elapsed_time}s")

                # Update BackgroundTask every 30 seconds
                if task_id and elapsed_time % 30 == 0:
                    try:
                        from services.services import get_task_service

                        task_service = get_task_service()
                        progress = min(95, int((elapsed_time / timeout_seconds) * 100))

                        await task_service.update_task_status(
                            task_id=task_id,
                            status="running",
                            message=f"Code generation in progress... ({int(elapsed_time)}s elapsed)",
                            progress=progress,
                            metadata={"elapsed_time": int(elapsed_time), "pid": pid},
                        )
                        logger.info(f"📊 Updated BackgroundTask {task_id} progress: {progress}%")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to update BackgroundTask progress: {e}")

                # Commit and push changes every 60 seconds
                if tool_context and elapsed_time % 60 == 0:
                    try:
                        commit_result = await _commit_and_push_changes(
                            repository_path=repository_path,
                            branch_name=branch_name,
                        )
                        logger.info(f"✅ [{branch_name}] Progress commit completed")
                    except Exception as e:
                        logger.warning(f"⚠️ [{branch_name}] Failed to commit/push: {e}")

            except OSError:
                # Process has exited
                logger.info(f"✅ Process {pid} completed (detected during check)")

                # Update BackgroundTask to completed
                if task_id:
                    try:
                        from services.services import get_task_service

                        task_service = get_task_service()

                        # Get diff
                        changed_files = []
                        if tool_context:
                            try:
                                diff_result = await get_repository_diff(tool_context)
                                diff_data = json.loads(diff_result)
                                for category in ["modified", "added", "untracked"]:
                                    changed_files.extend(diff_data.get(category, []))
                            except Exception as e:
                                logger.warning(f"Could not get diff: {e}")

                        files_summary = f"{len(changed_files)} files changed" if changed_files else "No files changed"

                        await task_service.update_task_status(
                            task_id=task_id,
                            status="completed",
                            message=f"Code generation completed - {files_summary}",
                            progress=100,
                            metadata={"changed_files": changed_files[:20]},
                        )
                        logger.info(f"✅ Updated BackgroundTask {task_id} to completed")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to update BackgroundTask: {e}")

                logger.info("✅ Code generation completed")
                return

    # Timeout exceeded, terminate the process
    logger.error(f"⏰ Process exceeded {timeout_seconds} seconds, terminating... (PID: {pid})")

    # Update BackgroundTask to failed
    if task_id:
        try:
            from services.services import get_task_service

            task_service = get_task_service()
            await task_service.update_task_status(
                task_id=task_id,
                status="failed",
                message=f"Code generation timeout after {timeout_seconds} seconds",
                progress=0,
                error=f"Process exceeded {timeout_seconds} seconds timeout",
            )
            logger.info(f"❌ Updated BackgroundTask {task_id} to failed (timeout)")
        except Exception as e:
            logger.warning(f"⚠️ Failed to update BackgroundTask on timeout: {e}")

    # Terminate process
    try:
        process.terminate()
        await asyncio.sleep(5)
        if process.returncode is None:
            process.kill()
            await process.wait()
    except Exception as e:
        logger.error(f"Failed to terminate process: {e}")


async def _load_informational_prompt_template(language: str) -> str:
    """Load informational prompt template for CLI.

    These prompts are informational (for analysis/understanding) rather than
    action-based (for building). They help the CLI understand the codebase
    structure and patterns.

    Args:
        language: "python" or "java"

    Returns:
        Prompt template content or error message
    """
    try:
        # Try github_cli templates first for incremental changes
        template_name = f"github_cli_{language}_instructions"
        try:
            template_content = load_template(template_name)
            return template_content
        except FileNotFoundError:
            # Fallback to build agent templates
            template_name = f"build_{language}_instructions"
            template_content = load_template(template_name)
            return template_content

    except FileNotFoundError as e:
        logger.error(f"Prompt template not found: {e}")
        return f"ERROR: Prompt template not found: {str(e)}"
    except Exception as e:
        logger.error(f"Error loading prompt template: {e}", exc_info=True)
        return f"ERROR: Failed to load prompt template: {str(e)}"


@creates_hook("background_task")
@creates_hook("code_changes")
async def generate_code_with_cli(
    user_request: str,
    tool_context: Optional[ToolContext] = None,
    language: Optional[str] = None,
) -> str:
    """
    Generate code using CLI based on user request.

    This tool uses CLI to generate code (entities, workflows, processors, etc.)
    based on the user's natural language request. Unlike the build agent which creates
    entire applications, this tool is for incremental code generation in an existing
    repository.

    The prompts used are INFORMATIONAL - they help the CLI understand the codebase
    structure and patterns, then the CLI takes action based on the user's request.

    IMPORTANT: This tool modifies files in the repository. Do not run multiple
    instances concurrently on the same repository to avoid conflicts.

    Args:
        user_request: Natural language description of what code to generate
                     (e.g., "Add a Customer entity with id, name, email fields")
        tool_context: Execution context
        language: "python" or "java" (auto-detected if not provided)

    Returns:
        Success message or error

    Timeout:
        1 hour (same as augment_build.sh script)

    Examples:
        >>> await generate_code_with_cli(
        ...     "Add a Customer entity with id, name, email, and phone fields",
        ...     tool_context
        ... )
        "✅ Code generated successfully. Files created: application/entity/customer/..."

        >>> await generate_code_with_cli(
        ...     "Create a workflow for Order entity with create and update transitions",
        ...     tool_context,
        ...     language="python"
        ... )
        "✅ Workflow generated successfully. File: application/resources/workflow/order/..."
    """
    try:
        if not tool_context:
            return f"ERROR: Tool context not available.{STOP_ON_ERROR}"

        # Get repository info from context
        repository_path = tool_context.state.get("repository_path")
        branch_name = tool_context.state.get("branch_name")

        if not repository_path:
            return f"ERROR: Repository path not found in context. Please clone repository first using clone_repository().{STOP_ON_ERROR}"

        if not branch_name:
            return f"ERROR: Branch name not found in context. Please clone repository first using clone_repository().{STOP_ON_ERROR}"

        # Auto-detect language if not provided
        if not language:
            project_info = _detect_project_type(repository_path)
            language = project_info["type"]
            logger.info(f"Auto-detected project type: {language}")

        # Validate language
        if language not in ["python", "java"]:
            return f"ERROR: Unsupported language: {language}. Must be 'python' or 'java'."

        # Verify repository exists
        repo_path = Path(repository_path)
        if not repo_path.exists():
            return f"ERROR: Repository directory does not exist: {repository_path}"

        if not (repo_path / ".git").exists():
            return f"ERROR: Directory exists but is not a git repository: {repository_path}"

        logger.info(f"✅ Repository verified at: {repository_path}")

        # Check CLI invocation limit
        from application.services.streaming_service import check_cli_invocation_limit, get_cli_invocation_count
        session_id = tool_context.state.get("session_id", "unknown")
        is_allowed, error_msg = check_cli_invocation_limit(session_id)
        if not is_allowed:
            logger.error(error_msg)
            return f"ERROR: {error_msg}"

        cli_count = get_cli_invocation_count(session_id)
        logger.info(f"🔧 CLI invocation #{cli_count} for session {session_id}")

        # Load informational prompt template
        prompt_template = await _load_informational_prompt_template(language)
        if prompt_template.startswith("ERROR"):
            return prompt_template

        # Combine informational template with user request
        # The template is informational (describes patterns), user request is the action
        full_prompt = f"""{prompt_template}

## User Request (Action to Take):
{user_request}

## 🚨 CRITICAL INSTRUCTIONS:

1. **Implement ONLY what the user requested above** - Do not add extra features or components
2. **Consult the reference documentation above** to understand how to implement correctly
3. **Follow the established patterns** described in the reference when implementing
4. **Do not build complete applications** unless explicitly requested

**Scope Control Examples:**
- ✅ User requests: "Add a Customer entity" → Create ONLY: entity class + JSON entity definition
- ❌ User requests: "Add a Customer entity" → Do NOT create: processor, criterion, workflow, routes (unless requested)
- ✅ User requests: "Add a Customer entity with workflow" → Create: entity class + JSON definition + workflow JSON
- ✅ User requests: "Add validation to Customer" → Create ONLY: criterion or processor for validation

**ALWAYS create JSON entity definition when creating/modifying entities:**
- Python: `application/resources/entity/{{entity_name}}/version_1/{{EntityName}}.json`
- Java: `src/main/resources/entity/{{entity_name}}/version_1/{{EntityName}}.json`

Based on the codebase patterns and structure described above, please implement EXACTLY what the user requested.
Follow the established patterns, naming conventions, and project structure.
Ensure all generated code follows the guidelines and best practices outlined above.
"""

        # Check if CLI script exists
        script_path = Path(AUGGIE_CLI_SCRIPT)
        if not script_path.exists():
            return f"ERROR: CLI script not found at {AUGGIE_CLI_SCRIPT}"

        logger.info(f"🤖 Generating code with CLI in {repository_path}")
        logger.info(f"📝 User request: {user_request[:100]}...")

        # Get Augment model from config (must be haiku4.5)
        from common.config.config import AUGMENT_MODEL

        # Validate that only haiku4.5 is used for Augment CLI
        if AUGMENT_MODEL != "haiku4.5":
            logger.error(f"Invalid model for Augment CLI: {AUGMENT_MODEL}. Only haiku4.5 is supported.")
            return f"ERROR: Augment CLI only supports haiku4.5 model. Current model: {AUGMENT_MODEL}"

        # Call CLI script
        cmd = [
            "bash",
            str(script_path.absolute()),
            full_prompt,
            AUGMENT_MODEL,
            repository_path,
            branch_name,
        ]

        logger.info(f"🔧 Executing CLI")
        logger.info(f"🎯 Model: {AUGMENT_MODEL}")
        logger.info(f"📁 Workspace: {repository_path}")
        logger.info(f"🌿 Branch: {branch_name}")

        # Execute CLI
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(script_path.parent),
        )

        logger.info(f"Started CLI process {process.pid}")

        # Create BackgroundTask entity to track code generation progress
        task_id = None
        conversation_id = tool_context.state.get("conversation_id")

        try:
            from services.services import get_task_service

            task_service = get_task_service()
            user_id = tool_context.state.get("user_id", "unknown")
            repository_type = tool_context.state.get("repository_type", "public")

            # Construct GitHub repository URL
            repository_url = None
            if repository_type == "public":
                # Use public repository URL
                if language.lower() == "python":
                    repo_name = "mcp-cyoda-quart-app"
                elif language.lower() == "java":
                    repo_name = "java-client-template"
                else:
                    repo_name = "mcp-cyoda-quart-app"
                repo_owner = os.getenv("REPOSITORY_OWNER", "Cyoda-platform")
                repository_url = f"https://github.com/{repo_owner}/{repo_name}/tree/{branch_name}"

            # Create background task
            background_task = await task_service.create_task(
                user_id=user_id,
                task_type="code_generation",
                name=f"Generate code: {user_request[:50]}...",
                description=f"Generating code with CLI: {user_request[:200]}...",
                branch_name=branch_name,
                language=language,
                user_request=user_request,
                conversation_id=conversation_id,
                repository_path=repository_path,
                repository_type=repository_type,
                repository_url=repository_url,
            )

            task_id = background_task.technical_id
            logger.info(f"✅ Created BackgroundTask {task_id} for code generation")

            # Update task to running status
            await task_service.update_task_status(
                task_id=task_id,
                status="running",
                message=f"Code generation started (PID: {process.pid})",
                progress=5,
                process_pid=process.pid,
            )

            # Store task_id in context
            tool_context.state["background_task_id"] = task_id
            tool_context.state["code_gen_process_pid"] = process.pid

            # Add task to conversation's background_task_ids list
            if conversation_id:
                from application.agents.shared.repository_tools import _add_task_to_conversation
                await _add_task_to_conversation(conversation_id, task_id)

        except Exception as e:
            logger.error(f"Failed to create BackgroundTask: {e}", exc_info=True)
            # Continue anyway - task tracking is not critical for execution

        # Start monitoring in background (don't wait for completion)
        # The monitoring task will update the BackgroundTask entity with progress
        monitoring_task = asyncio.create_task(
            _monitor_code_generation_process(
                process=process,
                repository_path=repository_path,
                branch_name=branch_name,
                user_request=user_request,
                timeout_seconds=3600,  # 1 hour timeout
                tool_context=tool_context,
            )
        )

        # Add task to background tasks set to prevent garbage collection
        from typing import Set, Any
        background_tasks: Set[Any] = getattr(asyncio, '_background_tasks', set())
        if not hasattr(asyncio, '_background_tasks'):
            setattr(asyncio, '_background_tasks', background_tasks)
        background_tasks.add(monitoring_task)
        monitoring_task.add_done_callback(background_tasks.discard)

        logger.info(f"🚀 Started background monitoring task for code generation")

        # Return immediately with task_id and background task hook
        logger.info(f"✅ Code generation started successfully (PID: {process.pid}, Task: {task_id})")

        if task_id:
            # Create background task hook for UI
            from application.agents.shared.hook_utils import (
                create_background_task_hook,
                wrap_response_with_hook,
            )

            hook = create_background_task_hook(
                task_id=task_id,
                task_type="code_generation",
                task_name=f"Generate code: {user_request[:50]}...",
                task_description=f"Generating code with CLI: {user_request[:200]}...",
                conversation_id=conversation_id,
                metadata={
                    "branch_name": branch_name,
                    "language": language,
                    "process_pid": process.pid,
                }
            )

            # Store hook in context for SSE streaming
            tool_context.state["last_tool_hook"] = hook

            message = f"""🤖 Code generation started with CLI!

📋 **Task ID:** {task_id}
🌿 **Branch:** {branch_name}
📝 **Request:** {user_request[:100]}{"..." if len(user_request) > 100 else ""}

⏳ Code generation is running in the background. I'll update you when it completes.
You can continue chatting while the code is being generated.

Click 'View Tasks' to monitor progress."""

            return wrap_response_with_hook(message, hook)
        else:
            return f"""🤖 Code generation started with CLI!

🌿 **Branch:** {branch_name}
📝 **Request:** {user_request[:100]}{"..." if len(user_request) > 100 else ""}

⏳ Code generation is running in the background. I'll update you when it completes."""

    except Exception as e:
        logger.error(f"Error in generate_code_with_cli: {e}", exc_info=True)
        return f"ERROR: {str(e)}"


# ============================================================================
# BUILD APPLICATION TOOLS (for building complete apps from scratch)
# ============================================================================

async def _monitor_build_process(
    process: Any,
    repository_path: str,
    branch_name: str,
    requirements: str,
    timeout_seconds: int = 1800,
    tool_context: Optional[ToolContext] = None,
) -> None:
    """
    Monitor the build process and update BackgroundTask entity with progress.

    This function runs in the background and:
    - Streams output chunks as they arrive
    - Checks process status every 10 seconds
    - Updates BackgroundTask progress every 30 seconds
    - Commits changes every 60 seconds
    - Handles completion, timeout, and errors

    Args:
        process: The subprocess running Augment CLI
        repository_path: Path to repository
        branch_name: Branch name
        requirements: User requirements
        timeout_seconds: Maximum time to wait (default: 1800 = 30 minutes)
        tool_context: Tool context for accessing conversation/task info
    """
    from services.services import get_task_service

    start_time = asyncio.get_event_loop().time()
    last_progress_update = start_time
    last_commit_time = start_time
    progress_update_interval = 30  # seconds
    commit_interval = 60  # seconds

    task_id = tool_context.state.get("background_task_id") if tool_context else None
    task_service = get_task_service()

    try:
        logger.info(f"🔍 Starting build monitoring for task {task_id}, PID: {process.pid}")

        # Start streaming output in background
        output_stream_task = asyncio.create_task(
            _stream_process_output(process=process, task_id=task_id)
        )
        logger.info(f"📤 Started output streaming for PID {process.pid}")

        while True:
            current_time = asyncio.get_event_loop().time()
            elapsed = current_time - start_time

            # Check if timeout exceeded
            if elapsed > timeout_seconds:
                logger.error(f"⏱️ Build timeout after {elapsed:.0f}s (limit: {timeout_seconds}s)")

                # Kill the process
                try:
                    process.kill()
                    await process.wait()
                except Exception as e:
                    logger.warning(f"Failed to kill process: {e}")

                # Update task as failed
                if task_id:
                    await task_service.update_task_status(
                        task_id=task_id,
                        status="failed",
                        progress=0,
                        message=f"Build timeout after {elapsed:.0f} seconds",
                        metadata={"error": "timeout", "elapsed_time": elapsed}
                    )

                return

            # Check if process is still running
            return_code = process.returncode
            if return_code is not None:
                # Process has finished
                logger.info(f"✅ Build process completed with return code: {return_code}")

                # Read final output
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), timeout=10
                    )
                    stdout_text = stdout.decode('utf-8', errors='replace') if stdout else ""
                    stderr_text = stderr.decode('utf-8', errors='replace') if stderr else ""
                except asyncio.TimeoutError:
                    stdout_text = ""
                    stderr_text = "Failed to read process output (timeout)"

                # Determine success/failure
                success = return_code == 0

                # Get diff to show what was generated
                changed_files = []
                if tool_context:
                    try:
                        diff_result = await get_repository_diff(tool_context)
                        diff_data = json.loads(diff_result)
                        for category in ["modified", "added", "untracked"]:
                            changed_files.extend(diff_data.get(category, []))
                    except Exception as e:
                        logger.warning(f"Could not get diff: {e}")

                # Final commit
                try:
                    await _commit_and_push_changes(repository_path, branch_name)
                    logger.info(f"✅ Final commit pushed for branch {branch_name}")
                except Exception as e:
                    logger.warning(f"Failed to commit final changes: {e}")

                # Update task status
                if task_id:
                    if success:
                        await task_service.update_task_status(
                            task_id=task_id,
                            status="completed",
                            progress=100,
                            message=f"Build completed successfully! Generated {len(changed_files)} files.",
                            metadata={
                                "elapsed_time": elapsed,
                                "changed_files": changed_files[:50],  # Limit to 50 files
                                "total_files": len(changed_files)
                            }
                        )
                    else:
                        await task_service.update_task_status(
                            task_id=task_id,
                            status="failed",
                            progress=0,
                            message=f"Build failed with return code {return_code}",
                            metadata={
                                "return_code": return_code,
                                "stderr": stderr_text[:1000],  # Limit error output
                                "elapsed_time": elapsed
                            }
                        )

                return

            # Process still running - update progress periodically
            if current_time - last_progress_update >= progress_update_interval:
                # Calculate progress (0-95% based on elapsed time, max 95% until complete)
                progress = min(95, int((elapsed / timeout_seconds) * 100))

                if task_id:
                    await task_service.update_task_status(
                        task_id=task_id,
                        status="running",
                        progress=progress,
                        message=f"Build in progress... ({int(elapsed)}s elapsed)",
                        metadata={"elapsed_time": elapsed, "pid": process.pid}
                    )

                last_progress_update = current_time
                logger.info(f"📊 Build progress: {progress}% ({int(elapsed)}s elapsed)")

            # Commit changes periodically
            if current_time - last_commit_time >= commit_interval:
                try:
                    await _commit_and_push_changes(repository_path, branch_name)
                    logger.info(f"💾 Progress commit pushed for branch {branch_name}")
                except Exception as e:
                    logger.warning(f"Failed to commit progress: {e}")

                last_commit_time = current_time

            # Wait before next check
            await asyncio.sleep(10)

    except Exception as e:
        logger.error(f"❌ Error monitoring build process: {e}", exc_info=True)

        # Update task as failed
        if task_id:
            try:
                await task_service.update_task_status(
                    task_id=task_id,
                    status="failed",
                    progress=0,
                    message=f"Build monitoring error: {str(e)}",
                    metadata={"error": str(e)}
                )
            except Exception as update_error:
                logger.error(f"Failed to update task status: {update_error}")


@creates_hook("background_task")
@creates_hook("code_changes")
async def generate_application(
    requirements: str,
    language: Optional[str] = None,
    repository_path: Optional[str] = None,
    branch_name: Optional[str] = None,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Generate a complete Cyoda application using Augment CLI with comprehensive prompts.

    This tool builds a COMPLETE application from scratch (entities, workflows, processors, routes, etc.)
    Use generate_code_with_auggie() for incremental changes to existing code.

    **IMPORTANT:** This tool automatically saves all conversation files to the branch BEFORE generating
    the application. This ensures the AI has access to all attached files (requirements, specs, etc.)
    when building the application.

    Uses repository_path, branch_name, and language from tool_context.state if not provided.
    This allows the agent to call generate_application with just requirements after clone_repository.

    Args:
        requirements: User requirements for the application
        language: Programming language ('java' or 'python') - optional if already in context
        repository_path: Path to cloned repository - optional if already in context
        branch_name: Branch name for the build - optional if already in context
        tool_context: Execution context (auto-injected)

    Returns:
        Status message with task ID or error
    """
    try:
        from application.agents.github.prompts import load_template
        from application.entity.background_task.version_1.background_task import BackgroundTask
        from services.services import get_task_service

        # SAFEGUARD: Check if build already started for this branch
        if tool_context:
            existing_build_pid = tool_context.state.get("build_process_pid")
            existing_branch = tool_context.state.get("branch_name")

            if existing_build_pid and existing_branch:
                logger.warning(f"⚠️ Build already started for branch {existing_branch} (PID: {existing_build_pid})")
                return f"⚠️ Build already in progress for branch {existing_branch} (PID: {existing_build_pid}). Please wait for it to complete."

        # Get values from context if not provided
        repository_name = "mcp-cyoda-quart-app"  # Default fallback
        if tool_context:
            language = language or tool_context.state.get("language")
            repository_path = repository_path or tool_context.state.get("repository_path")
            branch_name = branch_name or tool_context.state.get("branch_name")
            repository_name = tool_context.state.get("repository_name", repository_name)

            logger.info(f"🔍 Context state: language={language}, repository_path={repository_path}, branch_name={branch_name}, repository_name={repository_name}")

        # Validate required parameters
        if not language:
            logger.error("Language not specified and not found in context")
            return f"ERROR: Language not specified and not found in context. Please call clone_repository first.{STOP_ON_ERROR}"
        if not repository_path:
            logger.error("Repository path not specified and not found in context")
            return f"ERROR: Repository path not specified and not found in context. Please call clone_repository first.{STOP_ON_ERROR}"
        if not branch_name:
            logger.error("Branch name not specified and not found in context")
            return f"ERROR: Branch name not specified and not found in context. Please call clone_repository first.{STOP_ON_ERROR}"

        # SAFEGUARD: Check if branch is protected
        from application.agents.shared.repository_tools import _is_protected_branch, PROTECTED_BRANCHES
        if await _is_protected_branch(branch_name):
            error_msg = (
                f"🚫 CRITICAL ERROR: Cannot build on protected branch '{branch_name}'. "
                f"Protected branches ({', '.join(sorted(PROTECTED_BRANCHES))}) must NEVER be modified. "
                f"Please use generate_branch_uuid() to create a unique branch name."
            )
            logger.error(error_msg)
            return f"ERROR: {error_msg}"

        # SAFEGUARD: Check CLI invocation limit
        from application.services.streaming_service import check_cli_invocation_limit, get_cli_invocation_count
        session_id = tool_context.state.get("session_id", "unknown") if tool_context else "unknown"
        is_allowed, error_msg = check_cli_invocation_limit(session_id)
        if not is_allowed:
            logger.error(error_msg)
            return f"ERROR: {error_msg}"

        cli_count = get_cli_invocation_count(session_id)
        logger.info(f"🔧 CLI invocation #{cli_count} for session {session_id}")

        # IMPORTANT: Save all conversation files to branch BEFORE generating application
        # This ensures the AI has access to all attached files (requirements, specs, etc.)
        logger.info("📂 Checking for conversation files to save before generating application...")
        if tool_context:
            try:
                from application.agents.shared.repository_tools import retrieve_and_save_conversation_files

                conversation_id = tool_context.state.get("conversation_id")
                if conversation_id:
                    save_result = await retrieve_and_save_conversation_files(tool_context=tool_context)
                    if save_result.startswith("✅") or save_result.startswith("SUCCESS"):
                        logger.info(f"✅ Files saved successfully before generating application: {save_result}")
                    elif "No files found" in save_result or "No valid files" in save_result:
                        logger.info(f"ℹ️ No files to save: {save_result}")
                    else:
                        logger.warning(f"⚠️ File saving returned: {save_result}")
                else:
                    logger.info("ℹ️ No conversation_id in context, skipping file retrieval")
            except Exception as e:
                logger.warning(f"⚠️ Failed to save conversation files before generating application: {e}", exc_info=True)
                # Don't fail the build if file saving fails - continue with generation

        # Load comprehensive build prompt template
        template_name = f"build_{language.lower()}_instructions"
        try:
            prompt_template = load_template(template_name)
            logger.info(f"Loaded prompt template for {language} ({len(prompt_template)} chars)")
        except Exception as e:
            logger.error(f"Failed to load prompt template '{template_name}': {e}")
            return f"ERROR: Failed to load prompt template for {language}: {str(e)}"

        # Combine template with user requirements
        full_prompt = f"{prompt_template}\n\n## User Requirements:\n{requirements}"

        # Check if Augment CLI script exists
        script_path = Path(AUGGIE_CLI_SCRIPT)
        if not script_path.exists():
            logger.error(f"Augment CLI script not found: {AUGGIE_CLI_SCRIPT}")
            return f"ERROR: Augment CLI script not found at {AUGGIE_CLI_SCRIPT}"

        logger.info(
            f"Generating {language} application with Augment CLI in {repository_path}"
        )

        # Get Augment model from config (must be haiku4.5)
        from common.config.config import AUGMENT_MODEL

        # Validate that only haiku4.5 is used for Augment CLI
        if AUGMENT_MODEL != "haiku4.5":
            logger.error(f"Invalid model for Augment CLI: {AUGMENT_MODEL}. Only haiku4.5 is supported.")
            return f"ERROR: Augment CLI only supports haiku4.5 model. Current model: {AUGMENT_MODEL}"

        # Call Augment CLI script using asyncio
        # Format: bash <script> <prompt> <model> <workspace_dir> <branch_id>
        cmd = [
            "bash",
            str(script_path.absolute()),
            full_prompt,
            AUGMENT_MODEL,
            repository_path,
            branch_name,
        ]

        logger.info(f"🚀 Starting Augment CLI process...")
        logger.info(f"📝 Prompt length: {len(full_prompt)} chars")
        logger.info(f"🎯 Model: {AUGMENT_MODEL}")
        logger.info(f"📁 Workspace: {repository_path}")
        logger.info(f"🌿 Branch: {branch_name}")

        # Start the process (non-blocking)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=repository_path,
        )

        logger.info(f"✅ Augment CLI process started with PID: {process.pid}")

        # Store process PID in context for monitoring
        if tool_context:
            tool_context.state["build_process_pid"] = process.pid

        # Create BackgroundTask entity to track build progress
        task_service = get_task_service()
        conversation_id = tool_context.state.get("conversation_id") if tool_context else None
        repository_type = tool_context.state.get("repository_type") if tool_context else None

        # Construct GitHub repository URL
        repository_url = None
        if repository_type == "public":
            if language.lower() == "python":
                repo_name = "mcp-cyoda-quart-app"
            elif language.lower() == "java":
                repo_name = "java-client-template"
            else:
                repo_name = "mcp-cyoda-quart-app"
            repo_owner = os.getenv("REPOSITORY_OWNER", "Cyoda-platform")
            repository_url = f"https://github.com/{repo_owner}/{repo_name}/tree/{branch_name}"

        background_task = await task_service.create_task(
            user_id=tool_context.state.get("user_id", "CYODA") if tool_context else "CYODA",
            task_type="application_build",
            name=f"Build {language} application: {branch_name}",
            description=f"Building complete {language} application: {requirements[:200]}...",
            branch_name=branch_name,
            language=language,
            user_request=requirements,
            conversation_id=conversation_id,
            repository_path=repository_path,
            repository_type=repository_type,
            repository_url=repository_url,
        )

        task_id = background_task.technical_id
        logger.info(f"📋 Created BackgroundTask entity: {task_id}")

        # Store task_id in context
        if tool_context:
            tool_context.state["background_task_id"] = task_id

            # Add task to conversation's background_task_ids list
            if conversation_id:
                from application.agents.shared.repository_tools import _add_task_to_conversation
                await _add_task_to_conversation(conversation_id, task_id)

        # Start monitoring in background (don't wait!)
        monitoring_task = asyncio.create_task(
            _monitor_build_process(
                process=process,
                repository_path=repository_path,
                branch_name=branch_name,
                requirements=requirements,
                timeout_seconds=1800,  # 30 minutes
                tool_context=tool_context,
            )
        )

        # Prevent garbage collection of background task
        background_tasks: set[Any] = getattr(asyncio, '_background_tasks', set())
        if not hasattr(asyncio, '_background_tasks'):
            setattr(asyncio, '_background_tasks', background_tasks)
        background_tasks.add(monitoring_task)
        monitoring_task.add_done_callback(background_tasks.discard)

        logger.info(f"🎯 Build monitoring started in background for task {task_id}")

        # Return immediately with task ID and background task hook
        from application.agents.shared.hook_utils import (
            create_background_task_hook,
            create_deploy_and_open_cloud_hook,
            create_deploy_cyoda_environment_hook,
            create_launch_setup_assistant_hook,
            create_open_tasks_panel_hook,
            create_combined_hook,
            wrap_response_with_hook,
        )

        # Create background task hook for build progress
        background_task_hook = create_background_task_hook(
            task_id=task_id,
            task_type="application_build",
            task_name=f"Build {language} application: {branch_name}",
            task_description=f"Building complete {language} application: {requirements[:200]}...",
            conversation_id=conversation_id,
            metadata={
                "branch_name": branch_name,
                "language": language,
                "repository_path": repository_path,
            }
        )

        # Store background task hook in context for SSE streaming
        # Create deployment and setup hooks for parallel execution
        deploy_hook = create_deploy_cyoda_environment_hook(
            conversation_id=conversation_id,
            task_id=task_id
        )
        setup_hook = create_launch_setup_assistant_hook(
            conversation_id=conversation_id,
            task_id=task_id
        )
        tasks_panel_hook = create_open_tasks_panel_hook(
            conversation_id=conversation_id,
            task_id=task_id,
            message="Track build progress in the Tasks panel",
        )

        # Combine all hooks: background task + deployment + setup + tasks panel
        combined_hooks = create_combined_hook(
            background_task_hook=background_task_hook
        )
        combined_hooks["hooks"].extend([deploy_hook, setup_hook, tasks_panel_hook])

        if tool_context:
            tool_context.state["last_tool_hook"] = combined_hooks
            # Store deployment hook for later use when build completes
            tool_context.state["deployment_hook"] = create_deploy_and_open_cloud_hook(
                conversation_id=conversation_id
            )

        message = f"""🚀 Application build started successfully!

📋 **Task ID:** {task_id}
🌿 **Branch:** {branch_name}
💻 **Language:** {language}
📝 **Requirements:** {requirements[:100]}{"..." if len(requirements) > 100 else ""}

⏳ The build is running in the background. This typically takes 10-30 minutes.
I'll update you when it completes. You can continue chatting while the build runs.

📊 **While you wait:**
- Click 'View Tasks' to monitor build progress
- Deploy the Cyoda environment in parallel with the build
- Launch the Setup Assistant to configure your application"""

        return wrap_response_with_hook(message, combined_hooks)

    except Exception as e:
        logger.error(f"Error in generate_application: {e}", exc_info=True)
        return f"ERROR: {str(e)}"


# Backward compatibility alias
generate_code_with_auggie = generate_code_with_cli


@creates_hook("open_canvas_tab")
async def open_canvas_tab(
    tab_name: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """
    Open a specific canvas tab in the UI.

    This tool creates a hook that instructs the UI to open a specific canvas tab.
    The LLM can use this to guide users to view entities, workflows, requirements, or cloud settings.

    Args:
        tab_name: Name of the canvas tab to open. Valid values:
            - "entities" - Opens Canvas Entities tab
            - "workflows" - Opens Canvas Workflows tab
            - "requirements" - Opens Canvas Requirements tab
            - "cloud" - Opens Cloud/Environments tab
        tool_context: The ADK tool context

    Returns:
        Success message with canvas_tab hook

    Raises:
        ValueError: If tab_name is not one of the valid options

    Examples:
        >>> await open_canvas_tab("entities", tool_context)
        "✅ Opening Canvas Entities tab..."

        >>> await open_canvas_tab("workflows", tool_context)
        "✅ Opening Canvas Workflows tab..."

        >>> await open_canvas_tab("cloud", tool_context)
        "✅ Opening Cloud tab..."
    """
    try:
        from application.agents.shared.hook_utils import create_open_canvas_tab_hook, wrap_response_with_hook

        if not tool_context:
            return f"ERROR: Tool context not available.{STOP_ON_ERROR}"

        conversation_id = tool_context.state.get("conversation_id")
        if not conversation_id:
            return f"ERROR: conversation_id not found in context.{STOP_ON_ERROR}"

        # Validate tab_name
        valid_tabs = ["entities", "workflows", "requirements", "cloud"]
        if tab_name not in valid_tabs:
            return f"ERROR: Invalid tab_name '{tab_name}'. Must be one of: {', '.join(valid_tabs)}.{STOP_ON_ERROR}"

        # Create the hook
        hook = create_open_canvas_tab_hook(
            conversation_id=conversation_id,
            tab_name=tab_name,
        )

        # Store hook in context for SSE streaming
        tool_context.state["last_tool_hook"] = hook

        # Create appropriate message based on tab
        tab_messages = {
            "entities": "✅ Opening Canvas Entities tab to view and manage your entities.",
            "workflows": "✅ Opening Canvas Workflows tab to view and manage your workflows.",
            "requirements": "✅ Opening Canvas Requirements tab to view and manage your requirements.",
            "cloud": "✅ Opening Cloud tab to view your environment details.",
        }

        message = tab_messages.get(tab_name, f"✅ Opening Canvas {tab_name} tab...")

        logger.info(f"🎨 Opening canvas tab: {tab_name} for conversation {conversation_id}")
        return wrap_response_with_hook(message, hook)

    except Exception as e:
        logger.error(f"Error opening canvas tab: {e}", exc_info=True)
        return f"ERROR: Failed to open canvas tab: {str(e)}"


async def validate_workflow_against_schema(
    workflow_json: str,
    tool_context: Optional[ToolContext] = None,
) -> str:
    """Validate a workflow JSON against the workflow schema.

    This tool validates that a generated workflow matches the required schema
    before saving it to the repository. It checks:
    - Required fields (version, name, initialState, states)
    - State structure and transitions
    - Processor and criterion configurations
    - Execution modes and retry policies

    Args:
        workflow_json: The workflow JSON content as a string
        tool_context: Optional tool context for logging

    Returns:
        A validation result message with either:
        - Success message if validation passes
        - Detailed error messages if validation fails

    Examples:
        >>> workflow = '{"version": "1", "name": "Customer", "initialState": "initial_state", "states": {...}}'
        >>> await validate_workflow_against_schema(workflow)
        "✅ Workflow validation passed! The workflow matches the schema."

        >>> invalid_workflow = '{"name": "Customer"}'
        >>> await validate_workflow_against_schema(invalid_workflow)
        "❌ Workflow validation failed: Missing required field 'version'"
    """
    try:
        import jsonschema

        # Load the workflow schema
        schema_path = Path(__file__).parent / "prompts" / "workflow_schema.json"
        if not schema_path.exists():
            return f"ERROR: Workflow schema not found at {schema_path}.{STOP_ON_ERROR}"

        with open(schema_path, "r") as f:
            schema_data = json.load(f)

        # Extract the actual schema from the schema file
        schema = schema_data.get("schema", schema_data)

        # Parse the workflow JSON
        try:
            workflow = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            return f"❌ Workflow validation failed: Invalid JSON - {str(e)}"

        # Validate against schema
        try:
            jsonschema.validate(instance=workflow, schema=schema)
            logger.info("✅ Workflow validation passed")
            return "✅ Workflow validation passed! The workflow matches the schema and is ready to save."

        except jsonschema.ValidationError as e:
            # Provide detailed error message
            error_path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
            error_msg = f"❌ Workflow validation failed:\n"
            error_msg += f"   Location: {error_path}\n"
            error_msg += f"   Error: {e.message}\n"

            # Add helpful context
            if "required" in str(e.message).lower():
                error_msg += f"   Hint: Check that all required fields are present in your workflow.\n"
            elif "enum" in str(e.message).lower():
                error_msg += f"   Hint: Check that field values match the allowed options.\n"

            error_msg += f"\n   Please fix the workflow and try again."

            logger.warning(f"Workflow validation failed: {e.message}")
            return error_msg

        except jsonschema.SchemaError as e:
            return f"ERROR: Invalid schema file - {str(e)}.{STOP_ON_ERROR}"

    except ImportError:
        return f"ERROR: jsonschema library not available. Install with: pip install jsonschema.{STOP_ON_ERROR}"
    except Exception as e:
        logger.error(f"Error validating workflow: {e}", exc_info=True)
        return f"ERROR: Failed to validate workflow: {str(e)}.{STOP_ON_ERROR}"


async def load_workflow_schema() -> str:
    """Load the workflow schema from the prompts directory.

    Returns:
        JSON schema content as string, or error message if file not found
    """
    try:
        # Get the prompts directory relative to this file
        prompts_dir = Path(__file__).parent / "prompts"
        schema_file = prompts_dir / "workflow_schema.json"

        if not schema_file.exists():
            return f"ERROR: Workflow schema file not found at {schema_file}"

        schema_content = schema_file.read_text(encoding="utf-8")
        logger.info(f"✅ Loaded workflow schema from {schema_file}")
        return schema_content

    except Exception as e:
        logger.error(f"Error loading workflow schema: {e}", exc_info=True)
        return f"ERROR: Failed to load workflow schema: {str(e)}"


async def load_workflow_example() -> str:
    """Load the example workflow from the prompts directory.

    Returns:
        Example workflow JSON content as string, or error message if file not found
    """
    try:
        # Get the prompts directory relative to this file
        prompts_dir = Path(__file__).parent / "prompts"
        example_file = prompts_dir / "ExampleEntity.json"

        if not example_file.exists():
            return f"ERROR: Example workflow file not found at {example_file}"

        example_content = example_file.read_text(encoding="utf-8")
        logger.info(f"✅ Loaded example workflow from {example_file}")
        return example_content

    except Exception as e:
        logger.error(f"Error loading example workflow: {e}", exc_info=True)
        return f"ERROR: Failed to load example workflow: {str(e)}"


async def load_workflow_prompt() -> str:
    """Load the workflow design instructions from the prompts directory.

    Returns:
        Workflow prompt content as string, or error message if file not found
    """
    try:
        # Get the prompts directory relative to this file
        prompts_dir = Path(__file__).parent / "prompts"
        prompt_file = prompts_dir / "workflow_prompt.template"

        if not prompt_file.exists():
            return f"ERROR: Workflow prompt file not found at {prompt_file}"

        prompt_content = prompt_file.read_text(encoding="utf-8")
        logger.info(f"✅ Loaded workflow prompt from {prompt_file}")
        return prompt_content

    except Exception as e:
        logger.error(f"Error loading workflow prompt: {e}", exc_info=True)
        return f"ERROR: Failed to load workflow prompt: {str(e)}"

