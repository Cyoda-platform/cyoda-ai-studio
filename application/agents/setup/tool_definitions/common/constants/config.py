"""Configuration for the Setup agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class SetupConfig:
    """Configuration values for the Setup agent."""

    # Cyoda environment configuration
    cyoda_host: str = os.getenv("CYODA_HOST", "")
    cyoda_port: str = os.getenv("CYODA_PORT", "")
    cyoda_grpc_host: str = os.getenv("CYODA_GRPC_HOST", "")
    cyoda_grpc_port: str = os.getenv("CYODA_GRPC_PORT", "")

    # Client configuration
    client_host: str = os.getenv("CLIENT_HOST", "cyoda.cloud")

    # Cloud manager configuration
    cloud_manager_host: Optional[str] = os.getenv("CLOUD_MANAGER_HOST")
    deploy_status_url: Optional[str] = os.getenv("DEPLOY_CYODA_ENV_STATUS")

    # Google/LLM configuration
    google_model: str = os.getenv("GOOGLE_MODEL", "")
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")

    def get_deploy_status_url(self) -> str:
        """Get the deployment status URL."""
        if self.deploy_status_url:
            return self.deploy_status_url

        if not self.cloud_manager_host:
            raise ValueError("CLOUD_MANAGER_HOST not configured")

        protocol = "http" if "localhost" in self.cloud_manager_host else "https"
        return f"{protocol}://{self.cloud_manager_host}/deploy/cyoda-env/status"

    def get_client_url(self, user_id: str) -> str:
        """Get the client URL for a user."""
        return f"https://client-{user_id.lower()}.{self.client_host}"


# Global config instance
config = SetupConfig()
