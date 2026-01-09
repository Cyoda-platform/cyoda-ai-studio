#!/usr/bin/env python3
"""Update eval template files with actual responses from eval results."""

import json
import sys
from pathlib import Path


def extract_response_from_result(result_file: Path) -> dict:
    """Extract the actual response from an eval result file."""
    with open(result_file, "r") as f:
        content = f.read()
        # The file is a JSON string wrapped in quotes, so load twice
        try:
            data = json.loads(json.loads(content))
        except:
            # If that doesn't work, try loading once
            data = json.loads(content)

    # Navigate to the actual response
    if "eval_case_results" in data and len(data["eval_case_results"]) > 0:
        case_result = data["eval_case_results"][0]
        if "eval_metric_result_per_invocation" in case_result:
            invocations = case_result["eval_metric_result_per_invocation"]
            if len(invocations) > 0:
                actual_invocation = invocations[0]["actual_invocation"]
                final_response = actual_invocation["final_response"]
                if "parts" in final_response and len(final_response["parts"]) > 0:
                    response_text = final_response["parts"][0]["text"]
                    return {
                        "success": True,
                        "response": response_text,
                        "eval_set_id": data["eval_set_id"],
                    }

    return {"success": False, "error": "Could not extract response from result file"}


def update_template_file(template_file: Path, response: str):
    """Update a template file with the actual response."""
    with open(template_file, "r") as f:
        data = json.load(f)

    # Update the response in the first eval case
    if "eval_cases" in data and len(data["eval_cases"]) > 0:
        eval_case = data["eval_cases"][0]
        if "conversation" in eval_case and len(eval_case["conversation"]) > 0:
            conversation = eval_case["conversation"][0]
            conversation["final_response"]["parts"][0]["text"] = response

    # Write updated template
    with open(template_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Updated: {template_file.name}")


def main():
    """Main entry point."""
    # Paths
    base_dir = Path(__file__).parent.parent
    eval_history_dir = base_dir.parent / ".adk" / "eval_history"
    templates_dir = base_dir / "evals" / "scenarios"

    # Find all result files
    result_files = list(eval_history_dir.glob("*github_scenario*.json"))

    if not result_files:
        print("❌ No eval result files found")
        sys.exit(1)

    print(f"Found {len(result_files)} eval result files\n")

    # Process each result file
    updated_count = 0
    for result_file in result_files:
        print(f"Processing: {result_file.name}")

        # Extract response
        result = extract_response_from_result(result_file)

        if not result["success"]:
            print(f"  ⚠️  {result['error']}")
            continue

        # Find corresponding template file
        eval_set_id = result["eval_set_id"]
        template_file = templates_dir / f"{eval_set_id}.evalset.json"

        if not template_file.exists():
            print(f"  ⚠️  Template file not found: {template_file.name}")
            continue

        # Update template
        update_template_file(template_file, result["response"])
        updated_count += 1

    print(f"\n{'='*60}")
    print(f"Updated {updated_count} eval template files")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
