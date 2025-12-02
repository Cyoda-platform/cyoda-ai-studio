"""
Repository Management Module

Handles repository resolution and configuration including:
- Repository name resolution strategies
- Repository configuration
- Language-based repository selection
"""

from application.services.github.repository.resolver import (
    RepositoryResolver,
    DefaultRepositoryResolver,
    ParameterBasedRepositoryResolver,
    RepositoryResolverFactory,
    resolve_repository_name,
    resolve_repository_name_with_language_param,
)
from application.services.github.repository.config import RepositoryConfig

__all__ = [
    "RepositoryResolver",
    "DefaultRepositoryResolver",
    "ParameterBasedRepositoryResolver",
    "RepositoryResolverFactory",
    "resolve_repository_name",
    "resolve_repository_name_with_language_param",
    "RepositoryConfig",
]

