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

# Function to commit and push changes
commit_and_push() {
    local workspace="$1"
    local branch_id="$2"

    cd "$workspace"

    # Check if there are any changes to commit
    if ! git diff --quiet || ! git diff --cached --quiet; then
        # Stage changes
        if ! git add . 2>&1; then
            log "WARNING: git add failed"
            return 1
        fi

        # Commit changes
        local commit_output
        commit_output=$(git commit -m "Code generation progress with Augment CLI (branch: $branch_id)" 2>&1)
        local commit_exit=$?

        if [[ $commit_exit -ne 0 ]]; then
            # Exit code 1 means nothing to commit, which is fine
            if [[ $commit_exit -eq 1 ]]; then
                log "DEBUG: No changes to commit"
            else
                log "WARNING: git commit failed: $commit_output"
                return 1
            fi
        fi

        # Push changes
        local push_output
        push_output=$(git push origin HEAD 2>&1)
        local push_exit=$?

        if [[ $push_exit -ne 0 ]]; then
            log "ERROR: git push failed with exit code $push_exit: $push_output"
            return 1
        else
            log "SUCCESS: Changes pushed to remote"
        fi
    else
        log "DEBUG: No changes to commit"
    fi
}

# Main CLI execution with guaranteed periodic commits every 30 seconds
execute_auggie() {
    local workspace="$1"
    local instruction="$2"
    local model="$3"
    local branch_id="$4"
    local push_interval=30  # Push every 30 seconds
    local timeout_seconds=3600  # 1 hour

    log "Starting CLI execution in workspace: $workspace"
    log "Model: $model"

    cd "$workspace"

    log "Executing CLI with automation flags..."

    # Execute CLI in background to allow periodic commits
    timeout --foreground "$timeout_seconds" auggie --print --model "$model" --workspace-root "$workspace" "$instruction" &
    local cli_pid=$!

    log "CLI process started with PID: $cli_pid"
    log "Will push changes every $push_interval seconds"

    # Track time for guaranteed 30-second intervals
    local start_time=$(date +%s)
    local last_push_time=$start_time

    # Periodically commit and push changes every 30 seconds while CLI is running
    while kill -0 $cli_pid 2>/dev/null; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - last_push_time))

        # If 30 seconds have passed, push changes
        if [[ $elapsed -ge $push_interval ]]; then
            log "Pushing progress commit (elapsed: ${elapsed}s)..."
            commit_and_push "$workspace" "$branch_id"
            last_push_time=$(date +%s)
        else
            # Sleep only for the remaining time until next push
            local sleep_time=$((push_interval - elapsed))
            sleep "$sleep_time"
        fi
    done

    # Wait for CLI process to complete and get exit code
    wait $cli_pid
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

    # Execute CLI with guaranteed periodic commits every 30 seconds
    execute_auggie "$WORKSPACE_DIR" "$PROMPT" "$MODEL" "$BRANCH_ID"
    local exit_code=$?

    if [[ $exit_code -eq 124 ]]; then
        log "ERROR: CLI execution timed out after 1 hour"
        exit 124
    elif [[ $exit_code -eq 0 ]]; then
        log "CLI execution completed successfully"

        # Final commit and push
        log "Pushing final changes..."
        cd "$WORKSPACE_DIR"

        local final_push_output
        final_push_output=$(git add . 2>&1)

        local final_commit_output
        final_commit_output=$(git commit -m "Code generation completed with Augment CLI (branch: $BRANCH_ID)" 2>&1)

        local final_push_result
        final_push_result=$(git push origin HEAD 2>&1)
        local final_push_exit=$?

        if [[ $final_push_exit -eq 0 ]]; then
            log "Code committed and pushed successfully"
        else
            log "WARNING: Final push may have failed: $final_push_result"
        fi
    else
        log "ERROR: CLI execution failed with exit code $exit_code"
        exit $exit_code
    fi

    log "CLI automation script completed successfully"
}

# Execute main function
main "$@"
