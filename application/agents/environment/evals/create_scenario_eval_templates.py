#!/usr/bin/env python3
"""Create eval template files from environment scenarios.md."""

import json
import re
import time
import uuid
from pathlib import Path


def parse_scenarios(scenarios_file: Path) -> list[dict]:
    """Parse scenarios from scenarios.md file."""
    scenarios = []

    with open(scenarios_file, "r") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Remove leading "- " if present
        if line.startswith("- "):
            line = line[2:]

        # Extract scenario (remove "As a user, I want to " prefix if present)
        if line.startswith("As a user, I want to "):
            user_query = line[len("As a user, I want to ") :]
        elif line.startswith("As a user I want to "):
            user_query = line[len("As a user I want to ") :]
        else:
            user_query = line

        # Create scenario ID from text
        scenario_id = re.sub(r"[^a-z0-9]+", "_", user_query.lower())[:50].strip("_")

        scenarios.append(
            {
                "scenario_id": scenario_id,
                "scenario_text": line,
                "user_query": user_query,
            }
        )

    return scenarios


def create_eval_template(scenario: dict, output_dir: Path) -> Path:
    """Create an eval template file for a scenario."""
    eval_set_id = f"environment_scenario_{scenario['scenario_id']}"
    invocation_id = f"e-{uuid.uuid4()}"

    # Create minimal eval case - the response will be filled in when run with ADK
    evalset = {
        "eval_set_id": eval_set_id,
        "name": eval_set_id,
        "description": f"Test case for: {scenario['scenario_text']}",
        "eval_cases": [
            {
                "eval_id": f"case_{scenario['scenario_id'][:8]}",
                "conversation": [
                    {
                        "invocation_id": invocation_id,
                        "user_content": {
                            "parts": [{"text": scenario["user_query"]}],
                            "role": "user",
                        },
                        "final_response": {
                            "parts": [{"text": "<<RESPONSE_TO_BE_GENERATED>>"}],
                            "role": "model",
                        },
                        "intermediate_data": {},
                        "creation_timestamp": time.time(),
                    }
                ],
                "session_input": {"app_name": "environment", "user_id": "user"},
                "creation_timestamp": time.time(),
            }
        ],
        "creation_timestamp": time.time(),
    }

    output_file = output_dir / f"{eval_set_id}.evalset.json"

    with open(output_file, "w") as f:
        json.dump(evalset, f, indent=2)

    return output_file


def main():
    """Main entry point."""
    # Paths
    base_dir = Path(__file__).parent.parent
    scenarios_file = base_dir / "dialogues" / "scenarios.md"
    output_dir = base_dir / "evals" / "scenarios"

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading scenarios from: {scenarios_file}")
    print(f"Output directory: {output_dir}")

    # Parse scenarios
    scenarios = parse_scenarios(scenarios_file)
    print(f"Found {len(scenarios)} scenarios\n")

    # Create template files
    created_files = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['scenario_text']}")
        output_file = create_eval_template(scenario, output_dir)
        created_files.append(output_file)
        print(f"   Created: {output_file.name}")

    print(f"\n{'='*60}")
    print(f"Created {len(created_files)} eval template files")
    print(f"{'='*60}\n")

    print("Next steps:")
    print("1. Run the eval to generate responses:")
    print(f"\n   export DISABLE_MCP_TOOLSET=true MOCK_ALL_TOOLS=true && \\")
    print(f"   adk eval application/agents \\")
    print(f"     application/agents/environment/evals/scenarios/*.evalset.json \\")
    print(f"     --config_file_path application/agents/tests/evals/test_config.json\n")


if __name__ == "__main__":
    main()
