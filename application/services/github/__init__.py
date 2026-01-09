"""
GitHub Service Package

Unified service layer for all GitHub and Git operations.
Consolidates scattered GitHub interactions into a cohesive architecture.

Main Components:
- GitHubService: Main facade for all GitHub/Git operations
- API Client: GitHub REST API interactions
- Git Operations: Local git command operations
- Repository Management: Repository resolution and configuration
"""

from application.services.github.github_service import GitHubService

__all__ = ["GitHubService"]
