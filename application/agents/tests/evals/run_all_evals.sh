#!/bin/bash
set -e

# Cyoda AI Assistant - Run All Evaluations
# Runs all ADK eval sets and generates unified HTML report

echo "🧪 Running Cyoda AI Assistant Evaluations..."
echo "============================================="
echo ""

# Set required environment variables
export DISABLE_MCP_TOOLSET=true
export MOCK_ALL_TOOLS=true

# Get absolute paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
AGENT_DIR="$PROJECT_ROOT/application/agents"
EVAL_DIR="$SCRIPT_DIR"
HISTORY_DIR="$AGENT_DIR/.adk/eval_history"
REPORT_FILE="$EVAL_DIR/unified_report.html"

echo "📂 Project root: $PROJECT_ROOT"
echo "📂 Eval directory: $EVAL_DIR"
echo "📂 Results directory: $HISTORY_DIR"
echo ""

# Run all evaluations
echo "▶️  Running evaluations..."
echo ""

adk eval "$AGENT_DIR" \
  "$AGENT_DIR/coordinator/evals/"*.evalset.json \
  "$AGENT_DIR/environment/evals/"*.evalset.json \
  "$AGENT_DIR/qa/evals/"*.evalset.json \
  "$AGENT_DIR/github/evals/"*.evalset.json \
  --config_file_path "$EVAL_DIR/test_config.json" \
  --print_detailed_results

echo ""
echo "============================================="
echo "📊 Generating unified HTML report..."
echo ""

# Generate unified HTML report from all results
python "$EVAL_DIR/generate_html_report.py" \
  "$HISTORY_DIR"/*.evalset_result.json \
  -o "$REPORT_FILE"

echo ""
echo "============================================="
echo "✅ Evaluation Complete!"
echo ""
echo "📄 Report: $REPORT_FILE"
echo "🌐 Open with: xdg-open $REPORT_FILE"
echo ""

# Try to open report in browser (Linux)
if command -v xdg-open &> /dev/null; then
  echo "🚀 Opening report in browser..."
  xdg-open "$REPORT_FILE" 2>/dev/null || true
fi

# Exit with success
exit 0
