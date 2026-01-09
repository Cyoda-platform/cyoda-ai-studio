#!/bin/bash
# Run all environment scenario evals and update templates with actual responses

set -e

export DISABLE_MCP_TOOLSET=true
export MOCK_ALL_TOOLS=true

SCENARIO_DIR="application/agents/environment/evals/scenarios"
CONFIG_FILE="application/agents/tests/evals/test_config.json"

# Get all scenario files
SCENARIOS=($(ls $SCENARIO_DIR/*.evalset.json | xargs -n1 basename | sed 's/.evalset.json//'))

echo "Running ${#SCENARIOS[@]} environment scenarios..."
echo ""

# Run scenarios one by one
for i in "${!SCENARIOS[@]}"; do
  SCENARIO="${SCENARIOS[$i]}"
  echo "[$((i+1))/${#SCENARIOS[@]}] Running: $SCENARIO"

  timeout 120 adk eval application/agents \
    "$SCENARIO_DIR/$SCENARIO.evalset.json" \
    --config_file_path "$CONFIG_FILE" 2>&1 | grep -E "(passed|failed|Writing eval result)" || true

  echo ""
done

echo "============================================"
echo "All scenarios complete. Updating templates..."
echo "============================================"
echo ""

# Update templates with captured responses
python application/agents/environment/evals/update_eval_templates_from_results.py

echo ""
echo "✅ Done! All environment scenario eval files have been generated and updated with actual agent responses."
