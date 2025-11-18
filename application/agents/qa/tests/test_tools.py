"""Tests for QA agent tools."""

from __future__ import annotations

from application.agents.qa.tools import explain_cyoda_pattern, search_cyoda_concepts


def test_search_cyoda_concepts_found():
    """Test searching for existing concepts."""
    result = search_cyoda_concepts("technical id")

    assert result["found"] is True
    assert "technical id" in result["matches"]
    assert "definition" in result["matches"]["technical id"]


def test_search_cyoda_concepts_entity():
    """Test searching for entity concept."""
    result = search_cyoda_concepts("entity")

    assert result["found"] is True
    assert "entity" in result["matches"]
    assert "components" in result["matches"]["entity"]


def test_search_cyoda_concepts_not_found():
    """Test searching for non-existent concept."""
    result = search_cyoda_concepts("nonexistent concept")

    assert result["found"] is False
    assert "suggestion" in result


def test_search_cyoda_concepts_partial_match():
    """Test partial matching of concepts."""
    result = search_cyoda_concepts("work")  # Should match 'workflow'

    assert result["found"] is True
    assert "workflow" in result["matches"]


def test_explain_cyoda_pattern_found():
    """Test explaining existing pattern."""
    result = explain_cyoda_pattern("thin routes")

    assert result["found"] is True
    assert result["pattern"] == "thin routes"
    assert "principle" in result["details"]
    assert "reason" in result["details"]


def test_explain_cyoda_pattern_no_reflection():
    """Test explaining no reflection pattern."""
    result = explain_cyoda_pattern("no reflection")

    assert result["found"] is True
    assert result["pattern"] == "no reflection"
    assert "instead" in result["details"]


def test_explain_cyoda_pattern_not_found():
    """Test explaining non-existent pattern."""
    result = explain_cyoda_pattern("nonexistent pattern")

    assert result["found"] is False
    assert "available_patterns" in result


def test_explain_cyoda_pattern_partial_match():
    """Test partial matching of patterns."""
    result = explain_cyoda_pattern("manual")  # Should match 'manual transitions'

    assert result["found"] is True
    assert "manual transitions" in result["pattern"]
