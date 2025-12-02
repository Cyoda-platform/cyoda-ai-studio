"""Pytest configuration for tests.

Sets up Python path and fixtures for all tests.
"""

import sys
from pathlib import Path

# Add project root to Python path so imports work correctly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

