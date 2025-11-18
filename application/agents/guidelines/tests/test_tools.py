"""Tests for Guidelines agent tools."""

from __future__ import annotations

from application.agents.guidelines.tools import (
    get_design_principle,
    get_testing_guideline,
)


def test_get_design_principle_found():
    """Test getting existing design principle."""
    result = get_design_principle("no reflection")

    assert result["found"] is True
    assert result["principle"] == "no reflection"
    assert "description" in result["details"]
    assert "rationale" in result["details"]


def test_get_design_principle_thin_routes():
    """Test getting thin routes principle."""
    result = get_design_principle("thin routes")

    assert result["found"] is True
    assert result["principle"] == "thin routes"
    assert "pattern" in result["details"]


def test_get_design_principle_not_found():
    """Test getting non-existent principle."""
    result = get_design_principle("nonexistent principle")

    assert result["found"] is False
    assert "available_principles" in result


def test_get_design_principle_partial_match():
    """Test partial matching of principles."""
    result = get_design_principle("manual")  # Should match 'manual transitions only'

    assert result["found"] is True
    assert "manual transitions only" in result["principle"]


def test_get_testing_guideline_found():
    """Test getting existing testing guideline."""
    result = get_testing_guideline("unit tests")

    assert result["found"] is True
    assert result["topic"] == "unit tests"
    assert "description" in result["details"]
    assert "coverage" in result["details"]


def test_get_testing_guideline_integration():
    """Test getting integration testing guideline."""
    result = get_testing_guideline("integration")

    assert result["found"] is True
    assert "integration tests" in result["topic"]
    assert "approach" in result["details"]


def test_get_testing_guideline_not_found():
    """Test getting non-existent guideline."""
    result = get_testing_guideline("nonexistent guideline")

    assert result["found"] is False
    assert "available_topics" in result


def test_get_testing_guideline_partial_match():
    """Test partial matching of guidelines."""
    result = get_testing_guideline("mock")  # Should match 'mocking'

    assert result["found"] is True
    assert "mocking" in result["topic"]
