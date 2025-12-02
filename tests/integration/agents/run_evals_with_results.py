"""
Test runner for ADK evals with formatted results saved to file.

This script runs the ADK evaluation tests and saves the formatted results
to a JSON file with timestamps and detailed metrics.

Usage:
    python -m pytest tests/integration/agents/run_evals_with_results.py -v -s
    
Or run directly:
    python tests/integration/agents/run_evals_with_results.py
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytest
from google.adk.evaluation import AgentEvaluator


class EvalResultsCollector:
    """Collects and formats evaluation results."""

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("application/agents/eval_results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "test_cases": [],
            "summary": {},
        }

    def add_result(self, test_name: str, status: str, details: Dict[str, Any]):
        """Add a test result."""
        self.results["test_cases"].append({
            "name": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        })

    def save_results(self, filename: str = None) -> Path:
        """Save results to JSON file."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"eval_results_{timestamp}.json"

        output_file = self.output_dir / filename
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)

        return output_file

    def print_summary(self):
        """Print formatted summary."""
        print("\n" + "=" * 80)
        print("EVALUATION RESULTS SUMMARY")
        print("=" * 80)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Total Test Cases: {len(self.results['test_cases'])}")

        passed = sum(1 for tc in self.results["test_cases"] if tc["status"] == "PASSED")
        failed = sum(1 for tc in self.results["test_cases"] if tc["status"] == "FAILED")

        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print("=" * 80 + "\n")

        for tc in self.results["test_cases"]:
            status_symbol = "✅" if tc["status"] == "PASSED" else "❌"
            print(f"{status_symbol} {tc['name']}: {tc['status']}")
            if tc["details"]:
                for key, value in tc["details"].items():
                    if key == "error" and isinstance(value, str) and len(value) > 200:
                        # Print first 200 chars of error
                        print(f"   {key}: {value[:200]}...")
                    else:
                        print(f"   {key}: {value}")


class TestAddWorkflowADKEvalsWithResults:
    """ADK evaluation tests with results saved to file."""

    @pytest.mark.asyncio
    async def test_add_workflow_dialogue_evaluation_with_results(self):
        """Run add_workflow dialogue evaluation and save results."""
        collector = EvalResultsCollector()

        try:
            await AgentEvaluator.evaluate(
                agent_module="application.agents.github",
                eval_dataset_file_path_or_dir="tests/integration/agents/evals/add_workflow_dialogue.test.json",
                num_runs=1,
            )
            collector.add_result(
                "add_workflow_dialogue_evaluation",
                "PASSED",
                {"message": "All evaluation criteria met"},
            )
        except AssertionError as e:
            collector.add_result(
                "add_workflow_dialogue_evaluation",
                "FAILED",
                {"error": str(e)},
            )
            raise

        finally:
            output_file = collector.save_results()
            collector.print_summary()
            print(f"\n📁 Results saved to: {output_file}")


async def run_evals_standalone():
    """Run evals standalone and save results."""
    collector = EvalResultsCollector()

    print("🚀 Starting ADK Evaluation Tests...")
    print(f"📁 Results will be saved to: {collector.output_dir}\n")

    try:
        print("Running: add_workflow_dialogue_evaluation...")
        await AgentEvaluator.evaluate(
            agent_module="application.agents.github",
            eval_dataset_file_path_or_dir="tests/integration/agents/evals/add_workflow_dialogue.test.json",
            num_runs=1,
        )
        collector.add_result(
            "add_workflow_dialogue_evaluation",
            "PASSED",
            {"message": "All evaluation criteria met"},
        )
        print("✅ add_workflow_dialogue_evaluation PASSED\n")

    except AssertionError as e:
        collector.add_result(
            "add_workflow_dialogue_evaluation",
            "FAILED",
            {"error": str(e)},
        )
        print(f"❌ add_workflow_dialogue_evaluation FAILED\n{e}\n")

    finally:
        output_file = collector.save_results()
        collector.print_summary()
        print(f"📁 Results saved to: {output_file}\n")


if __name__ == "__main__":
    # Always run via pytest to ensure proper module imports
    pytest.main([__file__, "-v", "-s"])

