"""Resource Limit Service for User Quota Management.

This service manages resource limits and quotas for user operations.
Currently implements simple hard-coded limits, but designed to be extended
with user quota service integration in the future.
"""

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits for user operations."""

    max_replicas: int = 3  # Maximum replicas per user app deployment
    max_apps_per_environment: int = 10  # Maximum apps per environment
    max_environments: int = 5  # Maximum environments per user
    max_cpu_per_app: str = "2"  # Maximum CPU cores per app (e.g., "2" = 2 cores)
    max_memory_per_app: str = "4Gi"  # Maximum memory per app


@dataclass
class QuotaCheckResult:
    """Result of a quota/limit check."""

    allowed: bool
    reason: Optional[str] = None
    limit_value: Optional[int] = None
    current_value: Optional[int] = None


class ResourceLimitService:
    """Service for checking and enforcing resource limits.

    This service provides centralized limit checking for user operations.
    Future integration points:
    - User quota service API
    - Database-backed quota management
    - Per-user tier limits (free, paid, enterprise)
    - Dynamic quota adjustments
    """

    def __init__(self):
        """Initialize the resource limit service."""
        self.limits = self._load_limits()
        logger.info(
            f"ResourceLimitService initialized with max_replicas={self.limits.max_replicas}"
        )

    def _load_limits(self) -> ResourceLimits:
        """Load resource limits from configuration.

        Currently loads from environment variables with defaults.
        Future: Load from user quota service or database.

        Returns:
            ResourceLimits configuration
        """
        return ResourceLimits(
            max_replicas=int(os.getenv("MAX_REPLICAS_PER_APP", "3")),
            max_apps_per_environment=int(os.getenv("MAX_APPS_PER_ENVIRONMENT", "10")),
            max_environments=int(os.getenv("MAX_ENVIRONMENTS_PER_USER", "5")),
            max_cpu_per_app=os.getenv("MAX_CPU_PER_APP", "2"),
            max_memory_per_app=os.getenv("MAX_MEMORY_PER_APP", "4Gi"),
        )

    def check_replica_limit(
        self,
        user_id: str,
        env_name: str,
        app_name: str,
        requested_replicas: int
    ) -> QuotaCheckResult:
        """Check if requested replica count is within limits.

        Args:
            user_id: User ID requesting the operation
            env_name: Environment name
            app_name: Application name
            requested_replicas: Number of replicas requested

        Returns:
            QuotaCheckResult indicating if operation is allowed
        """
        if requested_replicas < 0:
            return QuotaCheckResult(
                allowed=False,
                reason="Replicas must be >= 0",
                limit_value=0,
                current_value=requested_replicas,
            )

        if requested_replicas > self.limits.max_replicas:
            logger.warning(
                f"Replica limit exceeded for user={user_id}, env={env_name}, "
                f"app={app_name}: requested={requested_replicas}, "
                f"limit={self.limits.max_replicas}"
            )
            return QuotaCheckResult(
                allowed=False,
                reason=f"Replica count exceeds maximum limit of {self.limits.max_replicas}",
                limit_value=self.limits.max_replicas,
                current_value=requested_replicas,
            )

        logger.debug(
            f"Replica limit check passed for user={user_id}, env={env_name}, "
            f"app={app_name}, replicas={requested_replicas}"
        )
        return QuotaCheckResult(
            allowed=True,
            limit_value=self.limits.max_replicas,
            current_value=requested_replicas,
        )

    def check_app_count_limit(
        self,
        user_id: str,
        env_name: str,
        current_app_count: int
    ) -> QuotaCheckResult:
        """Check if user can create another app in the environment.

        Args:
            user_id: User ID requesting the operation
            env_name: Environment name
            current_app_count: Current number of apps in environment

        Returns:
            QuotaCheckResult indicating if operation is allowed
        """
        if current_app_count >= self.limits.max_apps_per_environment:
            logger.warning(
                f"App count limit exceeded for user={user_id}, env={env_name}: "
                f"current={current_app_count}, limit={self.limits.max_apps_per_environment}"
            )
            return QuotaCheckResult(
                allowed=False,
                reason=f"Maximum {self.limits.max_apps_per_environment} apps per environment",
                limit_value=self.limits.max_apps_per_environment,
                current_value=current_app_count,
            )

        return QuotaCheckResult(
            allowed=True,
            limit_value=self.limits.max_apps_per_environment,
            current_value=current_app_count,
        )

    def check_environment_count_limit(
        self,
        user_id: str,
        current_env_count: int
    ) -> QuotaCheckResult:
        """Check if user can create another environment.

        Args:
            user_id: User ID requesting the operation
            current_env_count: Current number of environments

        Returns:
            QuotaCheckResult indicating if operation is allowed
        """
        if current_env_count >= self.limits.max_environments:
            logger.warning(
                f"Environment count limit exceeded for user={user_id}: "
                f"current={current_env_count}, limit={self.limits.max_environments}"
            )
            return QuotaCheckResult(
                allowed=False,
                reason=f"Maximum {self.limits.max_environments} environments per user",
                limit_value=self.limits.max_environments,
                current_value=current_env_count,
            )

        return QuotaCheckResult(
            allowed=True,
            limit_value=self.limits.max_environments,
            current_value=current_env_count,
        )

    def get_user_limits(self, user_id: str) -> ResourceLimits:
        """Get resource limits for a specific user.

        Currently returns global limits for all users.
        Future: Return user-specific limits based on tier/subscription.

        Args:
            user_id: User ID

        Returns:
            ResourceLimits for the user
        """
        # Future: Query user quota service
        # return await user_quota_service.get_limits(user_id)
        return self.limits

    def format_limit_error(self, result: QuotaCheckResult) -> str:
        """Format a user-friendly error message from quota check result.

        Args:
            result: QuotaCheckResult from a limit check

        Returns:
            Formatted error message
        """
        if result.allowed:
            return ""

        msg = f"❌ {result.reason}"
        if result.limit_value is not None and result.current_value is not None:
            msg += f"\n   Requested: {result.current_value}"
            msg += f"\n   Limit: {result.limit_value}"

        return msg


# Global singleton instance
_resource_limit_service: Optional[ResourceLimitService] = None


def get_resource_limit_service() -> ResourceLimitService:
    """Get the global ResourceLimitService instance.

    Returns:
        Singleton ResourceLimitService instance
    """
    global _resource_limit_service
    if _resource_limit_service is None:
        _resource_limit_service = ResourceLimitService()
    return _resource_limit_service
