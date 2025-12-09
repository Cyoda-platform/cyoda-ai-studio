#!/usr/bin/env python3
"""
Test script to verify metrics backend functionality.
Tests the /api/v1/metrics/query endpoint with various query types.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.resolve()
sys.path.insert(0, str(project_root))

from application.routes.metrics import _build_namespace, _build_query


def test_namespace_building():
    """Test namespace construction logic."""
    print("Testing namespace building...")
    
    # Test cyoda app
    ns = _build_namespace("demo", "dev", "cyoda")
    assert ns == "client-demo-dev", f"Expected 'client-demo-dev', got '{ns}'"
    print(f"✓ Cyoda namespace: {ns}")
    
    # Test custom app
    ns = _build_namespace("demo", "dev", "myapp")
    assert ns == "client-app-demo-dev-myapp", f"Expected 'client-app-demo-dev-myapp', got '{ns}'"
    print(f"✓ Custom app namespace: {ns}")


def test_query_building():
    """Test query building for all query types."""
    print("\nTesting query building...")
    
    namespace = "client-demo-dev"
    query_types = [
        "pod_status_up",
        "pod_status_down",
        "cpu_usage_rate",
        "memory_usage",
        "pod_count",
        "pod_restarts",
        "pod_not_ready",
        "memory_working_set",
        "cpu_usage_by_pod",
        "cpu_usage_by_deployment",
        "cpu_usage_by_node",
        "memory_usage_by_deployment",
        "http_requests_rate",
        "http_errors_rate",
        "http_request_latency_p95",
        "events_rate",
    ]
    
    for query_type in query_types:
        try:
            query = _build_query(query_type, namespace)
            assert namespace in query, f"Namespace not in query: {query}"
            print(f"✓ {query_type}: {query[:60]}...")
        except Exception as e:
            print(f"✗ {query_type}: {e}")
            return False
    
    return True


def test_invalid_query_type():
    """Test that invalid query types raise errors."""
    print("\nTesting error handling...")
    
    try:
        _build_query("invalid_query_type", "client-demo-dev")
        print("✗ Should have raised ValueError for invalid query type")
        return False
    except ValueError as e:
        print(f"✓ Correctly raised error: {str(e)[:60]}...")
        return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Metrics Backend Tests")
    print("=" * 60)
    
    try:
        test_namespace_building()
        
        if not test_query_building():
            return 1
        
        if not test_invalid_query_type():
            return 1
        
        print("\n" + "=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

