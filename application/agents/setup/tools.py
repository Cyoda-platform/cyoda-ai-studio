"""Tools for the Setup agent."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


async def validate_environment(
    required_vars: Optional[list[str]] = None,
) -> dict[str, bool]:
    """Validate that required environment variables are set.

    Checks if the specified environment variables are configured.
    Useful for verifying Cyoda project setup.

    Args:
      required_vars: List of environment variable names to check.
                     Defaults to common Cyoda variables.

    Returns:
      Dictionary mapping variable names to their presence status (True/False).
    """
    if required_vars is None:
        required_vars = [
            "CYODA_HOST",
            "CYODA_PORT",
            "CYODA_GRPC_HOST",
            "CYODA_GRPC_PORT",
            "GOOGLE_MODEL",
            "GOOGLE_API_KEY",
        ]

    return {var: os.getenv(var) is not None for var in required_vars}


async def check_project_structure() -> dict[str, Any]:
    """Check if the current directory has a valid Cyoda project structure.

    Verifies the presence of key directories and files for a Cyoda application.

    Returns:
      Dictionary with structure validation results:
        - is_valid: Overall validity
        - missing_items: List of missing required items
        - present_items: List of found items
        - recommendations: Setup recommendations
    """
    required_items = {
        "pyproject.toml": "file",
        "application": "directory",
        "common": "directory",
        ".env": "file",
        ".venv": "directory",
    }

    optional_items = {
        "application/entity": "directory",
        "application/routes": "directory",
        "application/agents": "directory",
        "application/resources/workflow": "directory",
    }

    cwd = Path.cwd()
    missing = []
    present = []

    for item, item_type in required_items.items():
        path = cwd / item
        if item_type == "file" and path.is_file():
            present.append(item)
        elif item_type == "directory" and path.is_dir():
            present.append(item)
        else:
            missing.append(item)

    optional_present = []
    for item, item_type in optional_items.items():
        path = cwd / item
        if item_type == "file" and path.is_file():
            optional_present.append(item)
        elif item_type == "directory" and path.is_dir():
            optional_present.append(item)

    is_valid = len(missing) == 0

    recommendations = []
    if not is_valid:
        recommendations.append("Create missing required items")
        if "pyproject.toml" in missing:
            recommendations.append("Initialize Python project with pyproject.toml")
        if ".env" in missing:
            recommendations.append(
                "Create .env file with required environment variables"
            )
        if ".venv" in missing:
            recommendations.append("Create virtual environment: python -m venv .venv")

    return {
        "is_valid": is_valid,
        "missing_items": missing,
        "present_items": present,
        "optional_present": optional_present,
        "recommendations": recommendations,
        "current_directory": str(cwd),
    }


async def validate_workflow_file(file_path: str) -> dict[str, Any]:
    """Validate a Cyoda workflow JSON file.

    Checks if the workflow file exists and has valid JSON structure.

    Args:
      file_path: Path to the workflow JSON file (relative or absolute).

    Returns:
      Dictionary with validation results:
        - is_valid: Whether the file is valid
        - exists: Whether the file exists
        - error: Error message if invalid
        - file_path: Resolved file path
    """
    import json

    path = Path(file_path)

    if not path.exists():
        return {
            "is_valid": False,
            "exists": False,
            "error": f"File not found: {file_path}",
            "file_path": str(path.absolute()),
        }

    try:
        with open(path, "r") as f:
            data = json.load(f)

        # Basic validation - check for required workflow fields
        required_fields = ["name", "states", "transitions"]
        missing_fields = [f for f in required_fields if f not in data]

        if missing_fields:
            return {
                "is_valid": False,
                "exists": True,
                "error": f'Missing required fields: {", ".join(missing_fields)}',
                "file_path": str(path.absolute()),
            }

        return {
            "is_valid": True,
            "exists": True,
            "error": None,
            "file_path": str(path.absolute()),
            "workflow_name": data.get("name"),
            "num_states": len(data.get("states", [])),
            "num_transitions": len(data.get("transitions", [])),
        }

    except json.JSONDecodeError as e:
        return {
            "is_valid": False,
            "exists": True,
            "error": f"Invalid JSON: {str(e)}",
            "file_path": str(path.absolute()),
        }




async def get_build_id_from_context(tool_context: ToolContext) -> str:
    """
    Retrieve build ID from the current session context.

    In the deprecated workflow system, this function retrieved the build ID from
    the deployment workflow entity. In the ADK version, we check the session state
    for a stored build_id value.

    Returns:
        Build ID string if found, otherwise a message indicating it's not available
    """
    try:
        # Try to get build_id from session state
        session_state = tool_context.state
        build_id = session_state.get('build_id')

        if build_id:
            logger.info(f"Retrieved build_id from session: {build_id}")
            return build_id
        else:
            logger.warning("No build_id found in session state")
            return "Build ID not found in session. Please provide your build ID manually or check your deployment status."

    except Exception as e:
        logger.exception(f"Error retrieving build_id: {e}")
        return f"Error retrieving build ID: {str(e)}"


async def get_env_deploy_status(build_id: str) -> str:
    """
    Check the deployment status for a given build ID.

    Makes an HTTP request to the Cyoda deployment status endpoint to check
    if the environment deployment is complete. Authenticates first using
    CYODA_CLIENT_ID and CYODA_CLIENT_SECRET.

    Args:
        build_id: The build identifier to check status for

    Returns:
        Formatted string with deployment state and status, or error message
    """
    try:
        import httpx

        # Get required environment variables
        cloud_manager_host = os.getenv('CLOUD_MANAGER_HOST')
        client_host = os.getenv('CLIENT_HOST')
        client_id = os.getenv('CYODA_CLIENT_ID')
        client_secret = os.getenv('CYODA_CLIENT_SECRET')

        if not cloud_manager_host:
            return "Error: CLOUD_MANAGER_HOST environment variable not configured"

        if not client_host:
            return "Error: CLIENT_HOST environment variable not configured"

        if not client_id or not client_secret:
            return "Error: CYODA_CLIENT_ID and CYODA_CLIENT_SECRET environment variables must be configured"

        # Determine protocol based on host
        protocol = "http" if "localhost" in cloud_manager_host else "https"

        # Construct authentication URL
        auth_url = f"{protocol}://cloud-manager-cyoda.{client_host}/api/auth/login"

        # Construct deployment status URL
        status_url = os.getenv(
            'DEPLOY_CYODA_ENV_STATUS',
            f"{protocol}://{cloud_manager_host}/deploy/cyoda-env/status"
        )

        # Authenticate and get token
        logger.info(f"Authenticating with cloud manager at {auth_url}")

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Login to get authentication token
            auth_response = await client.post(
                auth_url,
                json={
                    "username": client_id,
                    "password": client_secret
                }
            )
            auth_response.raise_for_status()

            auth_data = auth_response.json()
            token = auth_data.get('token') or auth_data.get('access_token')

            if not token:
                return "Error: No token returned from authentication endpoint"

            logger.info(f"Authentication successful, checking deployment status for build_id: {build_id}")

            # Step 2: Make authenticated request to check deployment status
            headers = {"Authorization": f"Bearer {token}"}
            response = await client.get(
                f"{status_url}?build_id={build_id}",
                headers=headers
            )
            response.raise_for_status()

            data = response.json()
            deploy_state = data.get('state', 'UNKNOWN')
            deploy_status = data.get('status', 'UNKNOWN')

            result = f"Deployment Status:\n- State: {deploy_state}\n- Status: {deploy_status}"
            logger.info(f"Deployment status for {build_id}: {result}")
            return result

    except httpx.HTTPError as e:
        error_msg = f"HTTP error checking deployment status: {str(e)}"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error checking deployment status: {str(e)}"
        logger.exception(error_msg)
        return error_msg


async def get_build_context(tool_context: ToolContext) -> str:
    """
    Get build context (language and branch_name) from tool_context.state or conversation's workflow_cache.

    Priority order:
    1. First check tool_context.state for language and branch_name (set by GitHub agent)
    2. If not found, retrieve from conversation's workflow_cache

    This allows the setup agent to automatically configure itself when invoked manually
    or after transfer from GitHub agent.

    Returns:
        JSON string with build context or error message
    """
    try:
        # PRIORITY 1: Check tool_context.state first (set by GitHub agent when transferring)
        language = tool_context.state.get("language")
        branch_name = tool_context.state.get("branch_name")

        if language and branch_name:
            logger.info(f"Retrieved build context from tool_context.state: language={language}, branch={branch_name}")
            return json.dumps({
                "success": True,
                "language": language,
                "branch_name": branch_name,
                "source": "tool_context.state"
            })

        # PRIORITY 2: Check workflow_cache if not found in tool_context.state
        from services.services import get_entity_service
        from application.entity.conversation.version_1.conversation import Conversation

        entity_service = get_entity_service()
        conversation_id = tool_context.state.get("conversation_id")

        if not conversation_id:
            return json.dumps({
                "success": False,
                "error": "No conversation_id found in session state and no language/branch in tool_context.state"
            })

        # Retrieve conversation entity
        conversation_response = await entity_service.get_by_id(
            entity_id=conversation_id,
            entity_class=Conversation.ENTITY_NAME,
            entity_version=str(Conversation.ENTITY_VERSION),
        )

        if not conversation_response or not conversation_response.data:
            return json.dumps({
                "success": False,
                "error": "Could not retrieve conversation entity"
            })

        conversation_data = conversation_response.data if isinstance(conversation_response.data, dict) else conversation_response.data.model_dump(by_alias=False)
        workflow_cache = conversation_data.get("workflowCache", {})

        language = workflow_cache.get("language")
        branch_name = workflow_cache.get("branch_name")

        if language and branch_name:
            logger.info(f"Retrieved build context from workflow_cache: language={language}, branch={branch_name}")
            return json.dumps({
                "success": True,
                "language": language,
                "branch_name": branch_name,
                "source": "workflow_cache"
            })
        else:
            return json.dumps({
                "success": False,
                "error": "No build context found in tool_context.state or conversation workflow_cache"
            })

    except Exception as e:
        error_msg = f"Error retrieving build context: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({
            "success": False,
            "error": error_msg
        })


async def get_user_info(user_request: str, tool_context: ToolContext) -> str:
    """
    Retrieve comprehensive user and workflow information from entity and workflow cache.

    This function collects all available information about the user's current context including:
    - User authentication status and Cyoda environment details
    - Repository information (branch, name, URL, installation ID)
    - Programming language and workflow settings
    - Build and deployment status
    - User requests and file attachments
    - Any other cached workflow data

    Args:
        user_request: The user's request or query for context
        tool_context: Tool context containing session state

    Returns:
        Formatted string with comprehensive user and workflow information
    """
    try:
        import httpx
        from services.services import get_entity_service
        from application.entity.conversation.version_1.conversation import Conversation

        session_state = tool_context.state
        conversation_id = session_state.get("conversation_id")
        user_id = session_state.get("user_id", "guest.user")

        # Check if user is guest
        is_guest = user_id.startswith('guest.')

        # Determine Cyoda environment URL and deployment status
        client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
        deployed = False

        if is_guest:
            cyoda_url = "please, log in to deploy"
        else:
            cyoda_url = f"https://client-{user_id.lower()}.{client_host}"
            # Check if environment is deployed by trying to access it
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{cyoda_url}/api/v1", headers={"Authorization": "Bearer guest_token"})
                    # If we get 401 (invalid token), environment exists
                    if response.status_code == 401:
                        deployed = True
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    deployed = True
            except Exception as e:
                logger.debug(f"Could not check Cyoda environment status: {e}")

        # Build info dictionary with user authentication and environment information
        info = {
            'user_logged_in_most_recent_status': not is_guest,
            'user_id': user_id,
            'cyoda_env_most_recent_url': cyoda_url,
            'cyoda_environment_most_recent_status': 'deployed' if deployed else 'is not yet deployed',
        }

        # Try to get workflow_cache from Conversation entity and merge all data
        if conversation_id:
            try:
                entity_service = get_entity_service()
                conversation_response = await entity_service.get_by_id(
                    entity_id=conversation_id,
                    entity_class=Conversation.ENTITY_NAME,
                    entity_version=str(Conversation.ENTITY_VERSION),
                )

                if conversation_response and conversation_response.data:
                    conversation_data = conversation_response.data if isinstance(conversation_response.data, dict) else conversation_response.data.model_dump(by_alias=False)
                    workflow_cache = conversation_data.get("workflowCache", {})

                    # Merge ALL workflow_cache data into info (like the old processor version)
                    info.update(workflow_cache)

                    logger.info(f"Retrieved workflow_cache from Conversation: {list(workflow_cache.keys())}")
            except Exception as e:
                logger.warning(f"Could not retrieve Conversation entity: {e}")
                # Continue with basic info only

        # Prepare the final result with all available information
        info_json = json.dumps(info, indent=2)
        return f"Please base your answer on this comprehensive information about the user and workflow context:\n{info_json}"

    except Exception as e:
        error_msg = f"Error getting user info: {str(e)}"
        logger.exception(error_msg)
        return f"Error getting user info: {error_msg}"


async def ui_function_issue_technical_user(tool_context: ToolContext, env_name: Optional[str] = None) -> str:
    """
    Issue M2M (machine-to-machine) technical user credentials.

    This function stores a UI function call instruction in the tool context
    that tells the frontend to make an API call to issue technical user credentials
    (CYODA_CLIENT_ID and CYODA_CLIENT_SECRET) for OAuth2 authentication.

    The UI function JSON will be added to the conversation by the agent framework
    after the agent completes its response, preventing race conditions.

    Use this tool when the user asks for credentials or needs to authenticate
    their application with the Cyoda environment.

    IMPORTANT: You MUST ask the user for env_name before calling this function. DO NOT assume or infer the environment name.
    The user might have multiple environments (dev, staging, prod, etc.), so you must explicitly ask them which environment needs credentials.

    Args:
        tool_context: The ADK tool context (auto-injected)
        env_name: Environment name to issue credentials for. REQUIRED - must be provided by the user.
                  If not provided, this function will return an error asking you to prompt the user.
                  Example prompt: "Which environment would you like to issue credentials for? For example: 'dev', 'prod', 'staging', etc."

    Returns:
        Success message confirming credential issuance was initiated
    """
    try:
        import re

        # Get user ID from context
        user_id = tool_context.state.get("user_id", "guest")

        if not env_name:
            return "ERROR: env_name parameter is required but was not provided. You MUST ask the user which environment to issue credentials for before calling this function. Ask them: 'Which environment would you like to issue credentials for? For example: dev, prod, staging, etc.' DO NOT assume or infer the environment name."

        if user_id.startswith("guest"):
            return "Sorry, issuing credentials is only available to logged-in users. Please sign up or log in first."

        # Helper function to normalize namespace (same as in environment agent)
        def _get_namespace(user_name: str):
            namespace = re.sub(r"[^a-z0-9-]", "-", user_name.lower())
            return namespace

        # Construct environment URL using the same pattern as environment agent
        client_host = os.getenv("CLIENT_HOST", "cyoda.cloud")
        namespace = f"client-{_get_namespace(user_id)}-{_get_namespace(env_name)}"
        env_url = f"{namespace}.{client_host}"

        # Create UI function parameters with environment URL
        ui_params = {
            "type": "ui_function",
            "function": "ui_function_issue_technical_user",
            "method": "POST",
            "path": "/api/clients",
            "response_format": "json",
            "env_url": env_url,
        }

        logger.info(f"Storing UI function in tool context for environment {env_url}: {json.dumps(ui_params)}")

        # Store UI function in tool context so the agent framework can add it to conversation
        # This prevents race conditions where both the tool and route handler update the conversation
        if "ui_functions" not in tool_context.state:
            tool_context.state["ui_functions"] = []
        tool_context.state["ui_functions"].append(ui_params)

        logger.info(f"✅ UI function stored in context for {env_url}, will be added to conversation after agent response")

        return f"✅ Credential issuance initiated for environment: {env_url}\n\nThe UI will create your M2M technical user credentials (CYODA_CLIENT_ID and CYODA_CLIENT_SECRET) for OAuth2 authentication with this environment."
    except Exception as e:
        error_msg = f"Error issuing technical user: {str(e)}"
        logger.exception(error_msg)
        return error_msg



async def list_directory_files(directory_path: str, tool_context: ToolContext) -> str:
    """
    List all files recursively in a directory.

    Walks through the directory tree and returns a list of all files found,
    excluding common directories like .git, .venv, __pycache__, etc.

    Args:
        directory_path: Relative path to the directory to list

    Returns:
        JSON string with list of files or error message
    """
    try:
        # Get project root from session state or use current directory
        session_state = tool_context.state
        project_root = session_state.get('project_path', os.getcwd())

        # Construct full path
        full_path = os.path.join(project_root, directory_path)

        # Validate path security
        if not os.path.exists(full_path):
            return json.dumps({"error": f"Directory not found: {directory_path}"})

        if not os.path.isdir(full_path):
            return json.dumps({"error": f"Path is not a directory: {directory_path}"})

        # Directories to exclude
        exclude_dirs = {'.git', '.venv', '__pycache__', 'node_modules', '.idea', 'backup'}

        # Collect all files recursively (run in thread pool for large directories)
        def _walk_directory():
            all_files = []
            for root, dirs, files in os.walk(full_path):
                # Remove excluded directories from traversal
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                # Add files with relative paths
                for file in files:
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, project_root)
                    all_files.append(relative_path)
            return all_files

        loop = asyncio.get_event_loop()
        all_files = await loop.run_in_executor(None, _walk_directory)

        logger.info(f"Listed {len(all_files)} files in {directory_path}")
        return json.dumps({"files": all_files, "count": len(all_files)}, indent=2)

    except Exception as e:
        error_msg = f"Error listing directory files: {str(e)}"
        logger.exception(error_msg)
        return json.dumps({"error": error_msg})


async def read_file(file_path: str, tool_context: ToolContext) -> str:
    """
    Read the contents of a file.

    Args:
        file_path: Relative path to the file to read

    Returns:
        File contents as string, or error message
    """
    try:
        # Get project root from session state or use current directory
        session_state = tool_context.state
        project_root = session_state.get('project_path', os.getcwd())

        # Construct full path
        full_path = os.path.join(project_root, file_path)

        # Validate path security
        if '..' in file_path or file_path.startswith('/'):
            return f"Error: Invalid file path. Path must be relative and not contain '..'"

        if not os.path.exists(full_path):
            return f"Error: File not found: {file_path}"

        if not os.path.isfile(full_path):
            return f"Error: Path is not a file: {file_path}"

        # Read file contents (run in thread pool for async)
        def _read_file():
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, _read_file)

        logger.info(f"Read file: {file_path} ({len(content)} characters)")
        return content

    except UnicodeDecodeError:
        return f"Error: File is not a text file or uses unsupported encoding: {file_path}"
    except Exception as e:
        error_msg = f"Error reading file: {str(e)}"
        logger.exception(error_msg)
        return error_msg


async def add_application_resource(file_path: str, content: str, tool_context: ToolContext) -> str:
    """
    Add or update an application resource file.

    Creates a new file or updates an existing file with the provided content.
    Validates path security to prevent directory traversal attacks.

    Args:
        file_path: Relative path where the file should be created/updated
        content: Content to write to the file

    Returns:
        Success message with file details, or error message
    """
    try:
        # Get project root from session state or use current directory
        session_state = tool_context.state
        project_root = session_state.get('project_path', os.getcwd())

        # Validate path security
        if '..' in file_path or file_path.startswith('/'):
            return "Error: Invalid file path. Path must be relative and not contain '..'"

        # Construct full path
        full_path = os.path.join(project_root, file_path)

        # Create parent directories and write file (run in thread pool for async)
        def _write_file():
            parent_dir = os.path.dirname(full_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _write_file)

        character_count = len(content)
        logger.info(f"Added/updated application resource: {file_path} ({character_count} characters)")
        return f"Successfully added application resource: {file_path} ({character_count} characters)"

    except Exception as e:
        error_msg = f"Error adding application resource: {str(e)}"
        logger.exception(error_msg)
        return error_msg


async def set_setup_context(
    programming_language: str,
    git_branch: str,
    repository_name: str,
    entity_name: Optional[str] = None,
    tool_context: ToolContext = None
) -> str:
    """
    Set the setup context parameters in session state.

    This tool should be called once the agent has gathered all required information
    from the user (programming language, git branch, repository name). It stores
    these values in session state so they can be used by the instruction template.

    Args:
        programming_language: Either "PYTHON" or "JAVA"
        git_branch: The git branch the user is working on
        repository_name: Either "mcp-cyoda-quart-app" or "java-client-template"
        entity_name: Optional entity name for the application

    Returns:
        Confirmation message with the stored context
    """
    try:
        # Validate programming language
        if programming_language not in ["PYTHON", "JAVA"]:
            return f"Error: programming_language must be either 'PYTHON' or 'JAVA', got '{programming_language}'"

        # Store in session state
        tool_context.state['programming_language'] = programming_language
        tool_context.state['git_branch'] = git_branch
        tool_context.state['repository_name'] = repository_name

        # Store entity_name if provided
        if entity_name:
            tool_context.state['entity_name'] = entity_name

        logger.info(f"Setup context set: {programming_language}, {git_branch}, {repository_name}, entity_name={entity_name}")

        return f"""Setup context configured:
- Programming Language: {programming_language}
- Git Branch: {git_branch}
- Repository: {repository_name}
{f'- Entity Name: {entity_name}' if entity_name else ''}

Now I'll provide you with detailed step-by-step setup instructions."""

    except Exception as e:
        error_msg = f"Error setting setup context: {str(e)}"
        logger.exception(error_msg)
        return error_msg


async def finish_discussion() -> str:
    """
    Mark the setup discussion as finished.

    This function signals that the setup process is complete and the user
    is ready to proceed with development.

    Returns:
        Success message indicating setup is complete
    """
    logger.info("Setup discussion marked as finished")
    return "Setup complete! You're all set to start developing your Cyoda application. If you need any further assistance, feel free to ask."