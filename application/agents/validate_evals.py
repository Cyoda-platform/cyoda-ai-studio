#!/usr/bin/env python3
"""Validate all evaluation JSON files."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def validate_test_config(file_path: Path) -> tuple[bool, str]:
    """Validate test_config.json file."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        if "criteria" not in data:
            return False, 'Missing "criteria" key'

        criteria = data["criteria"]
        required_metrics = [
            "tool_trajectory_avg_score",
            "response_match_score",
            "final_response_match_v2",
        ]

        for metric in required_metrics:
            if metric not in criteria:
                return False, f"Missing metric: {metric}"

            value = criteria[metric]
            if not isinstance(value, (int, float)) or not 0 <= value <= 1:
                return False, f"Invalid value for {metric}: {value} (must be 0-1)"

        return True, "Valid"

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def validate_test_file(file_path: Path) -> tuple[bool, str]:
    """Validate .test.json file."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        # Check required top-level keys
        required_keys = ["eval_set_id", "name", "eval_cases"]
        for key in required_keys:
            if key not in data:
                return False, f"Missing required key: {key}"

        # Check eval_cases
        if not isinstance(data["eval_cases"], list):
            return False, "eval_cases must be a list"

        if len(data["eval_cases"]) == 0:
            return False, "eval_cases is empty"

        # Validate each eval case
        for i, case in enumerate(data["eval_cases"]):
            if "eval_id" not in case:
                return False, f"Case {i}: missing eval_id"

            if "conversation" not in case:
                return False, f"Case {i}: missing conversation"

            if not isinstance(case["conversation"], list):
                return False, f"Case {i}: conversation must be a list"

            # Validate each invocation
            for j, invocation in enumerate(case["conversation"]):
                if "user_content" not in invocation:
                    return False, f"Case {i}, invocation {j}: missing user_content"

                if "final_response" not in invocation:
                    return False, f"Case {i}, invocation {j}: missing final_response"

                if "intermediate_data" not in invocation:
                    return False, f"Case {i}, invocation {j}: missing intermediate_data"

                # Check tool_uses
                intermediate = invocation["intermediate_data"]
                if "tool_uses" not in intermediate:
                    return False, f"Case {i}, invocation {j}: missing tool_uses"

                if not isinstance(intermediate["tool_uses"], list):
                    return False, f"Case {i}, invocation {j}: tool_uses must be a list"

                # Validate each tool use
                for k, tool_use in enumerate(intermediate["tool_uses"]):
                    if "name" not in tool_use:
                        return (
                            False,
                            f"Case {i}, invocation {j}, tool {k}: missing tool name",
                        )

                    if "args" not in tool_use:
                        return (
                            False,
                            f"Case {i}, invocation {j}, tool {k}: missing tool args",
                        )

        num_cases = len(data["eval_cases"])
        return True, f"Valid ({num_cases} cases)"

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    """Validate all evaluation files."""
    agents_dir = Path("application/agents")

    if not agents_dir.exists():
        print(f"❌ Directory not found: {agents_dir}")
        sys.exit(1)

    print("🔍 Validating evaluation files...\n")

    all_valid = True
    total_files = 0
    total_cases = 0

    # Find all eval directories
    for agent_dir in agents_dir.iterdir():
        if not agent_dir.is_dir():
            continue

        evals_dir = agent_dir / "evals"
        if not evals_dir.exists():
            continue

        print(f"📁 {agent_dir.name}/evals/")

        # Validate test_config.json
        test_config = evals_dir / "test_config.json"
        if test_config.exists():
            valid, message = validate_test_config(test_config)
            status = "✅" if valid else "❌"
            print(f"  {status} test_config.json - {message}")
            total_files += 1
            if not valid:
                all_valid = False
        else:
            print("  ⚠️  test_config.json - Missing")
            all_valid = False

        # Validate .test.json files
        for test_file in sorted(evals_dir.glob("*.test.json")):
            valid, message = validate_test_file(test_file)
            status = "✅" if valid else "❌"
            print(f"  {status} {test_file.name} - {message}")
            total_files += 1

            if valid and "cases)" in message:
                # Extract number of cases
                num_cases = int(message.split("(")[1].split()[0])
                total_cases += num_cases

            if not valid:
                all_valid = False

        print()

    print(f"\n📊 Summary:")
    print(f"  Total files: {total_files}")
    print(f"  Total test cases: {total_cases}")

    if all_valid:
        print("\n✅ All evaluation files are valid!")
        sys.exit(0)
    else:
        print("\n❌ Some evaluation files have errors!")
        sys.exit(1)


if __name__ == "__main__":
    main()
