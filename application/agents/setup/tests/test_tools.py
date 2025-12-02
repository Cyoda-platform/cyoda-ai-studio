"""Tests for Setup agent tools."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from application.agents.setup.tools import (
    check_project_structure,
    validate_environment,
    validate_workflow_file,
)


def test_validate_environment_all_present(monkeypatch):
    """Test validation when all vars are present."""
    monkeypatch.setenv("CYODA_HOST", "localhost")
    monkeypatch.setenv("CYODA_PORT", "8080")
    monkeypatch.setenv("GOOGLE_MODEL", "gemini-2.0-flash-exp")

    result = validate_environment(["CYODA_HOST", "CYODA_PORT", "GOOGLE_MODEL"])

    assert result["CYODA_HOST"] is True
    assert result["CYODA_PORT"] is True
    assert result["GOOGLE_MODEL"] is True


def test_validate_environment_some_missing(monkeypatch):
    """Test validation when some vars are missing."""
    monkeypatch.setenv("CYODA_HOST", "localhost")
    monkeypatch.delenv("CYODA_PORT", raising=False)

    result = validate_environment(["CYODA_HOST", "CYODA_PORT"])

    assert result["CYODA_HOST"] is True
    assert result["CYODA_PORT"] is False


def test_validate_environment_default_vars(monkeypatch):
    """Test validation with default variable list."""
    monkeypatch.setenv("CYODA_HOST", "localhost")
    monkeypatch.setenv("CYODA_PORT", "8080")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)

    result = validate_environment()

    assert "CYODA_HOST" in result
    assert "CYODA_PORT" in result
    assert "GOOGLE_MODEL" in result
    assert "GOOGLE_API_KEY" in result


def test_check_project_structure_valid(tmp_path, monkeypatch):
    """Test project structure check with valid structure."""
    # Create required items
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "application").mkdir()
    (tmp_path / "common").mkdir()
    (tmp_path / ".env").touch()
    (tmp_path / ".venv").mkdir()

    monkeypatch.chdir(tmp_path)

    result = check_project_structure()

    assert result["is_valid"] is True
    assert len(result["missing_items"]) == 0
    assert "pyproject.toml" in result["present_items"]
    assert "application" in result["present_items"]


def test_check_project_structure_missing_items(tmp_path, monkeypatch):
    """Test project structure check with missing items."""
    # Create only some items
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "application").mkdir()

    monkeypatch.chdir(tmp_path)

    result = check_project_structure()

    assert result["is_valid"] is False
    assert "common" in result["missing_items"]
    assert ".env" in result["missing_items"]
    assert ".venv" in result["missing_items"]
    assert len(result["recommendations"]) > 0


def test_validate_workflow_file_valid():
    """Test workflow file validation with valid file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        workflow_data = {
            "name": "test_workflow",
            "states": ["DRAFT", "VALIDATED"],
            "transitions": [{"from": "DRAFT", "to": "VALIDATED"}],
        }
        json.dump(workflow_data, f)
        temp_path = f.name

    try:
        result = validate_workflow_file(temp_path)

        assert result["is_valid"] is True
        assert result["exists"] is True
        assert result["error"] is None
        assert result["workflow_name"] == "test_workflow"
        assert result["num_states"] == 2
        assert result["num_transitions"] == 1
    finally:
        Path(temp_path).unlink()


def test_validate_workflow_file_missing():
    """Test workflow file validation with missing file."""
    result = validate_workflow_file("/nonexistent/workflow.json")

    assert result["is_valid"] is False
    assert result["exists"] is False
    assert "not found" in result["error"].lower()


def test_validate_workflow_file_invalid_json():
    """Test workflow file validation with invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ invalid json }")
        temp_path = f.name

    try:
        result = validate_workflow_file(temp_path)

        assert result["is_valid"] is False
        assert result["exists"] is True
        assert "Invalid JSON" in result["error"]
    finally:
        Path(temp_path).unlink()


def test_validate_workflow_file_missing_fields():
    """Test workflow file validation with missing required fields."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        workflow_data = {"name": "test_workflow"}  # Missing states and transitions
        json.dump(workflow_data, f)
        temp_path = f.name

    try:
        result = validate_workflow_file(temp_path)

        assert result["is_valid"] is False
        assert result["exists"] is True
        assert "Missing required fields" in result["error"]
    finally:
        Path(temp_path).unlink()
