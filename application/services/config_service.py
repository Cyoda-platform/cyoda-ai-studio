"""
Configuration Service for centralized environment variable management.

Provides validated configuration objects for external services (ELK, Grafana, Prometheus).
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ELKConfig:
    """Elasticsearch/Kibana configuration."""

    host: str
    user: str
    password: str

    def __post_init__(self):
        """Validate required fields."""
        if not all([self.host, self.user, self.password]):
            raise ValueError(
                "ELK configuration incomplete. Please set ELK_HOST, ELK_USER, and ELK_PASSWORD"
            )


@dataclass
class GrafanaConfig:
    """Grafana configuration."""

    host: str
    admin_user: str
    admin_password: str

    def __post_init__(self):
        """Validate required fields."""
        if not all([self.host, self.admin_user, self.admin_password]):
            raise ValueError(
                "Grafana configuration incomplete. Please set GRAFANA_HOST, "
                "GRAFANA_ADMIN_USER, and GRAFANA_ADMIN_PASSWORD"
            )


@dataclass
class PrometheusConfig:
    """Prometheus configuration."""

    host: str
    user: Optional[str] = None
    password: Optional[str] = None

    def __post_init__(self):
        """Validate required fields."""
        if not self.host:
            raise ValueError("PROMETHEUS_HOST environment variable not set")


class ConfigService:
    """
    Service for loading and managing application configuration.

    Provides validated configuration objects with helpful error messages.
    Caches configuration objects after first load.
    """

    def __init__(self):
        """Initialize configuration service with empty cache."""
        self._elk_config: Optional[ELKConfig] = None
        self._grafana_config: Optional[GrafanaConfig] = None
        self._prometheus_config: Optional[PrometheusConfig] = None

    def get_elk_config(self) -> ELKConfig:
        """
        Get ELK (Elasticsearch/Kibana) configuration.

        Returns:
            ELKConfig: Validated ELK configuration

        Raises:
            ValueError: If required environment variables are missing

        Example:
            >>> config_service = ConfigService()
            >>> elk_config = config_service.get_elk_config()
            >>> print(elk_config.host)
        """
        if self._elk_config is None:
            elk_host = os.getenv("ELK_HOST")
            elk_user = os.getenv("ELK_USER")
            elk_password = os.getenv("ELK_PASSWORD")

            self._elk_config = ELKConfig(
                host=elk_host or "",
                user=elk_user or "",
                password=elk_password or "",
            )
            logger.debug(f"Loaded ELK configuration for host: {elk_host}")

        return self._elk_config

    def get_grafana_config(self) -> GrafanaConfig:
        """
        Get Grafana configuration.

        Returns:
            GrafanaConfig: Validated Grafana configuration

        Raises:
            ValueError: If required environment variables are missing

        Example:
            >>> config_service = ConfigService()
            >>> grafana_config = config_service.get_grafana_config()
            >>> print(grafana_config.host)
        """
        if self._grafana_config is None:
            grafana_host = os.getenv("GRAFANA_HOST")
            grafana_admin_user = os.getenv("GRAFANA_ADMIN_USER")
            grafana_admin_password = os.getenv("GRAFANA_ADMIN_PASSWORD")

            self._grafana_config = GrafanaConfig(
                host=grafana_host or "",
                admin_user=grafana_admin_user or "",
                admin_password=grafana_admin_password or "",
            )
            logger.debug(f"Loaded Grafana configuration for host: {grafana_host}")

        return self._grafana_config

    def get_prometheus_config(self) -> PrometheusConfig:
        """
        Get Prometheus configuration.

        Returns:
            PrometheusConfig: Validated Prometheus configuration

        Raises:
            ValueError: If PROMETHEUS_HOST is not set

        Example:
            >>> config_service = ConfigService()
            >>> prom_config = config_service.get_prometheus_config()
            >>> print(prom_config.host)
        """
        if self._prometheus_config is None:
            prometheus_host = os.getenv("PROMETHEUS_HOST")
            prometheus_user = os.getenv("PROMETHEUS_USER")
            prometheus_password = os.getenv("PROMETHEUS_PASSWORD")

            self._prometheus_config = PrometheusConfig(
                host=prometheus_host or "",
                user=prometheus_user,
                password=prometheus_password,
            )
            logger.debug(f"Loaded Prometheus configuration for host: {prometheus_host}")

        return self._prometheus_config

    def clear_cache(self):
        """
        Clear cached configuration objects.

        Useful for testing or when environment variables change at runtime.
        """
        self._elk_config = None
        self._grafana_config = None
        self._prometheus_config = None
        logger.debug("Configuration cache cleared")


# Singleton instance for application-wide use
_config_service_instance: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """
    Get singleton ConfigService instance.

    Returns:
        ConfigService: Shared configuration service instance

    Example:
        >>> from application.services.config_service import get_config_service
        >>> config = get_config_service()
        >>> elk_config = config.get_elk_config()
    """
    global _config_service_instance
    if _config_service_instance is None:
        _config_service_instance = ConfigService()
    return _config_service_instance
