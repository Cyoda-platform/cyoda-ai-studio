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


def _validate_eval_cases_structure(eval_cases: any) -> tuple[bool, str]:
    """Validate eval_cases structure.

    Args:
        eval_cases: eval_cases data

    Returns:
        Tuple of (valid, error_message)
    """
    if not isinstance(eval_cases, list):
        return False, "eval_cases must be a list"

    if len(eval_cases) == 0:
        return False, "eval_cases is empty"

    return True, ""


def _validate_tool_uses(intermediate: dict, case_idx: int, inv_idx: int) -> tuple[bool, str]:
    """Validate tool_uses in intermediate data.

    Args:
        intermediate: Intermediate data
        case_idx: Case index
        inv_idx: Invocation index

    Returns:
        Tuple of (valid, error_message)
    """
    if "tool_uses" not in intermediate:
        return False, f"Case {case_idx}, invocation {inv_idx}: missing tool_uses"

    if not isinstance(intermediate["tool_uses"], list):
        return False, f"Case {case_idx}, invocation {inv_idx}: tool_uses must be a list"

    for k, tool_use in enumerate(intermediate["tool_uses"]):
        if "name" not in tool_use:
            return False, f"Case {case_idx}, invocation {inv_idx}, tool {k}: missing tool name"

        if "args" not in tool_use:
            return False, f"Case {case_idx}, invocation {inv_idx}, tool {k}: missing tool args"

    return True, ""


def _validate_invocation(invocation: dict, case_idx: int, inv_idx: int) -> tuple[bool, str]:
    """Validate single invocation.

    Args:
        invocation: Invocation data
        case_idx: Case index
        inv_idx: Invocation index

    Returns:
        Tuple of (valid, error_message)
    """
    required_keys = ["user_content", "final_response", "intermediate_data"]
    for key in required_keys:
        if key not in invocation:
            return False, f"Case {case_idx}, invocation {inv_idx}: missing {key}"

    return _validate_tool_uses(invocation["intermediate_data"], case_idx, inv_idx)


def _validate_eval_case(case: dict, case_idx: int) -> tuple[bool, str]:
    """Validate single eval case.

    Args:
        case: Case data
        case_idx: Case index

    Returns:
        Tuple of (valid, error_message)
    """
    if "eval_id" not in case:
        return False, f"Case {case_idx}: missing eval_id"

    if "conversation" not in case:
        return False, f"Case {case_idx}: missing conversation"

    if not isinstance(case["conversation"], list):
        return False, f"Case {case_idx}: conversation must be a list"

    for j, invocation in enumerate(case["conversation"]):
        valid, error = _validate_invocation(invocation, case_idx, j)
        if not valid:
            return False, error

    return True, ""


def validate_test_file(file_path: Path) -> tuple[bool, str]:
    """Validate .test.json file."""
    try:
        with open(file_path) as f:
            data = json.load(f)

        required_keys = ["eval_set_id", "name", "eval_cases"]
        for key in required_keys:
            if key not in data:
                return False, f"Missing required key: {key}"

        valid, error = _validate_eval_cases_structure(data["eval_cases"])
        if not valid:
            return False, error

        for i, case in enumerate(data["eval_cases"]):
            valid, error = _validate_eval_case(case, i)
            if not valid:
                return False, error

        num_cases = len(data["eval_cases"])
        return True, f"Valid ({num_cases} cases)"

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def _validate_test_config_file(evals_dir: Path) -> tuple[bool, int]:
    """Validate test_config.json file.

    Args:
        evals_dir: Evaluation directory

    Returns:
        Tuple of (all_valid, total_files)
    """
    test_config = evals_dir / "test_config.json"
    total_files = 0

    if test_config.exists():
        valid, message = validate_test_config(test_config)
        status = "✅" if valid else "❌"
        print(f"  {status} test_config.json - {message}")
        total_files = 1
        return valid, total_files

    print("  ⚠️  test_config.json - Missing")
    return False, 0


def _validate_test_files(evals_dir: Path) -> tuple[bool, int, int]:
    """Validate all .test.json files.

    Args:
        evals_dir: Evaluation directory

    Returns:
        Tuple of (all_valid, total_files, total_cases)
    """
    all_valid = True
    total_files = 0
    total_cases = 0

    for test_file in sorted(evals_dir.glob("*.test.json")):
        valid, message = validate_test_file(test_file)
        status = "✅" if valid else "❌"
        print(f"  {status} {test_file.name} - {message}")
        total_files += 1

        if valid and "cases)" in message:
            num_cases = int(message.split("(")[1].split()[0])
            total_cases += num_cases

        if not valid:
            all_valid = False

    return all_valid, total_files, total_cases


def _validate_agent_evals(agents_dir: Path) -> tuple[bool, int, int]:
    """Validate all evaluation files in agents directory.

    Args:
        agents_dir: Agents directory

    Returns:
        Tuple of (all_valid, total_files, total_cases)
    """
    all_valid = True
    total_files = 0
    total_cases = 0

    for agent_dir in agents_dir.iterdir():
        if not agent_dir.is_dir():
            continue

        evals_dir = agent_dir / "evals"
        if not evals_dir.exists():
            continue

        print(f"📁 {agent_dir.name}/evals/")

        config_valid, config_files = _validate_test_config_file(evals_dir)
        total_files += config_files
        if not config_valid:
            all_valid = False

        test_valid, test_files, test_cases = _validate_test_files(evals_dir)
        total_files += test_files
        total_cases += test_cases
        if not test_valid:
            all_valid = False

        print()

    return all_valid, total_files, total_cases


def main():
    """Validate all evaluation files."""
    agents_dir = Path("application/agents")

    if not agents_dir.exists():
        print(f"❌ Directory not found: {agents_dir}")
        sys.exit(1)

    print("🔍 Validating evaluation files...\n")

    all_valid, total_files, total_cases = _validate_agent_evals(agents_dir)

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
