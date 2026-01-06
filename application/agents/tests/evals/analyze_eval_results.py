#!/usr/bin/env python3
"""Analyze ADK evaluation results and show detailed comparison."""

import json
import sys
from pathlib import Path


def print_tool_comparison(expected_tools, actual_tools):
    """Print comparison of expected vs actual tool calls."""
    print("\n" + "="*80)
    print("TOOL CALLS COMPARISON")
    print("="*80)

    max_len = max(len(expected_tools), len(actual_tools))

    for i in range(max_len):
        print(f"\n--- Tool Call #{i+1} ---")

        if i < len(expected_tools):
            exp = expected_tools[i]
            print(f"✓ EXPECTED:")
            print(f"  Tool: {exp.get('name')}")
            print(f"  Args: {json.dumps(exp.get('args', {}), indent=8)}")
        else:
            print(f"✗ EXPECTED: (none)")

        if i < len(actual_tools):
            # Find actual tool call from invocation events
            print(f"\n✓ ACTUAL:")
            print(f"  Tool: {actual_tools[i].get('name')}")
            print(f"  Args: {json.dumps(actual_tools[i].get('args', {}), indent=8)}")
        else:
            print(f"\n✗ ACTUAL: (none)")

        # Check if match
        if i < len(expected_tools) and i < len(actual_tools):
            exp_name = expected_tools[i].get('name')
            act_name = actual_tools[i].get('name')
            if exp_name == act_name:
                print(f"\n  ✅ MATCH")
            else:
                print(f"\n  ❌ MISMATCH")


def extract_actual_tools_from_events(events):
    """Extract tool calls from invocation events."""
    tools = []
    for event in events:
        if event.get('content', {}).get('role') == 'model':
            parts = event.get('content', {}).get('parts', [])
            for part in parts:
                if part.get('function_call'):
                    fc = part['function_call']
                    tools.append({
                        'name': fc.get('name'),
                        'args': fc.get('args', {})
                    })
    return tools


def print_response_comparison(expected_text, actual_text):
    """Print comparison of expected vs actual responses."""
    print("\n" + "="*80)
    print("RESPONSE COMPARISON")
    print("="*80)

    print("\n✓ EXPECTED RESPONSE:")
    print("-" * 80)
    print(expected_text or "(empty)")
    print("-" * 80)

    print("\n✓ ACTUAL RESPONSE:")
    print("-" * 80)
    print(actual_text or "(empty)")
    print("-" * 80)

    # Simple match check
    if expected_text and actual_text:
        if expected_text.strip() == actual_text.strip():
            print("\n✅ EXACT MATCH")
        elif expected_text.strip().lower() in actual_text.strip().lower():
            print("\n⚠️  PARTIAL MATCH (actual contains expected)")
        elif actual_text.strip().lower() in expected_text.strip().lower():
            print("\n⚠️  PARTIAL MATCH (expected contains actual)")
        else:
            print("\n❌ NO MATCH")
            print(f"\nExpected length: {len(expected_text)} chars")
            print(f"Actual length:   {len(actual_text)} chars")


def analyze_eval_case(case_result):
    """Analyze a single eval case."""
    eval_id = case_result.get('eval_id')
    status = case_result.get('final_eval_status')

    status_text = {1: "✅ PASSED", 2: "❌ FAILED", 3: "⚠️  SKIPPED"}.get(status, "❓ UNKNOWN")

    print("\n" + "="*80)
    print(f"EVAL CASE: {eval_id}")
    print(f"STATUS: {status_text}")
    print("="*80)

    # Get metrics
    metrics = case_result.get('overall_eval_metric_results', [])
    if metrics:
        print("\nMETRICS:")
        for metric in metrics:
            name = metric.get('metric_name')
            score = metric.get('score')
            threshold = metric.get('threshold')
            m_status = metric.get('eval_status')
            m_status_text = {1: "✅ PASS", 2: "❌ FAIL"}.get(m_status, "❓")
            print(f"  {name}: {score:.2f} (threshold: {threshold}) {m_status_text}")

    # Get invocations
    invocations = case_result.get('eval_metric_result_per_invocation', [])

    for idx, inv in enumerate(invocations):
        print(f"\n{'='*80}")
        print(f"INVOCATION #{idx+1}")
        print('='*80)

        expected = inv.get('expected_invocation', {})
        actual = inv.get('actual_invocation', {})

        # User query
        exp_query = expected.get('user_content', {}).get('parts', [{}])[0].get('text', '')
        act_query = actual.get('user_content', {}).get('parts', [{}])[0].get('text', '')

        print(f"\nUSER QUERY:")
        print(f"  {exp_query}")
        if exp_query != act_query:
            print(f"\n  ⚠️  Actual query differs: {act_query}")

        # Extract expected tools
        expected_tools = expected.get('intermediate_data', {}).get('tool_uses', [])

        # Extract actual tools from events
        actual_events = actual.get('intermediate_data', {}).get('invocation_events', [])
        actual_tools = extract_actual_tools_from_events(actual_events)

        # Print tool comparison
        if expected_tools or actual_tools:
            print_tool_comparison(expected_tools, actual_tools)

        # Extract expected response
        exp_response_parts = expected.get('final_response', {}).get('parts', [])
        exp_response_text = ""
        for part in exp_response_parts:
            if part.get('text'):
                exp_response_text += part['text']

        # Extract actual response (from first model event with text)
        act_response_text = ""
        for event in actual_events:
            if event.get('content', {}).get('role') == 'model':
                parts = event.get('content', {}).get('parts', [])
                for part in parts:
                    if part.get('text'):
                        act_response_text += part['text']
                        break
                if act_response_text:
                    break

        # Print response comparison
        if exp_response_text or act_response_text:
            print_response_comparison(exp_response_text, act_response_text)


def main():
    if len(sys.argv) < 2:
        print("Usage: analyze_eval_results.py <eval_result.json>")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    # Read and parse
    content = file_path.read_text()

    # Handle double-encoded JSON
    data = json.loads(content)
    if isinstance(data, str):
        # Double-encoded
        data = json.loads(data)

    # Get eval cases
    eval_cases = data.get('eval_case_results', [])

    print("\n" + "="*80)
    print(f"EVALUATION RESULTS: {data.get('eval_set_id')}")
    print(f"Total Cases: {len(eval_cases)}")
    print("="*80)

    for case in eval_cases:
        analyze_eval_case(case)

    print("\n" + "="*80)
    print("END OF REPORT")
    print("="*80)


if __name__ == '__main__':
    main()
