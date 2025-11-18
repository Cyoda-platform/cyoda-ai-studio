"""
GitHub API Module

Handles all GitHub REST API interactions including:
- Workflow operations
- Repository management
- Collaborator management
"""

from application.services.github.api.client import GitHubAPIClient
from application.services.github.api.workflows import WorkflowOperations
from application.services.github.api.repositories import RepositoryOperations
from application.services.github.api.collaborators import CollaboratorOperations

__all__ = [
    "GitHubAPIClient",
    "WorkflowOperations",
    "RepositoryOperations",
    "CollaboratorOperations",
]

