#!/usr/bin/env python3
"""Batch update all evalset.json files with their latest evaluation results."""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Import the update function
from update_expected_values import update_evalset_from_results


def find_evalset_file(evalset_id, base_path):
    """Find the evalset.json file for a given evalset_id."""

    # Common locations to search
    search_paths = [
        base_path / "application/agents/github/evals",
        base_path / "application/agents/environment/evals",
        base_path / "application/agents/coordinator/evals",
        base_path / "application/agents/qa/evals",
        base_path / "tests/integration/agents",
    ]

    for search_path in search_paths:
        if not search_path.exists():
            continue

        # Look for files matching the evalset_id
        for file in search_path.glob("*.evalset.json"):
            with open(file, "r") as f:
                try:
                    data = json.load(f)
                    if data.get("eval_set_id") == evalset_id:
                        return file
                except:
                    continue

    return None


def main():
    base_path = Path(__file__).parent.parent.parent.parent.parent
    eval_history_path = base_path / "application/agents/.adk/eval_history"

    if not eval_history_path.exists():
        print(f"❌ Eval history directory not found: {eval_history_path}")
        sys.exit(1)

    # Find all result files and group by evalset_id
    result_files_by_evalset = defaultdict(list)

    for result_file in eval_history_path.glob("*.evalset_result.json"):
        # Extract evalset_id from filename: agents_<evalset_id>_<timestamp>.evalset_result.json
        filename = result_file.stem  # Remove .json
        # Remove the timestamp part (everything after the last underscore that looks like a number)
        parts = filename.split("_")

        # Find where the timestamp starts (it's a long number with dots)
        evalset_parts = []
        for i, part in enumerate(parts):
            if i > 0 and ("." in part or part.isdigit()) and len(part) > 10:
                # This is likely the start of timestamp
                break
            evalset_parts.append(part)

        # Remove 'agents' prefix
        if evalset_parts[0] == "agents":
            evalset_parts = evalset_parts[1:]

        evalset_id = "_".join(evalset_parts)

        # Get file modification time
        mtime = result_file.stat().st_mtime
        result_files_by_evalset[evalset_id].append((mtime, result_file))

    print(f"📊 Found {len(result_files_by_evalset)} unique evalsets\n")

    # Process each evalset
    total_updated = 0
    total_evalsets = 0

    for evalset_id, files in sorted(result_files_by_evalset.items()):
        # Get the most recent result file
        files.sort(reverse=True)  # Sort by mtime descending
        latest_result_file = files[0][1]

        # Find the corresponding evalset.json file
        evalset_file = find_evalset_file(evalset_id, base_path)

        if not evalset_file:
            print(f"⚠️  {evalset_id}: evalset.json not found, skipping")
            continue

        print(f"🔄 Processing: {evalset_id}")
        print(f"   Result file: {latest_result_file.name}")
        print(f"   Evalset file: {evalset_file.relative_to(base_path)}")

        try:
            updated_count = update_evalset_from_results(
                latest_result_file, evalset_file
            )
            total_updated += updated_count
            total_evalsets += 1
            print()
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            continue

    print("=" * 80)
    print(f"✅ Batch update complete!")
    print(f"   Updated {total_evalsets} evalset files")
    print(f"   Updated {total_updated} total invocations")
    print("=" * 80)


if __name__ == "__main__":
    main()
