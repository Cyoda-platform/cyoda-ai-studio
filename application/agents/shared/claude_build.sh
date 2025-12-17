#!/bin/bash
set -euo pipefail

# Claude CLI Automation Script for Cyoda Client Application Generation
#
# This script generates code using Claude CLI in non-interactive mode
# based on functional requirements and entity definitions.
#
# Usage: ./claude_build.sh <prompt> <model> [workspace_dir] [branch_id]

# Parse command line arguments
PROMPT_OR_FILE="${1:-}"
MODEL="${2:-sonnet}"
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
execute_claude() {
    local workspace="$1"
    local instruction="$2"
    local model="$3"
    # Configurable timeout (default: 1 hour = 3600 seconds)
    local timeout_seconds="${CLAUDE_TIMEOUT_SECONDS:-3600}"

    log "Starting Claude CLI execution in workspace: $workspace"
    log "Model: $model"

    cd "$workspace"

    log "Executing Claude CLI with automation flags..."

    # Execute Claude CLI with 1-hour timeout
    # --print: Non-interactive mode
    # --output-format text: Plain text output (can be changed to json if needed)
    # --permission-mode acceptEdits: Auto-accept file edit permissions
    # --allowed-tools: Whitelist specific tools
    # --model: Optional - Claude CLI will use default if not specified
    # Prompt is piped via stdin to avoid command-line length limits

    # Build command with optional model flag
    # Configurable budget/tool call limit (default: 100)
    local max_tool_calls="${CLAUDE_MAX_TOOL_CALLS:-100}"
    local budget_prompt="You have a maximum budget of $max_tool_calls tool calls for this task. Track your progress and complete the task efficiently within this limit. If you approach the limit, prioritize the most critical work."

    local cmd="timeout --foreground $timeout_seconds claude --print --output-format text --permission-mode acceptEdits --allowed-tools \"Bash Read Write Edit Glob Grep\""

    # Only add budget prompt if max_tool_calls is set (not "0" or "unlimited")
    if [[ "$max_tool_calls" != "0" ]] && [[ "$max_tool_calls" != "unlimited" ]]; then
        cmd="$cmd --append-system-prompt \"$budget_prompt\""
        log "Tool call budget: $max_tool_calls"
    fi

    # Only add --model flag if model is not empty and not "default"
    if [[ -n "$model" ]] && [[ "$model" != "default" ]]; then
        cmd="$cmd --model $model"
        log "Using model: $model"
    else
        log "Using Claude CLI default model"
    fi

    # Execute command with heredoc for prompt
    eval "$cmd" <<EOF
$instruction
EOF

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log "Claude CLI execution completed successfully"
    elif [[ $exit_code -eq 124 ]]; then
        log "ERROR: Claude CLI execution timed out after ${timeout_seconds}s ($(($timeout_seconds / 60)) minutes)"
        return 124
    else
        log "ERROR: Claude CLI execution failed with exit code $exit_code"
        return $exit_code
    fi
}

# Main execution
main() {
    log "Starting Claude CLI automation script"
    log "PROMPT_OR_FILE argument: $PROMPT_OR_FILE"
    log "Prompt: ${PROMPT:0:100}$([ ${#PROMPT} -gt 100 ] && echo '...')"
    log "Model: $MODEL"
    log "Workspace: $WORKSPACE_DIR"
    log "Branch ID: $BRANCH_ID"

    setup_environment

    # Execute Claude CLI (git operations are handled by Python code)
    execute_claude "$WORKSPACE_DIR" "$PROMPT" "$MODEL"
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log "Claude CLI automation script completed successfully"
        exit 0
    else
        log "Claude CLI automation script failed with exit code $exit_code"
        exit $exit_code
    fi
}

# Execute main function
main "$@"
