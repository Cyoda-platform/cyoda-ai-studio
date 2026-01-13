"""
Structured Output Handler for OpenAI SDK

Provides utilities for working with Pydantic schemas and structured outputs.
"""

import json
import logging
from typing import Any, Dict, Type, TypeVar

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputHandler:
    """Handle structured outputs with Pydantic schemas."""

    @staticmethod
    def validate_schema(schema: Type[T], data: Dict[str, Any]) -> T:
        """
        Validate data against Pydantic schema.

        Args:
            schema: Pydantic model class
            data: Dictionary to validate

        Returns:
            Validated instance of schema

        Raises:
            ValidationError: If data doesn't match schema
        """
        try:
            logger.debug(f"Validating data against schema: {schema.__name__}")
            return schema(**data)
        except ValidationError as e:
            logger.error(f"Schema validation failed for {schema.__name__}: {e}")
            raise

    @staticmethod
    def schema_to_json_schema(schema: Type[T]) -> Dict[str, Any]:
        """
        Convert Pydantic schema to JSON schema.

        Args:
            schema: Pydantic model class

        Returns:
            JSON schema dictionary

        Raises:
            Exception: If schema conversion fails
        """
        try:
            logger.debug(f"Converting schema to JSON: {schema.__name__}")
            json_schema = schema.model_json_schema()
            logger.debug(f"JSON schema generated: {len(json.dumps(json_schema))} bytes")
            return json_schema
        except Exception as e:
            logger.error(f"Failed to convert schema to JSON: {e}")
            raise

    @staticmethod
    def schema_to_dict(schema: Type[T]) -> Dict[str, Any]:
        """
        Convert Pydantic schema instance to dictionary.

        Args:
            schema: Pydantic model instance

        Returns:
            Dictionary representation

        Raises:
            Exception: If conversion fails
        """
        try:
            logger.debug(f"Converting schema instance to dict: {type(schema).__name__}")
            return schema.model_dump()
        except Exception as e:
            logger.error(f"Failed to convert schema to dict: {e}")
            raise

    @staticmethod
    def schema_to_json(schema: Type[T]) -> str:
        """
        Convert Pydantic schema instance to JSON string.

        Args:
            schema: Pydantic model instance

        Returns:
            JSON string representation

        Raises:
            Exception: If conversion fails
        """
        try:
            logger.debug(f"Converting schema instance to JSON: {type(schema).__name__}")
            return schema.model_dump_json()
        except Exception as e:
            logger.error(f"Failed to convert schema to JSON: {e}")
            raise

    @staticmethod
    def get_schema_fields(schema: Type[T]) -> Dict[str, Any]:
        """
        Get field information from Pydantic schema.

        Args:
            schema: Pydantic model class

        Returns:
            Dictionary of field names and their types

        Raises:
            Exception: If field extraction fails
        """
        try:
            logger.debug(f"Extracting fields from schema: {schema.__name__}")
            fields = {}
            for field_name, field_info in schema.model_fields.items():
                fields[field_name] = {
                    "type": str(field_info.annotation),
                    "required": field_info.is_required(),
                    "description": field_info.description or "",
                }
            logger.debug(f"Extracted {len(fields)} fields from schema")
            return fields
        except Exception as e:
            logger.error(f"Failed to extract fields from schema: {e}")
            raise

    @staticmethod
    def merge_schemas(schema1: Type[T], schema2: Type[T]) -> Dict[str, Any]:
        """
        Merge two Pydantic schemas.

        Args:
            schema1: First Pydantic model class
            schema2: Second Pydantic model class

        Returns:
            Merged JSON schema

        Raises:
            Exception: If merge fails
        """
        try:
            logger.debug(f"Merging schemas: {schema1.__name__} + {schema2.__name__}")
            json_schema1 = schema1.model_json_schema()
            json_schema2 = schema2.model_json_schema()

            merged = {
                "type": "object",
                "properties": {
                    **json_schema1.get("properties", {}),
                    **json_schema2.get("properties", {}),
                },
                "required": list(
                    set(
                        json_schema1.get("required", [])
                        + json_schema2.get("required", [])
                    )
                ),
            }
            logger.debug(f"Schemas merged successfully")
            return merged
        except Exception as e:
            logger.error(f"Failed to merge schemas: {e}")
            raise
