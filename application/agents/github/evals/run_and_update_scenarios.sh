#!/bin/bash
# Run all scenario evals and update templates with actual responses

set -e

export DISABLE_MCP_TOOLSET=true
export MOCK_ALL_TOOLS=true

SCENARIO_DIR="application/agents/github/evals/scenarios"
CONFIG_FILE="application/agents/tests/evals/test_config.json"

# Get all scenario files (excluding the 3 already processed)
SCENARIOS=(
  "github_scenario_add_rest_endpoints_for_product_entity_with_get_pos"
  "github_scenario_add_a_discount_feature_to_orders"
  "github_scenario_add_a_requirement_document_to_the_repository_for_a"
  "github_scenario_build_an_application_based_on_the_docs_in_this_bra"
  "github_scenario_build_an_application_based_on_the_attached_require"
  "github_scenario_view_edit_the_customer_entity_in_the_canvas"
  "github_scenario_view_edit_the_order_workflow_in_the_canvas"
  "github_scenario_view_edit_the_requirement_document_in_the_canvas"
)

echo "Running ${#SCENARIOS[@]} scenarios..."
echo ""

# Run scenarios in batches of 4 to avoid timeout
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
python application/agents/github/evals/update_eval_templates_from_results.py

echo ""
echo "✅ Done! All scenario eval files have been generated and updated with actual agent responses."
