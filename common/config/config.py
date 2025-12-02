"""
Enhanced configuration module with backward compatibility.

This module provides backward compatibility with the old configuration system
while using the new configuration manager under the hood.
"""

import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import new configuration system
try:
    from .manager import get_config_manager  # type: ignore[import-untyped]

    _use_new_config = True
    _config_manager = get_config_manager()
except ImportError:
    _use_new_config = False


# Legacy function for backward compatibility
def get_env(key: str) -> str:
    """Get environment variable or raise exception if not found."""
    value = os.getenv(key)
    if value is None:
        raise Exception(f"{key} not found")
    return value


SKIP_SSL = os.getenv("SKIP_SSL", False)
CYODA_HOST = get_env("CYODA_HOST")
CYODA_CLIENT_ID = get_env("CYODA_CLIENT_ID")
CYODA_CLIENT_SECRET = get_env("CYODA_CLIENT_SECRET")
CYODA_TOKEN_URL = f"{'http' if SKIP_SSL else 'https'}://{CYODA_HOST}/api/oauth/token"
CHAT_ID = os.getenv("CHAT_ID", "cyoda-client")
ENTITY_VERSION = os.getenv("ENTITY_VERSION", "1")
GRPC_PROCESSOR_TAG = os.getenv("GRPC_PROCESSOR_TAG", "cloud_manager_app")
CYODA_AI_URL = os.getenv(
    "CYODA_AI_URL", f"{'http' if SKIP_SSL else 'https'}://{CYODA_HOST}/ai"
)
CYODA_API_URL = os.getenv(
    "CYODA_API_URL", f"{'http' if SKIP_SSL else 'https'}://{CYODA_HOST}/api"
)
GRPC_ADDRESS = os.getenv("GRPC_ADDRESS", f"grpc-{CYODA_HOST}")
PROJECT_DIR = os.getenv("PROJECT_DIR", os.path.expanduser("~/cyoda_projects"))
CHAT_REPOSITORY = os.getenv("CHAT_REPOSITORY", "cyoda")
IMPORT_WORKFLOWS = bool(os.getenv("IMPORT_WORKFLOWS", "true"))

# GitHub Configuration
# GitHub App configuration for public repositories
GITHUB_APP_ID = os.getenv("GITHUB_APP_ID")
GITHUB_APP_OWNER = os.getenv("GITHUB_APP_OWNER")
GITHUB_APP_CLIENT_ID = os.getenv("GITHUB_APP_CLIENT_ID")
GITHUB_APP_PRIVATE_KEY_PATH = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH")
GITHUB_APP_PRIVATE_KEY_CONTENT = os.getenv("GITHUB_APP_PRIVATE_KEY_CONTENT")
GITHUB_APP_PUBLIC_LINK = os.getenv("GITHUB_APP_PUBLIC_LINK")
GITHUB_WEBHOOK_URL = os.getenv("GITHUB_WEBHOOK_URL")
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")

# GitHub App - Public Repository Configuration
GITHUB_PUBLIC_REPO_INSTALLATION_ID = os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID")
PYTHON_PUBLIC_REPO_URL = os.getenv("PYTHON_PUBLIC_REPO_URL", "https://github.com/Cyoda-platform/mcp-cyoda-quart-app")
JAVA_PUBLIC_REPO_URL = os.getenv("JAVA_PUBLIC_REPO_URL", "https://github.com/Cyoda-platform/java-client-template")

# GitHub repository defaults
GH_DEFAULT_OWNER = os.getenv("GH_DEFAULT_OWNER", "Cyoda-platform")
GH_DEFAULT_REPOS = os.getenv("GH_DEFAULT_REPOS", "mcp-cyoda-quart-app,java-client-template").split(",")
GH_DEFAULT_USERNAME = os.getenv("GH_DEFAULT_USERNAME", "target-username")
GH_DEFAULT_PERMISSION = os.getenv("GH_DEFAULT_PERMISSION", "push")

# Repository configuration
REPOSITORY_URL = os.getenv("REPOSITORY_URL", "https://github.com/{owner}/{repository_name}")
RAW_REPOSITORY_URL = os.getenv("RAW_REPOSITORY_URL", "https://raw.githubusercontent.com/{owner}/{repository_name}")
PYTHON_REPOSITORY_NAME = os.getenv("PYTHON_REPOSITORY_NAME", "mcp-cyoda-quart-app")
JAVA_REPOSITORY_NAME = os.getenv("JAVA_REPOSITORY_NAME", "java-client-template")
CLIENT_GIT_BRANCH = os.getenv("CLIENT_GIT_BRANCH", "main")
CLONE_REPO = os.getenv("CLONE_REPO", "false").lower() == "true"

# AI Model Configuration
AI_MODEL = os.getenv("AI_MODEL", "gemini-2.0-flash-exp")
AI_SDK = os.getenv("AI_SDK", "google")  # "google" or "openai"

# Constants
CYODA_ENTITY_TYPE_EDGE_MESSAGE = "EDGE_MESSAGE"
GENERAL_MEMORY_TAG = "general"
