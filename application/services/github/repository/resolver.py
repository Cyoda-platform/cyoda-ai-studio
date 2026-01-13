"""
Repository resolver using Strategy pattern to determine repository names
based on programming language.

Note: This is a simplified version for the new application.
Entity-based resolution has been removed as it depends on deprecated WorkflowEntity.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional

from common.config.config import (
    JAVA_REPOSITORY_NAME,
    PYTHON_REPOSITORY_NAME,
)


class RepositoryResolver(ABC):
    """Abstract base class for repository resolution strategies."""

    @abstractmethod
    def resolve_repository_name(
        self, programming_language: Optional[str] = None
    ) -> str:
        """
        Resolve repository name based on programming language.

        Args:
            programming_language: Optional programming language override

        Returns:
            Repository name
        """
        pass


class DefaultRepositoryResolver(RepositoryResolver):
    """
    Default repository resolver based on programming language.
    Defaults to Python if no language is specified.
    """

    def resolve_repository_name(
        self, programming_language: Optional[str] = None
    ) -> str:
        """Resolve repository name based on programming language.

        Args:
            programming_language: Optional programming language override

        Returns:
            Repository name for the determined language
        """
        if programming_language:
            return self._get_repository_for_language(programming_language)

        return PYTHON_REPOSITORY_NAME

    def _get_repository_for_language(self, programming_language: str) -> str:
        """Get repository name for a specific programming language.

        Args:
            programming_language: Programming language (case-insensitive)

        Returns:
            Repository name for the language, defaults to Python for unknown languages
        """
        language_upper = programming_language.upper()

        if language_upper == "JAVA":
            return JAVA_REPOSITORY_NAME

        if language_upper == "PYTHON":
            return PYTHON_REPOSITORY_NAME

        return PYTHON_REPOSITORY_NAME


class ParameterBasedRepositoryResolver(RepositoryResolver):
    """
    Repository resolver that prioritizes explicit programming_language parameter.
    Useful for functions that receive programming_language as a parameter.
    """

    def resolve_repository_name(
        self, programming_language: Optional[str] = None
    ) -> str:
        """
        Resolve repository name with priority on programming_language parameter.

        Args:
            programming_language: Programming language parameter

        Returns:
            Repository name
        """
        if programming_language:
            language_upper = programming_language.upper()
            if language_upper == "JAVA":
                return JAVA_REPOSITORY_NAME
            elif language_upper == "PYTHON":
                return PYTHON_REPOSITORY_NAME

        default_resolver = DefaultRepositoryResolver()
        return default_resolver.resolve_repository_name(programming_language)


class RepositoryResolverFactory:
    """
    Factory for creating repository resolvers.
    Provides a centralized way to get the appropriate resolver.
    """

    @staticmethod
    def get_default_resolver() -> RepositoryResolver:
        """Get the default repository resolver."""
        return DefaultRepositoryResolver()

    @staticmethod
    def get_parameter_based_resolver() -> RepositoryResolver:
        """Get parameter-based repository resolver."""
        return ParameterBasedRepositoryResolver()

    @staticmethod
    def get_resolver_for_context(
        has_programming_language_param: bool = False,
    ) -> RepositoryResolver:
        """
        Get appropriate resolver based on context.

        Args:
            has_programming_language_param: Whether the calling function has programming_language parameter

        Returns:
            Appropriate repository resolver
        """
        if has_programming_language_param:
            return ParameterBasedRepositoryResolver()
        else:
            return DefaultRepositoryResolver()


def resolve_repository_name(programming_language: Optional[str] = None) -> str:
    """Resolve repository name using default resolution strategy.

    Args:
        programming_language: Optional programming language override

    Returns:
        Repository name
    """
    resolver = RepositoryResolverFactory.get_default_resolver()
    return resolver.resolve_repository_name(programming_language)


def resolve_repository_name_with_language_param(
    programming_language: Optional[str] = None,
) -> str:
    """Resolve repository name with priority on programming_language parameter.

    Args:
        programming_language: Programming language parameter with high priority

    Returns:
        Repository name based on parameter-prioritized resolution
    """
    resolver = RepositoryResolverFactory.get_parameter_based_resolver()
    return resolver.resolve_repository_name(programming_language)
