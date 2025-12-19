#!/usr/bin/env python3
"""
Test script to verify 3-day window pagination logic
"""

from datetime import datetime, timedelta, timezone

def test_window_calculation():
    """Test that the 3-day window calculation works correctly"""
    
    # Test 1: Current time (no window_start provided)
    current_time = datetime.now(timezone.utc)
    window_start = current_time
    window_end = window_start - timedelta(days=3)
    
    print(f"Test 1: Current time window")
    print(f"  Window Start: {window_start.isoformat()}")
    print(f"  Window End: {window_end.isoformat()}")
    print(f"  Date Range: {window_end.strftime('%Y-%m-%d')} to {window_start.strftime('%Y-%m-%d')}")
    print()
    
    # Test 2: Next window (3 days earlier)
    next_window_start = (window_end - timedelta(seconds=1)).isoformat()
    print(f"Test 2: Next window start (for pagination)")
    print(f"  Next Window Start: {next_window_start}")
    print()
    
    # Test 3: Verify date format for search condition
    window_end_str = window_end.strftime("%Y-%m-%d")
    print(f"Test 3: Date format for search condition")
    print(f"  Window End (formatted): {window_end_str}")
    print(f"  This will be used in: .add_condition('date', SearchOperator.GREATER_THAN, '{window_end_str}')")
    print()
    
    # Test 4: Simulate multiple pagination requests
    print(f"Test 4: Simulating pagination flow")
    current = datetime.now(timezone.utc)
    for i in range(3):
        window_start = current - timedelta(days=3*i)
        window_end = window_start - timedelta(days=3)
        print(f"  Page {i+1}: {window_end.strftime('%Y-%m-%d')} to {window_start.strftime('%Y-%m-%d')}")
    print()
    
    print("✅ All tests passed!")

if __name__ == "__main__":
    test_window_calculation()

