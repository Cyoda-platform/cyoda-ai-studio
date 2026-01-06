"""Constants for the Setup agent."""

from __future__ import annotations

# Programming languages
LANGUAGE_PYTHON = "PYTHON"
LANGUAGE_JAVA = "JAVA"
VALID_LANGUAGES = [LANGUAGE_PYTHON, LANGUAGE_JAVA]

# Repository names
REPO_PYTHON_TEMPLATE = "mcp-cyoda-quart-app"
REPO_JAVA_TEMPLATE = "java-client-template"

# Default environment variables to check
DEFAULT_ENV_VARS = [
    "CYODA_HOST",
    "CYODA_PORT",
    "CYODA_GRPC_HOST",
    "CYODA_GRPC_PORT",
    "GOOGLE_MODEL",
    "GOOGLE_API_KEY",
]

# Required project structure items
REQUIRED_PROJECT_ITEMS = {
    "pyproject.toml": "file",
    "application": "directory",
    "common": "directory",
    ".env": "file",
    ".venv": "directory",
}

# Optional project structure items
OPTIONAL_PROJECT_ITEMS = {
    "application/entity": "directory",
    "application/routes": "directory",
    "application/agents": "directory",
    "application/resources/workflow": "directory",
}

# Required workflow fields
REQUIRED_WORKFLOW_FIELDS = ["name", "states", "transitions"]

# Directories to exclude from file listing
EXCLUDED_DIRECTORIES = {'.git', '.venv', '__pycache__', 'node_modules', '.idea', 'backup'}

# File encoding
DEFAULT_ENCODING = "utf-8"

# HTTP protocols
HTTP_PROTOCOL = "http"
HTTPS_PROTOCOL = "https"

# Session state keys
KEY_USER_ID = "user_id"
KEY_CONVERSATION_ID = "conversation_id"
KEY_BUILD_ID = "build_id"
KEY_LANGUAGE = "language"
KEY_BRANCH_NAME = "branch_name"
KEY_PROJECT_PATH = "project_path"
KEY_PROGRAMMING_LANGUAGE = "programming_language"
KEY_GIT_BRANCH = "git_branch"
KEY_REPOSITORY_NAME = "repository_name"
KEY_ENTITY_NAME = "entity_name"

# Guest user prefix
GUEST_USER_PREFIX = "guest."

# Deployment states
STATE_UNKNOWN = "UNKNOWN"

# UI function types
UI_FUNCTION_TYPE = "ui_function"
UI_FUNCTION_ISSUE_TECHNICAL_USER = "ui_function_issue_technical_user"
