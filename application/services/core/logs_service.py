"""
Logs Service for Elasticsearch log management.

Encapsulates log-related business logic for API key generation and log search.
"""

# Re-export all public APIs from the logs_service package
from .logs_service import LogsService

__all__ = ["LogsService"]
