#!/bin/bash
# View and analyze ADK evaluation results

set -e

RESULTS_DIR="application/agents/eval_results"

if [ ! -d "$RESULTS_DIR" ]; then
    echo "❌ Results directory not found: $RESULTS_DIR"
    exit 1
fi

# Get the latest results file
LATEST_FILE=$(ls -t "$RESULTS_DIR"/*.json 2>/dev/null | head -1)

if [ -z "$LATEST_FILE" ]; then
    echo "❌ No results files found in $RESULTS_DIR"
    exit 1
fi

echo "📊 ADK EVALUATION RESULTS"
echo "=========================="
echo ""
echo "📁 File: $LATEST_FILE"
echo "📅 Modified: $(date -r "$LATEST_FILE" '+%Y-%m-%d %H:%M:%S')"
echo ""

# Parse and display results
echo "📈 Results Summary:"
echo "---"

# Extract test case status
jq -r '.test_cases[] | "\(.status): \(.name)"' "$LATEST_FILE" | while read line; do
    if [[ $line == PASSED* ]]; then
        echo "✅ $line"
    else
        echo "❌ $line"
    fi
done

echo ""
echo "📋 Full Results (JSON):"
echo "---"
jq . "$LATEST_FILE"

echo ""
echo "💡 To view all results files:"
echo "   ls -lt $RESULTS_DIR"
echo ""
echo "💡 To view a specific file:"
echo "   jq . $RESULTS_DIR/eval_results_YYYYMMDD_HHMMSS.json"

