#!/bin/bash
set -euo pipefail

# Gemini CLI Automation Script for Cyoda Client Application Generation
#
# This script generates code using Gemini CLI (https://github.com/google-gemini/gemini-cli)
# based on functional requirements and entity definitions.
#
# Requirements:
#   - Gemini CLI installed (npm install -g @google/generative-ai-cli)
#   - GEMINI_API_KEY environment variable set
#
# Usage: ./gemini_build.sh <prompt> <model> [workspace_dir] [branch_id]

# Parse command line arguments
PROMPT_OR_FILE="${1:-}"
MODEL="${2:-gemini-2.0-flash-exp}"
WORKSPACE_DIR="${3:-$(pwd)}"
BRANCH_ID="${4:-unknown}"

# Validate required arguments
if [[ -z "$PROMPT_OR_FILE" ]]; then
    echo "Error: prompt or prompt file path argument is required"
    echo "Usage: $0 <prompt_or_file_path> <model> [workspace_dir] [branch_id]"
    echo "  - If argument starts with '@', it's treated as a file path (e.g., @/path/to/prompt.txt)"
    echo "  - Otherwise, it's treated as the prompt text directly"
    exit 1
fi

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$BRANCH_ID] $1"
}

# Check if Gemini CLI is installed
if ! command -v gemini &> /dev/null; then
    log "ERROR: Gemini CLI not found. Please install it:"
    log "  npm install -g @google/generative-ai-cli"
    exit 1
fi

# Check authentication
# Gemini CLI can use either:
# 1. Logged-in session (stored in ~/.gemini/) - like Claude/Augment
# 2. API key via GEMINI_API_KEY or GOOGLE_API_KEY environment variables

if [[ -z "${GEMINI_API_KEY:-}" ]] && [[ -z "${GOOGLE_API_KEY:-}" ]]; then
    # No API key provided - check if user is logged in
    if [[ -f ~/.gemini/oauth_creds.json ]]; then
        log "Using Gemini CLI with logged-in credentials from ~/.gemini/"
    else
        log "WARNING: No API key set and no logged-in session found"
        log "Gemini CLI will try to use default authentication"
        log ""
        log "To authenticate, either:"
        log "  1. Use logged-in session: gemini (then login interactively)"
        log "  2. Set API key: export GOOGLE_API_KEY='your-key'"
    fi
else
    # API key provided
    if [[ -n "${GEMINI_API_KEY:-}" ]]; then
        log "Using GEMINI_API_KEY for authentication"
    else
        export GEMINI_API_KEY="$GOOGLE_API_KEY"
        log "Using GOOGLE_API_KEY for authentication"
    fi
fi

# Determine if it's a file path or direct prompt
if [[ "$PROMPT_OR_FILE" == @* ]]; then
    # It's a file path (remove the @ prefix)
    PROMPT_FILE="${PROMPT_OR_FILE#@}"

    if [[ ! -f "$PROMPT_FILE" ]]; then
        echo "Error: Prompt file not found: $PROMPT_FILE"
        exit 1
    fi

    # Read prompt from file
    PROMPT="$(cat "$PROMPT_FILE")"
    log "Using prompt from file: $PROMPT_FILE"
else
    # It's a direct prompt
    PROMPT="$PROMPT_OR_FILE"
    log "Using direct prompt"
fi

# Set up environment for automation
setup_environment() {
    log "Setting up automation environment..."

    export CI=true
    export TERM=dumb
    export NO_COLOR=1
    export FORCE_COLOR=0
    export NODE_ENV=production

    log "Environment configured for automation"
}

# Main CLI execution
execute_gemini() {
    local workspace="$1"
    local instruction="$2"
    local model="$3"
    local timeout_seconds=3600  # 1 hour

    log "Starting Gemini CLI execution in workspace: $workspace"
    log "Model: $model"

    cd "$workspace"

    log "Executing Gemini CLI with automation flags..."

    # Execute Gemini CLI with 1-hour timeout
    # --yolo: Automatically accept all actions (non-interactive mode)
    # --model: Specify the model to use (optional - CLI will use default if not set)
    # Piping the prompt via stdin

    # Build command with optional model flag
    local cmd="timeout --foreground $timeout_seconds gemini --yolo"

    # Only add --model flag if model is not empty and not "default"
    if [[ -n "$model" ]] && [[ "$model" != "default" ]]; then
        cmd="$cmd --model $model"
        log "Using model: $model"
    else
        log "Using Gemini CLI default model"
    fi

    # Execute command with heredoc for prompt
    bash -c "$cmd" <<EOF
$instruction
EOF

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log "Gemini CLI execution completed successfully"
    elif [[ $exit_code -eq 124 ]]; then
        log "ERROR: Gemini CLI execution timed out after 1 hour"
        return 124
    else
        log "ERROR: Gemini CLI execution failed with exit code $exit_code"
        return $exit_code
    fi
}

# Main execution
main() {
    log "Starting Gemini CLI automation script"
    log "PROMPT_OR_FILE argument: $PROMPT_OR_FILE"
    log "Prompt: ${PROMPT:0:100}$([ ${#PROMPT} -gt 100 ] && echo '...')"
    log "Model: $MODEL"
    log "Workspace: $WORKSPACE_DIR"
    log "Branch ID: $BRANCH_ID"

    setup_environment

    # Execute Gemini CLI (git operations are handled by Python code)
    execute_gemini "$WORKSPACE_DIR" "$PROMPT" "$MODEL"
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log "Gemini CLI automation script completed successfully"
        exit 0
    else
        log "Gemini CLI automation script failed with exit code $exit_code"
        exit $exit_code
    fi
}

# Execute main function
main "$@"
