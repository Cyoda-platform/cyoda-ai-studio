"""Named constants for GitHub agent tools.

This module centralizes all magic strings, file extensions, project types,
and other constant values used throughout the GitHub agent.
"""

from __future__ import annotations

# ============================================================================
# Project Types
# ============================================================================

PROJECT_TYPE_PYTHON = "python"
PROJECT_TYPE_JAVA = "java"

SUPPORTED_PROJECT_TYPES = [PROJECT_TYPE_PYTHON, PROJECT_TYPE_JAVA]

# ============================================================================
# File Extensions
# ============================================================================

# Document extensions
EXT_PDF = ".pdf"
EXT_DOCX = ".docx"
EXT_XLSX = ".xlsx"
EXT_PPTX = ".pptx"

# Data/Config extensions
EXT_XML = ".xml"
EXT_JSON = ".json"
EXT_YAML = ".yaml"
EXT_YML = ".yml"
EXT_TOML = ".toml"
EXT_INI = ".ini"
EXT_CFG = ".cfg"
EXT_CONF = ".conf"
EXT_PROPERTIES = ".properties"
EXT_ENV = ".env"
EXT_TXT = ".txt"

# Markup/Documentation extensions
EXT_MD = ".md"
EXT_MARKDOWN = ".markdown"
EXT_RST = ".rst"
EXT_TEX = ".tex"
EXT_LATEX = ".latex"

# Code extensions
EXT_PY = ".py"
EXT_JAVA = ".java"
EXT_JS = ".js"
EXT_TS = ".ts"

# Database extensions
EXT_SQL = ".sql"

# Grouped extension sets for validation
DOCUMENT_EXTENSIONS = [EXT_PDF, EXT_DOCX, EXT_XLSX, EXT_PPTX, EXT_XML, EXT_JSON, EXT_TXT]
CONFIG_EXTENSIONS = [EXT_YML, EXT_YAML, EXT_TOML, EXT_INI, EXT_CFG, EXT_CONF, EXT_PROPERTIES, EXT_ENV]
MARKUP_EXTENSIONS = [EXT_MD, EXT_MARKDOWN, EXT_RST, EXT_TEX, EXT_LATEX, EXT_SQL]

# ============================================================================
# Resource Path Segments
# ============================================================================

# Resource type names
RESOURCE_TYPE_ENTITY = "entity"
RESOURCE_TYPE_WORKFLOW = "workflow"
RESOURCE_TYPE_FUNCTIONAL_REQUIREMENTS = "functional_requirements"

# Version directory prefix
VERSION_DIR_PREFIX = "version_"

# ============================================================================
# Git Configuration
# ============================================================================

# Git commands
GIT_CMD = "git"
GIT_STATUS = "status"
GIT_CONFIG = "config"
GIT_ADD = "add"
GIT_COMMIT = "commit"
GIT_PUSH = "push"
GIT_REMOTE = "remote"
GIT_PULL = "pull"
GIT_CLONE = "clone"
GIT_CHECKOUT = "checkout"

# Git command arguments
GIT_PORCELAIN_FLAG = "--porcelain"
GIT_ALL_FILES = "."
GIT_ORIGIN = "origin"
GIT_GET_URL = "get-url"
GIT_COMMIT_MESSAGE_FLAG = "-m"

# Git user configuration
GIT_USER_NAME_KEY = "user.name"
GIT_USER_EMAIL_KEY = "user.email"
GIT_DEFAULT_USER_NAME = "Cyoda Agent"
GIT_DEFAULT_USER_EMAIL = "agent@cyoda.ai"

# ============================================================================
# CLI Providers
# ============================================================================

CLI_PROVIDER_AUGMENT = "augment"
CLI_PROVIDER_CLAUDE = "claude"
CLI_PROVIDER_GEMINI = "gemini"

SUPPORTED_CLI_PROVIDERS = [CLI_PROVIDER_AUGMENT, CLI_PROVIDER_CLAUDE, CLI_PROVIDER_GEMINI]

# ============================================================================
# Build Modes
# ============================================================================

BUILD_MODE_TEST = "test"
BUILD_MODE_PRODUCTION = "production"

# ============================================================================
# File Names
# ============================================================================

