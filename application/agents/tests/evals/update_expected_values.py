#!/usr/bin/env python3
"""
Update expected values in evalset.json based on actual results from evaluation run.
This script reads the evaluation results and updates the expected values in the evalset file.
"""

import json
import sys
from pathlib import Path


def extract_tools_from_events(invocation_events):
    """Extract tool calls from invocation events."""
    tools = []
    for event in invocation_events:
        if event.get("content", {}).get("role") == "model":
            parts = event.get("content", {}).get("parts", [])
            for part in parts:
                if "function_call" in part and part["function_call"]:
                    fc = part["function_call"]
                    tools.append(
                        {
                            "id": None,
                            "args": fc.get("args", {}),
                            "name": fc["name"],
                            "partial_args": None,
                            "will_continue": None,
                        }
                    )
    return tools


def update_evalset_from_results(results_file, evalset_file):
    """Update evalset.json with actual results from the evaluation run."""

    # Read results file
    with open(results_file, "r") as f:
        content = f.read().strip()
        # Handle JSON string wrapping
        if content.startswith('"') and content.endswith('"'):
            content = json.loads(content)
        results = json.loads(content) if isinstance(content, str) else content

    # Read evalset file
    with open(evalset_file, "r") as f:
        evalset = json.load(f)

    # Create a mapping of eval_id to actual results
    actual_results = {}
    for case_result in results.get("eval_case_results", []):
        eval_id = case_result["eval_id"]
        actual_results[eval_id] = case_result

    # Update each test case in the evalset
    updated_count = 0
    for eval_case in evalset["eval_cases"]:
        eval_id = eval_case["eval_id"]

        if eval_id not in actual_results:
            print(f"⚠️  No results found for {eval_id}, skipping")
            continue

        actual_case = actual_results[eval_id]
        actual_invocations = actual_case.get("eval_metric_result_per_invocation", [])
        expected_invocations = eval_case["conversation"]

        # Update each invocation
        for idx, expected_inv in enumerate(expected_invocations):
            if idx >= len(actual_invocations):
                print(f"⚠️  {eval_id}: No actual data for invocation {idx+1}")
                continue

            actual_inv = actual_invocations[idx]["actual_invocation"]

            # Update final response text
            if actual_inv.get("final_response", {}).get("parts"):
                actual_text = actual_inv["final_response"]["parts"][0].get("text", "")
                expected_inv["final_response"]["parts"][0]["text"] = actual_text

            # Update intermediate_data tools
            if (
                "intermediate_data" in actual_inv
                and "invocation_events" in actual_inv["intermediate_data"]
            ):
                tools = extract_tools_from_events(
                    actual_inv["intermediate_data"]["invocation_events"]
                )
                expected_inv["intermediate_data"]["tool_uses"] = tools

            print(f"✅ Updated {eval_id} invocation {idx+1}")
            updated_count += 1

    # Write updated evalset
    with open(evalset_file, "w") as f:
        json.dump(evalset, f, indent=2)

    print(f"\n✅ Updated {updated_count} invocations in {evalset_file}")
    return updated_count


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python update_expected_values.py <results_file> <evalset_file>")
        sys.exit(1)

    results_file = Path(sys.argv[1])
    evalset_file = Path(sys.argv[2])

    if not results_file.exists():
        print(f"❌ Results file not found: {results_file}")
        sys.exit(1)

    if not evalset_file.exists():
        print(f"❌ Evalset file not found: {evalset_file}")
        sys.exit(1)

    update_evalset_from_results(results_file, evalset_file)
