"""Middleware package for common authentication and authorization."""

from common.middleware.auth_middleware import require_auth

__all__ = ["require_auth"]
