"""
Search condition builder for constructing search queries.

Provides a fluent API for building complex search conditions using CyodaOperator.
"""

from dataclasses import dataclass
from typing import Any, List, Optional

from common.search.operators import CyodaOperator, LogicalOperator


@dataclass
class SearchCondition:
    """A single search condition."""

    field: str
    operator: CyodaOperator
    value: Any


@dataclass
class SearchConditionRequest:
    """Complex search request with multiple conditions."""

    conditions: List[SearchCondition]
    operator: str = "and"
    limit: Optional[int] = None
    offset: Optional[int] = None

    @classmethod
    def builder(cls) -> "SearchConditionRequestBuilder":
        """Create a builder for SearchConditionRequest."""
        return SearchConditionRequestBuilder()


class SearchConditionRequestBuilder:
    """Fluent builder for SearchConditionRequest."""

    def __init__(self) -> None:
        self._conditions: List[SearchCondition] = []
        self._operator = "and"
        self._limit: Optional[int] = None
        self._offset: Optional[int] = None

    def add_condition(
        self, field: str, operator: CyodaOperator, value: Any
    ) -> "SearchConditionRequestBuilder":
        """Add a search condition."""
        self._conditions.append(SearchCondition(field, operator, value))
        return self

    def equals(self, field: str, value: Any) -> "SearchConditionRequestBuilder":
        """Add equals condition."""
        return self.add_condition(field, CyodaOperator.EQUALS, value)

    def contains(self, field: str, value: str) -> "SearchConditionRequestBuilder":
        """Add contains condition."""
        return self.add_condition(field, CyodaOperator.CONTAINS, value)

    def operator(self, op: LogicalOperator) -> "SearchConditionRequestBuilder":
        """Set logical operator (and/or)."""
        self._operator = op.value
        return self

    def limit(self, limit: int) -> "SearchConditionRequestBuilder":
        """Set result limit."""
        self._limit = limit
        return self

    def offset(self, offset: int) -> "SearchConditionRequestBuilder":
        """Set result offset."""
        self._offset = offset
        return self

    def build(self) -> SearchConditionRequest:
        """Build the search request."""
        return SearchConditionRequest(
            conditions=self._conditions,
            operator=self._operator,
            limit=self._limit,
            offset=self._offset,
        )
