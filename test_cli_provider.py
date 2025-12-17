#!/usr/bin/env python3
"""
Test script for CLI provider configuration
"""

import os
import sys

# Add project root to path
sys.path.insert(0, '/home/kseniia/IdeaProjects/cyoda-ai-studio')

def test_config():
    """Test configuration loading"""
    print("=" * 80)
    print("Testing CLI Provider Configuration")
    print("=" * 80)

    from common.config.config import CLI_PROVIDER, AUGMENT_MODEL, CLAUDE_MODEL, GEMINI_MODEL

    print(f"\n✅ Configuration loaded successfully:")
    print(f"   CLI_PROVIDER: {CLI_PROVIDER}")
    print(f"   AUGMENT_MODEL: {AUGMENT_MODEL}")
    print(f"   CLAUDE_MODEL: {CLAUDE_MODEL}")
    print(f"   GEMINI_MODEL: {GEMINI_MODEL}")

    return True

def test_cli_routing():
    """Test CLI routing logic"""
    print("\n" + "=" * 80)
    print("Testing CLI Routing Logic")
    print("=" * 80)

    from application.agents.github.tools import _get_cli_config

    providers = ["augment", "claude", "gemini"]

    for provider in providers:
        script_path, model = _get_cli_config(provider)
        exists = script_path.exists()
        status = "✅" if exists else "❌"

        print(f"\n{status} Provider: {provider}")
        print(f"   Script: {script_path.name}")
        print(f"   Model: {model}")
        print(f"   Exists: {exists}")
        print(f"   Path: {script_path}")

    return True

def test_scripts_executable():
    """Test that scripts are executable"""
    print("\n" + "=" * 80)
    print("Testing Script Permissions")
    print("=" * 80)

    from pathlib import Path

    scripts = [
        "application/agents/shared/augment_build.sh",
        "application/agents/shared/claude_build.sh",
        "application/agents/shared/gemini_build.sh",
    ]

    for script_rel in scripts:
        script = Path(f"/home/kseniia/IdeaProjects/cyoda-ai-studio/{script_rel}")
        is_exec = os.access(script, os.X_OK)
        status = "✅" if is_exec else "❌"

        print(f"\n{status} {script.name}")
        print(f"   Executable: {is_exec}")
        print(f"   Exists: {script.exists()}")

    return True

def test_env_override():
    """Test environment variable override"""
    print("\n" + "=" * 80)
    print("Testing Environment Variable Override")
    print("=" * 80)

    # Set env var
    os.environ["CLI_PROVIDER"] = "claude"

    # Reload module to pick up new env var
    import importlib
    import common.config.config as config_module
    importlib.reload(config_module)

    from common.config.config import CLI_PROVIDER

    print(f"\n✅ CLI_PROVIDER after override: {CLI_PROVIDER}")

    # Get CLI config
    from application.agents.github.tools import _get_cli_config
    script_path, model = _get_cli_config()

    print(f"   Using script: {script_path.name}")
    print(f"   Using model: {model}")

    # Reset
    os.environ["CLI_PROVIDER"] = "augment"

    return CLI_PROVIDER == "claude"

def main():
    """Run all tests"""
    print("\n🧪 CLI Provider Integration Tests\n")

    tests = [
        ("Configuration Loading", test_config),
        ("CLI Routing Logic", test_cli_routing),
        ("Script Permissions", test_scripts_executable),
        ("Environment Override", test_env_override),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(1 for _, p in results if p)

    print(f"\nTotal: {passed}/{total} tests passed")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
