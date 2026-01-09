"""
Search condition converter for transforming between formats.

Provides conversion from SearchConditionRequest to Cyoda API format.
"""

import logging
from typing import Any, Dict

from common.search.condition_builder import SearchCondition, SearchConditionRequest
from common.search.operators import CyodaOperator

logger = logging.getLogger(__name__)


class SearchConditionConverter:
    """Converts search conditions between formats."""

    @staticmethod
    def to_cyoda_format(request: SearchConditionRequest) -> Dict[str, Any]:
        """
        Convert SearchConditionRequest directly to Cyoda format.

        This is a single-step conversion that eliminates double mapping.
        """
        if not request.conditions:
            return {"type": "group", "operator": "AND", "conditions": []}

        # Convert each condition to Cyoda format
        cyoda_conditions = [
            SearchConditionConverter._condition_to_cyoda(cond)
            for cond in request.conditions
        ]

        # Always wrap in group format - Cyoda API requires this
        return {
            "type": "group",
            "operator": request.operator.upper(),
            "conditions": cyoda_conditions,
        }

    @staticmethod
    def _condition_to_cyoda(condition: SearchCondition) -> Dict[str, Any]:
        """Convert a single SearchCondition to Cyoda format."""
        field = condition.field
        cyoda_operator = condition.operator.value
        value = condition.value

        # Special handling for state/current_state fields
        if field in ["state", "current_state"]:
            return {
                "type": "lifecycle",
                "field": field,
                "operatorType": cyoda_operator,
                "value": value,
            }

        # Standard simple condition
        json_path = f"$.{field}" if not field.startswith("$.") else field
        return {
            "type": "simple",
            "jsonPath": json_path,
            "operatorType": cyoda_operator,
            "value": value,
        }

    @staticmethod
    def from_cyoda_format(cyoda_condition: Dict[str, Any]) -> SearchConditionRequest:
        """
        Convert Cyoda format back to SearchConditionRequest.

        Useful for parsing Cyoda search results or conditions.
        """
        builder = SearchConditionRequest.builder()

        if cyoda_condition.get("type") == "group":
            # Handle group conditions
            operator = cyoda_condition.get("operator", "AND").lower()
            if operator in ["and", "or"]:
                builder.operator(
                    __import__(
                        "common.search.operators", fromlist=["LogicalOperator"]
                    ).LogicalOperator[operator.upper()]
                )

            conditions = cyoda_condition.get("conditions", [])
            for cond in conditions:
                SearchConditionConverter._add_cyoda_condition_to_builder(cond, builder)
        else:
            # Single condition
            SearchConditionConverter._add_cyoda_condition_to_builder(
                cyoda_condition, builder
            )

        return builder.build()

    @staticmethod
    def _add_cyoda_condition_to_builder(
        cyoda_condition: Dict[str, Any], builder: Any
    ) -> None:
        """Add a Cyoda condition to the builder."""
        condition_type = cyoda_condition.get("type")

        if condition_type == "lifecycle":
            field = cyoda_condition.get("field", "state")
            operator_type = cyoda_condition.get("operatorType", "EQUALS")
            value = cyoda_condition.get("value")
        elif condition_type == "simple":
            json_path = cyoda_condition.get("jsonPath", "")
            field = (
                json_path.replace("$.", "") if json_path.startswith("$.") else json_path
            )
            operator_type = cyoda_condition.get("operatorType", "EQUALS")
            value = cyoda_condition.get("value")
        else:
            return

        # Use CyodaOperator directly
        cyoda_operator = CyodaOperator(operator_type)
        builder.add_condition(field, cyoda_operator, value)
