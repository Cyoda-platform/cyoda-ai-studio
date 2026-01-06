"""Constants used across repository tools."""

import os
from pathlib import Path

# Constants for conversation locking
MAX_LOCK_RETRIES = 10
INITIAL_RETRY_DELAY_SECONDS = 0.2
MAX_RETRY_DELAY_SECONDS = 2.0

# Constants for error messages
UNKNOWN_ERROR_MESSAGE = "Unknown error"

# Constants for process monitoring
PROCESS_CHECK_INTERVAL_SECONDS = 10
PROCESS_COMMIT_INTERVAL_SECONDS = 60
DEFAULT_BUILD_TIMEOUT_SECONDS = 1800
PROCESS_KILL_GRACE_SECONDS = 5

# Constants for output streaming
OUTPUT_UPDATE_SIZE_THRESHOLD = 1024
OUTPUT_UPDATE_TIME_THRESHOLD_SECONDS = 5.0

# Protected branches that should never be used for builds
PROTECTED_BRANCHES = {"main", "master", "develop", "development", "production", "prod"}

# Template repository URLs (used for cloning the initial template)
JAVA_TEMPLATE_REPO = "https://github.com/Cyoda-platform/java-client-template"
PYTHON_TEMPLATE_REPO = "https://github.com/Cyoda-platform/mcp-cyoda-quart-app"

# GitHub configuration from environment
# Public repository URLs (where we push the code for public builds)
PYTHON_PUBLIC_REPO_URL = os.getenv("PYTHON_PUBLIC_REPO_URL", PYTHON_TEMPLATE_REPO)
JAVA_PUBLIC_REPO_URL = os.getenv("JAVA_PUBLIC_REPO_URL", JAVA_TEMPLATE_REPO)
GITHUB_PUBLIC_REPO_INSTALLATION_ID = os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID")

# Module directory and script paths
_MODULE_DIR = Path(__file__).parent.parent
_DEFAULT_SCRIPT = _MODULE_DIR / "augment_build_mock.sh"
AUGMENT_CLI_SCRIPT = os.getenv("AUGMENT_CLI_SCRIPT", str(_DEFAULT_SCRIPT))
