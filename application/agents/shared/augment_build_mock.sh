#!/bin/bash
set -euo pipefail

# Mock Build Script for Testing
# Simulates Augment CLI by adding test lines to a file every 30 seconds, 3 times
# This avoids wasting tokens during testing
#
# Usage: ./augment_build_mock.sh <prompt> <model> [workspace_dir] [branch_id]

# Parse command line arguments
PROMPT_OR_FILE="${1:-}"
MODEL="${2:-haiku4.5}"
WORKSPACE_DIR="${3:-$(pwd)}"
BRANCH_ID="${4:-unknown}"

# Validate required arguments
if [[ -z "$PROMPT_OR_FILE" ]]; then
    echo "Error: prompt or prompt file path argument is required"
    exit 1
fi

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FILE="$WORKSPACE_DIR/TEST_BUILD_OUTPUT.txt"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$BRANCH_ID] $1"
}

log "Starting mock build script"
log "Workspace: $WORKSPACE_DIR"
log "Branch ID: $BRANCH_ID"

# Initialize test file
echo "Mock Build Started at $(date)" > "$TEST_FILE"
echo "Branch: $BRANCH_ID" >> "$TEST_FILE"
echo "---" >> "$TEST_FILE"

# Simulate 4 commits with 30-second intervals (120 seconds total = 2 minutes)
for i in {1..4}; do
    log "Mock build iteration $i/4..."

    # Add test content
    echo "Build iteration $i completed at $(date)" >> "$TEST_FILE"
    echo "  - Generated test files" >> "$TEST_FILE"
    echo "  - Compiled successfully" >> "$TEST_FILE"
    echo "" >> "$TEST_FILE"

    # Wait 30 seconds before next iteration (except on last iteration)
    if [[ $i -lt 4 ]]; then
        log "Waiting 30 seconds before next iteration..."
        sleep 30
    fi
done

log "Mock build completed successfully"
echo "Mock Build Completed at $(date)" >> "$TEST_FILE"

exit 0

