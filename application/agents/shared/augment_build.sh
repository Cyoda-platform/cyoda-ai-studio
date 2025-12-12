#!/bin/bash
set -euo pipefail

# CLI Automation Script for Cyoda Client Application Generation
# Following https://docs.augmentcode.com/cli/automation best practices
# 
# This script generates controllers, processors, and criteria for a Cyoda client application
# based on functional requirements and entity definitions.
#
# Usage: ./auggie_example.sh <prompt> <model> [workspace_dir] [branch_id]

# Parse command line arguments
PROMPT_OR_FILE="${1:-}"
MODEL="${2:-haiku4.5}"
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

# Set up environment for automation (following official docs)
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
execute_auggie() {
    local workspace="$1"
    local instruction="$2"
    local model="$3"
    
    log "Starting CLI execution in workspace: $workspace"
    log "Model: $model"
    
    cd "$workspace"
    
    log "Executing CLI with automation flags..."

    # Execute CLI following automation best practices
    # Use the prompt passed as argument instead of hardcoded instruction
    auggie --print --model "$model" --workspace-root "$workspace" "$instruction"
    
    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log "CLI execution completed successfully"
    else
        log "ERROR: CLI execution failed with exit code $exit_code"
        return $exit_code
    fi
}

# Main execution
main() {
    log "Starting CLI automation script"
    log "Prompt: ${PROMPT:0:100}$([ ${#PROMPT} -gt 100 ] && echo '...')"
    log "Model: $MODEL"
    log "Workspace: $WORKSPACE_DIR"
    log "Branch ID: $BRANCH_ID"

    setup_environment

    # Run CLI with a 1-hour timeout
    timeout --foreground 1h auggie --print --model "$MODEL" --workspace-root "$WORKSPACE_DIR" "$PROMPT"
    local exit_code=$?

    if [[ $exit_code -eq 124 ]]; then
        log "ERROR: CLI execution timed out after 1 hour"
        exit 124
    elif [[ $exit_code -eq 0 ]]; then
        log "CLI execution completed successfully"
    else
        log "ERROR: CLI execution failed with exit code $exit_code"
        exit $exit_code
    fi

    log "CLI automation script completed successfully"
}

# Execute main function
main "$@"
