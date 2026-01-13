#!/usr/bin/env python3
"""Generate eval test cases from scenarios.md by running them through the agent."""

import asyncio
import json
import logging
import os
import re
import sys
import time
import uuid
from pathlib import Path

# Ensure we're in the right directory
project_root = Path(__file__).parent.parent.parent.parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "services"))
sys.path.insert(0, str(project_root / "application"))
sys.path.insert(0, str(project_root / "common"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_agent():
    """Lazy load agent to avoid import errors during script init."""
    from google.adk import Runner

    from application.agents.agent import root_agent

    return root_agent


def parse_scenarios(scenarios_file: Path) -> list[dict]:
    """Parse scenarios from scenarios.md file.

    Returns list of dicts with:
    - scenario_id: sanitized identifier
    - scenario_text: original text
    - user_query: the actual user request
    """
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


async def run_scenario(scenario: dict) -> dict:
    """Run a single scenario through the agent and capture response."""
    from google.adk import Runner

    logger.info(f"Running scenario: {scenario['scenario_id']}")
    logger.info(f"Query: {scenario['user_query']}")

    agent = load_agent()
    runner = Runner(agent)

    try:
        response_parts = []
        tool_calls = []

        async for event in runner.run_async(scenario["user_query"]):
            # Capture text responses
            if hasattr(event, "text") and event.text:
                response_parts.append(event.text)

            # Capture tool calls
            if hasattr(event, "tool_name"):
                tool_calls.append(
                    {
                        "tool_name": event.tool_name,
                        "tool_input": getattr(event, "tool_input", None),
                    }
                )

        await runner.close()

        final_response = "".join(response_parts).strip()

        return {"success": True, "response": final_response, "tool_calls": tool_calls}

    except Exception as e:
        logger.error(f"Error running scenario: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


def create_eval_case(scenario: dict, result: dict) -> dict:
    """Create an eval case in ADK format."""
    invocation_id = f"e-{uuid.uuid4()}"

    eval_case = {
        "eval_id": f"case_{scenario['scenario_id'][:6]}",
        "conversation": [
            {
                "invocation_id": invocation_id,
                "user_content": {
                    "parts": [{"text": scenario["user_query"]}],
                    "role": "user",
                },
                "final_response": {
                    "parts": [{"text": result.get("response", "No response captured")}],
                    "role": "model",
                },
                "intermediate_data": {
                    "tool_calls": result.get("tool_calls", []),
                    "success": result.get("success", False),
                },
                "creation_timestamp": time.time(),
            }
        ],
        "session_input": {"app_name": "github", "user_id": "user"},
        "creation_timestamp": time.time(),
    }

    return eval_case


def create_evalset_file(scenario: dict, eval_case: dict, output_dir: Path):
    """Create an evalset JSON file for a scenario."""
    eval_set_id = f"github_scenario_{scenario['scenario_id']}"

    evalset = {
        "eval_set_id": eval_set_id,
        "name": eval_set_id,
        "description": f"Test case for: {scenario['scenario_text']}",
        "eval_cases": [eval_case],
        "creation_timestamp": time.time(),
    }

    output_file = output_dir / f"{eval_set_id}.evalset.json"

    with open(output_file, "w") as f:
        json.dump(evalset, f, indent=2)

    logger.info(f"Created eval file: {output_file}")
    return output_file


async def main():
    """Main entry point."""
    # Set environment variables
    os.environ["DISABLE_MCP_TOOLSET"] = "true"
    os.environ["MOCK_ALL_TOOLS"] = "true"  # Use mocking for consistent results

    # Paths
    base_dir = Path(__file__).parent.parent
    scenarios_file = base_dir / "dialogues" / "scenarios.md"
    output_dir = base_dir / "evals"

    logger.info(f"Reading scenarios from: {scenarios_file}")
    logger.info(f"Output directory: {output_dir}")

    # Parse scenarios
    scenarios = parse_scenarios(scenarios_file)
    logger.info(f"Found {len(scenarios)} scenarios")

    # Process each scenario
    results = []
    for i, scenario in enumerate(scenarios, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing scenario {i}/{len(scenarios)}")
        logger.info(f"{'='*60}")

        result = await run_scenario(scenario)

        if result["success"]:
            eval_case = create_eval_case(scenario, result)
            output_file = create_evalset_file(scenario, eval_case, output_dir)
            results.append(
                {
                    "scenario": scenario["scenario_id"],
                    "status": "success",
                    "file": str(output_file),
                }
            )
        else:
            logger.error(f"Failed to run scenario: {scenario['scenario_id']}")
            results.append(
                {
                    "scenario": scenario["scenario_id"],
                    "status": "failed",
                    "error": result.get("error", "Unknown error"),
                }
            )

    # Print summary
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")

    successful = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")

    logger.info(f"Total scenarios: {len(scenarios)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")

    if failed > 0:
        logger.info("\nFailed scenarios:")
        for r in results:
            if r["status"] == "failed":
                logger.info(f"  - {r['scenario']}: {r.get('error', 'Unknown')}")

    logger.info("\nGenerated eval files:")
    for r in results:
        if r["status"] == "success":
            logger.info(f"  - {r['file']}")


if __name__ == "__main__":
    asyncio.run(main())
