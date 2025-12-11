"""
Customer Entity Processors

Implements three processors for Customer entity:
- validate_customer: Validates customer data before creation/update
- apply_customer_update: Applies updates to customer records
- archive_customer: Archives customer records
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from common.entity.entity_casting import cast_entity
from common.processor.base import CyodaEntity, CyodaProcessor


logger = logging.getLogger(__name__)


class ValidateCustomerProcessor(CyodaProcessor):
    """Validates customer data before creation or update."""

    def __init__(self) -> None:
        super().__init__(
            name="ValidateCustomerProcessor",
            description="Validates customer data integrity and business rules",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Validate customer entity data.

        Args:
            entity: The customer entity to validate
            **kwargs: Additional processing parameters

        Returns:
            The validated entity
        """
        try:
            logger.info(f"Validating customer {getattr(entity, 'technical_id', '<unknown>')}")

            # Validate required fields
            if not hasattr(entity, 'email') or not entity.email:
                raise ValueError("Email is required")

            if not hasattr(entity, 'name') or not entity.name:
                raise ValueError("Customer name is required")

            # Validate email format
            if '@' not in entity.email or '.' not in entity.email.split('@')[1]:
                raise ValueError("Invalid email format")

            # Validate name length
            if len(entity.name.strip()) < 2:
                raise ValueError("Customer name must be at least 2 characters")

            logger.info(f"Customer {entity.technical_id} validation passed")
            return entity

        except Exception as e:
            logger.error(f"Validation error for customer: {str(e)}")
            raise


class ApplyCustomerUpdateProcessor(CyodaProcessor):
    """Applies updates to customer records."""

    def __init__(self) -> None:
        super().__init__(
            name="ApplyCustomerUpdateProcessor",
            description="Applies updates to customer records with audit trail",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Apply updates to customer entity.

        Args:
            entity: The customer entity to update
            **kwargs: Additional processing parameters

        Returns:
            The updated entity with audit information
        """
        try:
            logger.info(f"Applying updates to customer {getattr(entity, 'technical_id', '<unknown>')}")

            # Add update timestamp
            current_timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            if hasattr(entity, 'updated_at'):
                entity.updated_at = current_timestamp

            # Add audit trail if available
            if hasattr(entity, 'last_modified_by'):
                entity.last_modified_by = kwargs.get('user_id', 'system')

            logger.info(f"Customer {entity.technical_id} updated successfully")
            return entity

        except Exception as e:
            logger.error(f"Error applying customer update: {str(e)}")
            raise


class ArchiveCustomerProcessor(CyodaProcessor):
    """Archives customer records."""

    def __init__(self) -> None:
        super().__init__(
            name="ArchiveCustomerProcessor",
            description="Archives customer records and marks them as inactive",
        )

    async def process(self, entity: CyodaEntity, **kwargs: Any) -> CyodaEntity:
        """
        Archive customer entity.

        Args:
            entity: The customer entity to archive
            **kwargs: Additional processing parameters

        Returns:
            The archived entity
        """
        try:
            logger.info(f"Archiving customer {getattr(entity, 'technical_id', '<unknown>')}")

            # Mark as archived
            if hasattr(entity, 'is_active'):
                entity.is_active = False

            if hasattr(entity, 'archived_at'):
                entity.archived_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

            if hasattr(entity, 'archived_by'):
                entity.archived_by = kwargs.get('user_id', 'system')

            logger.info(f"Customer {entity.technical_id} archived successfully")
            return entity

        except Exception as e:
            logger.error(f"Error archiving customer: {str(e)}")
            raise

