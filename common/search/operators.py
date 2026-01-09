"""
Unified operator definitions.

This module provides a single source of truth for all operators.
We use CyodaOperator directly throughout the codebase - no intermediate format needed.
"""

from enum import Enum


class CyodaOperator(Enum):
    """Cyoda API operators."""

    # Equality operators
    EQUALS = "EQUALS"
    NOT_EQUAL = "NOT_EQUAL"
    IEQUALS = "IEQUALS"
    INOT_EQUAL = "INOT_EQUAL"

    # Null checks
    IS_NULL = "IS_NULL"
    NOT_NULL = "NOT_NULL"

    # Comparison operators
    GREATER_THAN = "GREATER_THAN"
    GREATER_OR_EQUAL = "GREATER_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_OR_EQUAL = "LESS_OR_EQUAL"

    # Text operators
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT_CONTAINS"
    STARTS_WITH = "STARTS_WITH"
    NOT_STARTS_WITH = "NOT_STARTS_WITH"
    ENDS_WITH = "ENDS_WITH"
    NOT_ENDS_WITH = "NOT_ENDS_WITH"

    # Case-insensitive text operators
    ICONTAINS = "ICONTAINS"
    INOT_CONTAINS = "INOT_CONTAINS"
    ISTARTS_WITH = "ISTARTS_WITH"
    INOT_STARTS_WITH = "INOT_STARTS_WITH"
    IENDS_WITH = "IENDS_WITH"
    INOT_ENDS_WITH = "INOT_ENDS_WITH"

    # Pattern matching
    MATCHES_PATTERN = "MATCHES_PATTERN"
    LIKE = "LIKE"

    # Range operators
    BETWEEN = "BETWEEN"
    BETWEEN_INCLUSIVE = "BETWEEN_INCLUSIVE"

    # Change detection
    IS_UNCHANGED = "IS_UNCHANGED"
    IS_CHANGED = "IS_CHANGED"


class LogicalOperator(Enum):
    """Logical operators for combining search conditions."""

    AND = "and"
    OR = "or"
