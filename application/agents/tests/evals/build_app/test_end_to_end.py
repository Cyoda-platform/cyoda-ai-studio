#!/usr/bin/env python3
"""
End-to-end integration test for building institutional trading platform.
Tests the full flow: user request → coordinator → github_agent → option selection.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add application to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from application.agents.agent import create_root_agent


async def test_institutional_trading_platform_flow():
    """
    Test end-to-end flow for building institutional trading platform.

    Expected flow:
    1. User sends complex build request
    2. Coordinator routes to github_agent
    3. Github_agent checks branch configuration
    4. Github_agent presents setup options
    5. Response includes option selection UI
    """
    print("🧪 Starting end-to-end test: Institutional Trading Platform\n")

    # Setup environment for testing
    os.environ['DISABLE_MCP_TOOLSET'] = 'true'
    os.environ['MOCK_ALL_TOOLS'] = 'true'

    # Create root agent
    print("📦 Creating root agent...")
    root_agent = await create_root_agent()

    # Test query
    user_query = (
        "Develop an institutional trading platform with real-time market data feeds, "
        "advanced order management systems, comprehensive portfolio tracking, risk controls, "
        "regulatory compliance for equities and derivatives, and real-time P&L calculations"
    )

    print(f"📤 Sending request: {user_query[:100]}...\n")

    # Track events
    events = []
    tools_called = []
    agents_used = set()
    transfers = []

    # Send request and collect events
    async for event in root_agent.run(user_query):
        events.append(event)

        # Track event types
        if hasattr(event, 'type'):
            event_type = event.type

            # Track agent usage
            if hasattr(event, 'agent_name'):
                agents_used.add(event.agent_name)

            # Track tool calls
            if event_type == 'tool_call':
                tool_name = event.data.get('name') if hasattr(event, 'data') else 'unknown'
                tools_called.append(tool_name)
                print(f"  🔧 Tool called: {tool_name}")

                # Track transfers
                if tool_name == 'transfer_to_agent':
                    target = event.data.get('args', {}).get('agent_name')
                    transfers.append(target)
                    print(f"  ↪️  Transferred to: {target}")

            # Track content
            elif event_type == 'content':
                content = event.data.get('text', '') if hasattr(event, 'data') else ''
                if content:
                    preview = content[:100] + '...' if len(content) > 100 else content
                    print(f"  💬 Content: {preview}")

    print("\n" + "="*80)
    print("📊 Test Results")
    print("="*80 + "\n")

    # Validate results
    passed = True

    # Check 1: Coordinator transferred to github_agent
    print("✓ Test 1: Coordinator transfers to github_agent")
    if 'github_agent' not in transfers:
        print(f"  ❌ FAILED: Expected transfer to github_agent, got: {transfers}")
        passed = False
    else:
        print(f"  ✅ PASSED: Transferred to github_agent")

    # Check 2: Branch configuration was checked
    print("\n✓ Test 2: Github agent checks branch configuration")
    if 'check_existing_branch_configuration' not in tools_called:
        print(f"  ❌ FAILED: Expected check_existing_branch_configuration call")
        passed = False
    else:
        print(f"  ✅ PASSED: Branch configuration checked")

    # Check 3: User was asked to select option
    print("\n✓ Test 3: Github agent asks user to select option")
    if 'ask_user_to_select_option' not in tools_called:
        print(f"  ❌ FAILED: Expected ask_user_to_select_option call")
        passed = False
    else:
        print(f"  ✅ PASSED: User prompted for option selection")

    # Check 4: Both agents were used
    print("\n✓ Test 4: Multiple agents involved")
    print(f"  Agents used: {sorted(agents_used)}")
    if len(agents_used) < 2:
        print(f"  ❌ FAILED: Expected at least 2 agents")
        passed = False
    else:
        print(f"  ✅ PASSED: Multiple agents participated")

    # Summary
    print("\n" + "="*80)
    if passed:
        print("🎉 ALL TESTS PASSED")
        print("="*80)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("="*80)
        return 1


async def main():
    """Main test runner."""
    exit_code = await test_institutional_trading_platform_flow()
    sys.exit(exit_code)


if __name__ == '__main__':
    asyncio.run(main())
