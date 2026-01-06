#!/usr/bin/env python3
"""Generate HTML report from ADK evaluation results."""

import json
import sys
from pathlib import Path
from datetime import datetime


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ADK Evaluation Report - {eval_set_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .meta {{ opacity: 0.9; font-size: 0.95em; }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            border-left: 4px solid #667eea;
        }}
        .stat-card.passed {{ border-left-color: #10b981; }}
        .stat-card.failed {{ border-left-color: #ef4444; }}
        .stat-card h3 {{ color: #6b7280; font-size: 0.875em; text-transform: uppercase; margin-bottom: 10px; }}
        .stat-card .value {{ font-size: 2.5em; font-weight: bold; color: #1f2937; }}
        .stat-card .percentage {{ font-size: 1.2em; color: #6b7280; margin-left: 10px; }}
        .test-case {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .test-case.passed {{ border-left: 6px solid #10b981; }}
        .test-case.failed {{ border-left: 6px solid #ef4444; }}
        .test-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f3f4f6;
        }}
        .test-id {{ font-size: 1.3em; font-weight: 600; color: #1f2937; }}
        .status-badge {{
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.875em;
            text-transform: uppercase;
        }}
        .status-badge.passed {{ background: #d1fae5; color: #065f46; }}
        .status-badge.failed {{ background: #fee2e2; color: #991b1b; }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .metric {{
            padding: 15px;
            background: #f9fafb;
            border-radius: 8px;
            border-left: 3px solid #667eea;
        }}
        .metric.passed {{ border-left-color: #10b981; background: #f0fdf4; }}
        .metric.failed {{ border-left-color: #ef4444; background: #fef2f2; }}
        .metric-name {{ font-weight: 600; color: #374151; margin-bottom: 5px; }}
        .metric-score {{ font-size: 1.5em; font-weight: bold; }}
        .metric-threshold {{ color: #6b7280; font-size: 0.9em; }}
        .invocation {{
            background: #fafbfc;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid #e5e7eb;
        }}
        .section-title {{
            font-size: 1.1em;
            font-weight: 600;
            color: #1f2937;
            margin: 20px 0 10px 0;
            padding-bottom: 8px;
            border-bottom: 2px solid #e5e7eb;
        }}
        .query {{
            background: #eff6ff;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #3b82f6;
            margin-bottom: 15px;
            font-family: 'Courier New', monospace;
        }}
        .tools-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .tool-column {{
            padding: 15px;
            border-radius: 8px;
        }}
        .tool-column.expected {{ background: #fef3c7; border: 2px solid #f59e0b; }}
        .tool-column.actual {{ background: #dbeafe; border: 2px solid #3b82f6; }}
        .tool-column h4 {{ margin-bottom: 10px; color: #1f2937; }}
        .tool-call {{
            background: white;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .tool-name {{ font-weight: 600; color: #7c3aed; }}
        .tool-args {{ color: #6b7280; margin-left: 10px; }}
        .match-indicator {{
            text-align: center;
            font-size: 2em;
            padding: 20px;
        }}
        .match-indicator.match {{ color: #10b981; }}
        .match-indicator.mismatch {{ color: #ef4444; }}
        .response-comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }}
        .response-column {{
            padding: 15px;
            border-radius: 8px;
        }}
        .response-column.expected {{ background: #fef3c7; border: 2px solid #f59e0b; }}
        .response-column.actual {{ background: #dbeafe; border: 2px solid #3b82f6; }}
        .response-column h4 {{ margin-bottom: 10px; color: #1f2937; }}
        .response-text {{
            background: white;
            padding: 12px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .no-response {{ color: #9ca3af; font-style: italic; }}
        .conversation-flow {{
            margin: 20px 0;
        }}
        .event {{
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #e5e7eb;
        }}
        .event.model {{ background: #eff6ff; border-left-color: #3b82f6; }}
        .event.user {{ background: #f0fdf4; border-left-color: #10b981; }}
        .event-header {{
            font-weight: 600;
            color: #374151;
            margin-bottom: 8px;
            font-size: 0.9em;
        }}
        .event-content {{
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            margin: 5px 0;
        }}
        .function-call {{
            background: #fef3c7;
            padding: 8px;
            border-radius: 4px;
            margin: 5px 0;
            border-left: 3px solid #f59e0b;
        }}
        .function-response {{
            background: #dbeafe;
            padding: 8px;
            border-radius: 4px;
            margin: 5px 0;
            border-left: 3px solid #3b82f6;
        }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: #6b7280;
            font-size: 0.9em;
            margin-top: 40px;
        }}
        @media print {{
            body {{ background: white; }}
            .test-case {{ page-break-inside: avoid; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 ADK Evaluation Report</h1>
            <div class="meta">
                <div>Evaluation Set: <strong>{eval_set_id}</strong></div>
                <div>Generated: <strong>{timestamp}</strong></div>
                <div>Total Test Cases: <strong>{total_cases}</strong></div>
            </div>
        </div>

        <div class="summary">
            <div class="stat-card passed">
                <h3>Tests Passed</h3>
                <div>
                    <span class="value">{passed_count}</span>
                    <span class="percentage">{pass_rate:.0f}%</span>
                </div>
            </div>
            <div class="stat-card failed">
                <h3>Tests Failed</h3>
                <div>
                    <span class="value">{failed_count}</span>
                    <span class="percentage">{fail_rate:.0f}%</span>
                </div>
            </div>
            <div class="stat-card">
                <h3>Success Rate</h3>
                <div>
                    <span class="value">{pass_rate:.1f}%</span>
                </div>
            </div>
        </div>

        {test_cases_html}

        <div class="footer">
            Generated by ADK Evaluation Report Generator • Cyoda AI Assistant
        </div>
    </div>
</body>
</html>
"""

TEST_CASE_TEMPLATE = """
<div class="test-case {status_class}">
    <div class="test-header">
        <div class="test-id">{test_id}</div>
        <span class="status-badge {status_class}">{status_text}</span>
    </div>

    <div class="metrics">
        {metrics_html}
    </div>

    {invocations_html}
</div>
"""

def extract_tool_calls(events):
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


def extract_response_text(events):
    """Extract response text from invocation events."""
    texts = []
    for event in events:
        if event.get('content', {}).get('role') == 'model':
            parts = event.get('content', {}).get('parts', [])
            for part in parts:
                if part.get('text'):
                    texts.append(part['text'])
    return ' '.join(texts) if texts else None


def generate_html_report(result_files, output_path):
    """Generate HTML report from evaluation result files."""
    all_cases = []
    eval_set_id = "Unknown"

    for file_path in result_files:
        data = json.loads(Path(file_path).read_text())
        if isinstance(data, str):
            data = json.loads(data)

        eval_set_id = data.get('eval_set_id', eval_set_id)
        all_cases.extend(data.get('eval_case_results', []))

    # Calculate summary stats
    total_cases = len(all_cases)
    passed_count = sum(1 for c in all_cases if c.get('final_eval_status') == 1)
    failed_count = total_cases - passed_count
    pass_rate = (passed_count / total_cases * 100) if total_cases > 0 else 0
    fail_rate = 100 - pass_rate

    # Generate test case HTML
    test_cases_html = []
    for case in all_cases:
        case_id = case.get('eval_id', 'Unknown')
        status = case.get('final_eval_status')
        status_class = 'passed' if status == 1 else 'failed'
        status_text = 'Passed' if status == 1 else 'Failed'

        # Generate metrics HTML
        metrics = case.get('overall_eval_metric_results', [])
        metrics_html = []
        for metric in metrics:
            name = metric.get('metric_name', 'Unknown')
            score = metric.get('score', 0)
            threshold = metric.get('threshold', 0)
            m_status = metric.get('eval_status')
            m_class = 'passed' if m_status == 1 else 'failed'

            metrics_html.append(f"""
                <div class="metric {m_class}">
                    <div class="metric-name">{name}</div>
                    <div>
                        <span class="metric-score">{score:.2f}</span>
                        <span class="metric-threshold">/ {threshold}</span>
                    </div>
                </div>
            """)

        # Generate invocations HTML
        invocations = case.get('eval_metric_result_per_invocation', [])
        invocations_html = []

        for idx, inv in enumerate(invocations):
            expected_inv = inv.get('expected_invocation', {})
            actual_inv = inv.get('actual_invocation', {})

            # Get user query
            exp_query = expected_inv.get('user_content', {}).get('parts', [{}])[0].get('text', 'N/A')

            # Get expected tools
            expected_tools = expected_inv.get('intermediate_data', {}).get('tool_uses', [])

            # Get actual tools
            actual_events = actual_inv.get('intermediate_data', {}).get('invocation_events', [])
            actual_tools = extract_tool_calls(actual_events)

            # Get expected response text
            expected_response = expected_inv.get('final_response', {}).get('parts', [{}])[0].get('text', None)

            # Get actual response text from final_response field (what ADK evaluator sees)
            actual_final_response = actual_inv.get('final_response')
            if actual_final_response and actual_final_response.get('parts'):
                actual_response = actual_final_response.get('parts', [{}])[0].get('text', None)
            else:
                actual_response = None

            # Also extract from events for informational purposes
            actual_response_from_events = extract_response_text(actual_events)

            # Build conversation flow HTML from events
            conversation_flow_html = ""
            for event_idx, event in enumerate(actual_events):
                author = event.get('author', 'unknown')
                content = event.get('content', {})
                role = content.get('role', 'unknown')
                parts = content.get('parts', [])

                event_class = role if role in ['model', 'user'] else 'unknown'
                event_parts_html = []

                for part in parts:
                    if part.get('text'):
                        event_parts_html.append(f'<div class="event-content">{part["text"]}</div>')

                    if part.get('function_call'):
                        fc = part['function_call']
                        args_str = json.dumps(fc.get('args', {}))
                        event_parts_html.append(f'''
                            <div class="function-call">
                                <strong>🔧 Function Call:</strong> {fc.get('name')}({args_str})
                            </div>
                        ''')

                    if part.get('function_response'):
                        fr = part['function_response']
                        response_str = json.dumps(fr.get('response', {}), indent=2)
                        event_parts_html.append(f'''
                            <div class="function-response">
                                <strong>✅ Function Response:</strong> {fr.get('name')}<br>
                                <pre style="margin: 5px 0; font-size: 0.85em;">{response_str}</pre>
                            </div>
                        ''')

                if event_parts_html:
                    conversation_flow_html += f'''
                        <div class="event {event_class}">
                            <div class="event-header">Event #{event_idx + 1} - {author} ({role})</div>
                            {''.join(event_parts_html)}
                        </div>
                    '''

            # Build tools comparison
            expected_tools_html = ""
            for tool in expected_tools:
                args_str = json.dumps(tool.get('args', {}))
                expected_tools_html += f"""
                    <div class="tool-call">
                        <span class="tool-name">{tool.get('name')}</span>
                        <span class="tool-args">{args_str}</span>
                    </div>
                """

            actual_tools_html = ""
            for tool in actual_tools:
                args_str = json.dumps(tool.get('args', {}))
                actual_tools_html += f"""
                    <div class="tool-call">
                        <span class="tool-name">{tool.get('name')}</span>
                        <span class="tool-args">{args_str}</span>
                    </div>
                """

            # Check if tools match
            match = len(expected_tools) == len(actual_tools)
            if match:
                for exp, act in zip(expected_tools, actual_tools):
                    if exp.get('name') != act.get('name'):
                        match = False
                        break

            match_indicator = "✅ MATCH" if match else "❌ MISMATCH"
            match_class = "match" if match else "mismatch"

            # Build response comparison HTML
            expected_response_html = f'<div class="response-text">{expected_response}</div>' if expected_response else '<div class="response-text no-response">No response</div>'

            if actual_response:
                actual_response_html = f'<div class="response-text">{actual_response}</div>'
            else:
                # Show null but also show what was in events if different
                if actual_response_from_events:
                    actual_response_html = f'''<div class="response-text no-response">null (ADK sees no final_response)</div>
                    <div style="margin-top: 8px; padding: 10px; background: #fff3cd; border-left: 3px solid #ffc107; border-radius: 4px; font-size: 0.85em;">
                        <strong>Note:</strong> Coordinator said: "{actual_response_from_events}" but transfer ended turn before final_response was set.
                    </div>'''
                else:
                    actual_response_html = '<div class="response-text no-response">null</div>'

            invocations_html.append(f"""
                <div class="invocation">
                    <div class="section-title">Invocation #{idx + 1}</div>
                    <div class="query"><strong>Query:</strong> {exp_query}</div>

                    <div class="section-title">Conversation Flow (Actual Events)</div>
                    <div class="conversation-flow">
                        {conversation_flow_html or '<div style="color: #9ca3af; font-style: italic;">No events recorded</div>'}
                    </div>

                    <div class="section-title">Response Comparison</div>
                    <div class="response-comparison">
                        <div class="response-column expected">
                            <h4>Expected Response</h4>
                            {expected_response_html}
                        </div>
                        <div class="response-column actual">
                            <h4>Actual Response (from final_response field)</h4>
                            {actual_response_html}
                        </div>
                    </div>

                    <div class="section-title">Tool Calls Comparison</div>
                    <div class="tools-comparison">
                        <div class="tool-column expected">
                            <h4>Expected Tools</h4>
                            {expected_tools_html or '<div class="tool-call">None</div>'}
                        </div>
                        <div class="tool-column actual">
                            <h4>Actual Tools</h4>
                            {actual_tools_html or '<div class="tool-call">None</div>'}
                        </div>
                    </div>
                    <div class="match-indicator {match_class}">{match_indicator}</div>
                </div>
            """)

        test_cases_html.append(TEST_CASE_TEMPLATE.format(
            test_id=case_id,
            status_class=status_class,
            status_text=status_text,
            metrics_html=''.join(metrics_html),
            invocations_html=''.join(invocations_html)
        ))

    # Generate final HTML
    html = HTML_TEMPLATE.format(
        eval_set_id=eval_set_id,
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        total_cases=total_cases,
        passed_count=passed_count,
        failed_count=failed_count,
        pass_rate=pass_rate,
        fail_rate=fail_rate,
        test_cases_html=''.join(test_cases_html)
    )

    # Write to file
    output_file = Path(output_path)
    output_file.write_text(html, encoding='utf-8')

    print(f"✅ HTML report generated: {output_file.absolute()}")
    print(f"📊 Summary: {passed_count}/{total_cases} tests passed ({pass_rate:.0f}%)")
    print(f"🌐 Open in browser: file://{output_file.absolute()}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: generate_html_report.py <eval_result_files...> [-o output.html]")
        print("\nExample:")
        print("  python generate_html_report.py application/agents/.adk/eval_history/agents_*.json")
        print("  python generate_html_report.py results/*.json -o report.html")
        sys.exit(1)

    # Parse arguments
    result_files = []
    output_path = "eval_report.html"

    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == '-o' and i + 1 < len(sys.argv):
            output_path = sys.argv[i + 1]
            i += 2
        else:
            # Expand glob patterns
            from glob import glob
            result_files.extend(glob(sys.argv[i]))
            i += 1

    if not result_files:
        print("❌ No result files found")
        sys.exit(1)

    generate_html_report(result_files, output_path)
