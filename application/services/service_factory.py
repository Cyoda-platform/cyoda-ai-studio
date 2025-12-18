"""
Service Factory for centralized service initialization.

Implements the Factory pattern for creating and managing service instances.
Provides singleton access to services across the application.
"""

import logging
from typing import Optional

from application.repositories.conversation_repository import ConversationRepository
from application.repositories.task_repository import TaskRepository
from application.services.chat_service import ChatService
from application.services.config_service import ConfigService, get_config_service
from application.services.edge_message_persistence_service import (
    EdgeMessagePersistenceService,
)
from application.services.logs_service import LogsService
from application.services.metrics_service import MetricsService
from services.services import get_entity_service, get_task_service

logger = logging.getLogger(__name__)


class ServiceFactory:
    """
    Factory for creating and managing service instances.

    Implements singleton pattern for services to ensure single instance
    across the application. Manages dependencies between services.
    """

    _instance: Optional["ServiceFactory"] = None

    # Service instances (lazy-loaded)
    _config_service: Optional[ConfigService] = None
    _chat_service: Optional[ChatService] = None
    _logs_service: Optional[LogsService] = None
    _metrics_service: Optional[MetricsService] = None
    _conversation_repository: Optional[ConversationRepository] = None
    _task_repository: Optional[TaskRepository] = None
    _persistence_service: Optional[EdgeMessagePersistenceService] = None

    def __new__(cls):
        """Ensure only one instance exists (Singleton pattern)."""
        if cls._instance is None:
            cls._instance = super(ServiceFactory, cls).__new__(cls)
            logger.debug("ServiceFactory instance created")
        return cls._instance

    @property
    def config_service(self) -> ConfigService:
        """
        Get ConfigService instance.

        Returns:
            ConfigService: Configuration service singleton

        Example:
            >>> factory = ServiceFactory()
            >>> config = factory.config_service
        """
        if self._config_service is None:
            self._config_service = get_config_service()
            logger.debug("ConfigService initialized")
        return self._config_service

    @property
    def persistence_service(self) -> EdgeMessagePersistenceService:
        """
        Get EdgeMessagePersistenceService instance.

        Returns:
            EdgeMessagePersistenceService: Message persistence service

        Example:
            >>> factory = ServiceFactory()
            >>> persistence = factory.persistence_service
        """
        if self._persistence_service is None:
            from services.services import get_repository
            repository = get_repository()
            self._persistence_service = EdgeMessagePersistenceService(repository)
            logger.debug("EdgeMessagePersistenceService initialized")
        return self._persistence_service

    @property
    def conversation_repository(self) -> ConversationRepository:
        """
        Get ConversationRepository instance.

        Returns:
            ConversationRepository: Conversation data access repository

        Example:
            >>> factory = ServiceFactory()
            >>> repo = factory.conversation_repository
        """
        if self._conversation_repository is None:
            entity_service = get_entity_service()
            self._conversation_repository = ConversationRepository(entity_service)
            logger.debug("ConversationRepository initialized")
        return self._conversation_repository

    @property
    def task_repository(self) -> TaskRepository:
        """
        Get TaskRepository instance.

        Returns:
            TaskRepository: Task data access repository

        Example:
            >>> factory = ServiceFactory()
            >>> repo = factory.task_repository
        """
        if self._task_repository is None:
            task_service = get_task_service()
            self._task_repository = TaskRepository(task_service)
            logger.debug("TaskRepository initialized")
        return self._task_repository

    @property
    def chat_service(self) -> ChatService:
        """
        Get ChatService instance.

        Automatically initializes dependencies (repository, persistence).

        Returns:
            ChatService: Chat business logic service

        Example:
            >>> factory = ServiceFactory()
            >>> chat = factory.chat_service
        """
        if self._chat_service is None:
            self._chat_service = ChatService(
                conversation_repository=self.conversation_repository,
                persistence_service=self.persistence_service,
            )
            logger.debug("ChatService initialized")
        return self._chat_service

    @property
    def logs_service(self) -> LogsService:
        """
        Get LogsService instance.

        Automatically initializes ConfigService dependency.

        Returns:
            LogsService: Elasticsearch log management service

        Example:
            >>> factory = ServiceFactory()
            >>> logs = factory.logs_service
        """
        if self._logs_service is None:
            self._logs_service = LogsService(self.config_service)
            logger.debug("LogsService initialized")
        return self._logs_service

    @property
    def metrics_service(self) -> MetricsService:
        """
        Get MetricsService instance.

        Automatically initializes ConfigService dependency.

        Returns:
            MetricsService: Prometheus/Grafana metrics service

        Example:
            >>> factory = ServiceFactory()
            >>> metrics = factory.metrics_service
        """
        if self._metrics_service is None:
            self._metrics_service = MetricsService(self.config_service)
            logger.debug("MetricsService initialized")
        return self._metrics_service

    def clear_cache(self):
        """
        Clear all cached service instances.

        Useful for testing or when services need to be re-initialized.

        Example:
            >>> factory = ServiceFactory()
            >>> factory.clear_cache()  # Force re-initialization
        """
        self._config_service = None
        self._chat_service = None
        self._logs_service = None
        self._metrics_service = None
        self._conversation_repository = None
        self._task_repository = None
        self._persistence_service = None
        logger.debug("ServiceFactory cache cleared")


# Global factory instance
_factory_instance: Optional[ServiceFactory] = None


def get_service_factory() -> ServiceFactory:
    """
    Get global ServiceFactory instance.

    Returns:
        ServiceFactory: Singleton factory instance

    Example:
        >>> from application.services.service_factory import get_service_factory
        >>> factory = get_service_factory()
        >>> chat_service = factory.chat_service
        >>> logs_service = factory.logs_service
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = ServiceFactory()
    return _factory_instance