# Common file names in repositories
FILE_POM_XML = "pom.xml"
FILE_REQUIREMENTS_TXT = "requirements.txt"
FILE_PACKAGE_JSON = "package.json"
FILE_BUILD_GRADLE = "build.gradle"
FILE_SETUP_PY = "setup.py"
FILE_PYPROJECT_TOML = "pyproject.toml"

# ============================================================================
# Timeouts and Intervals (in seconds)
# ============================================================================

# CLI process timeouts
CLI_PROCESS_TIMEOUT = 3600  # 1 hour for code generation
BUILD_PROCESS_TIMEOUT = 1800  # 30 minutes for builds
COMMIT_TIMEOUT = 60  # 1 minute for commit/push operations
AUTH_REFRESH_TIMEOUT = 10  # 10 seconds for refreshing GitHub authentication
PROCESS_CHECK_INTERVAL = 10  # Check process status every 10 seconds

# Monitoring intervals
COMMIT_INTERVAL_DEFAULT = 30  # Commit progress every 30 seconds (code generation)
COMMIT_INTERVAL_BUILD = 60  # Commit progress every 60 seconds (builds)
PROGRESS_UPDATE_INTERVAL = 30  # Update task progress every 30 seconds

# Progress percentage bounds
PROGRESS_MAX_BEFORE_COMPLETION = 95  # Max progress before actual completion
PROGRESS_COMPLETE = 100

# ============================================================================
# Workflow Files
# ============================================================================

WORKFLOW_SCHEMA_FILENAME = "workflow_schema.json"
WORKFLOW_EXAMPLE_FILENAME = "ExampleEntity.json"
WORKFLOW_PROMPT_TEMPLATE = "workflow_prompt.template"

# ============================================================================
# UI Tab Names
# ============================================================================

TAB_ENTITIES = "entities"
TAB_WORKFLOWS = "workflows"
TAB_REQUIREMENTS = "requirements"
TAB_CLOUD = "cloud"

VALID_CANVAS_TABS = [TAB_ENTITIES, TAB_WORKFLOWS, TAB_REQUIREMENTS, TAB_CLOUD]

# ============================================================================
# Git Status Messages
# ============================================================================

GIT_MSG_NOTHING_TO_COMMIT = "nothing to commit"
GIT_MSG_WORKING_TREE_CLEAN = "working tree clean"

# Git status codes (from git status --porcelain)
GIT_STATUS_MODIFIED = "M"
GIT_STATUS_ADDED = "A"
GIT_STATUS_DELETED = "D"
GIT_STATUS_RENAMED = "R"
GIT_STATUS_COPIED = "C"
GIT_STATUS_UNTRACKED = "??"

# ============================================================================
# Diff Categories
# ============================================================================

DIFF_CATEGORY_MODIFIED = "modified"
DIFF_CATEGORY_ADDED = "added"
DIFF_CATEGORY_DELETED = "deleted"
DIFF_CATEGORY_UNTRACKED = "untracked"

# ============================================================================
# Repository Information
# ============================================================================

DEFAULT_REPO_OWNER = "Cyoda-platform"
PUBLIC_REPO_PYTHON = "mcp-cyoda-quart-app"
PUBLIC_REPO_JAVA = "java-client-template"

# ============================================================================
# Log File Naming
# ============================================================================

LOG_PREFIX_BUILD = "build_"
LOG_PREFIX_CODEGEN = "codegen_"
LOG_SUFFIX_TEMP = "_TEMP_"
LOG_EXTENSION = ".log"

# ============================================================================
# String Truncation Lengths
# ============================================================================

TRUNCATE_LENGTH_SHORT = 50  # For brief descriptions
TRUNCATE_LENGTH_MEDIUM = 100  # For medium-length text
TRUNCATE_LENGTH_LONG = 200  # For longer descriptions

# ============================================================================
# File Limit
# ============================================================================

MAX_CHANGED_FILES_IN_METADATA = 20  # Max files to include in task metadata

# ============================================================================
# Error Messages
# ============================================================================

# Error suffix to instruct LLM to stop on errors (imported from tools.py)
STOP_ON_ERROR = " STOP: Do not retry this operation. Report this error to the user and wait for instructions."
