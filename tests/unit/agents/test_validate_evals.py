"""Tests for validate_test_file function in application/agents/validate_evals.py."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from application.agents.validate_evals import validate_test_file


class TestValidateTestFile:
    """Tests for validate_test_file with >=70% coverage."""

    def test_valid_test_file(self):
        """Test validation of valid test file."""
        valid_data = {
            "eval_set_id": "test-set-1",
            "name": "Test Evaluations",
            "eval_cases": [
                {
                    "eval_id": "eval-1",
                    "conversation": [
                        {
                            "user_content": "Test question",
                            "final_response": "Test response",
                            "intermediate_data": {
                                "tool_uses": [{"name": "test_tool", "args": {}}]
                            }
                        }
                    ]
                }
            ]
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(valid_data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is True
            assert "Valid" in message
            assert "1 cases" in message

    def test_invalid_json(self):
        """Test validation with invalid JSON."""
        with patch('builtins.open', mock_open(read_data="invalid json")):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "Invalid JSON" in message

    def test_missing_eval_set_id(self):
        """Test validation with missing eval_set_id."""
        data = {
            "name": "Test",
            "eval_cases": []
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "eval_set_id" in message

    def test_missing_name(self):
        """Test validation with missing name."""
        data = {
            "eval_set_id": "test-1",
            "eval_cases": []
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "name" in message

    def test_eval_cases_not_list(self):
        """Test validation when eval_cases is not a list."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": "not a list"
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "must be a list" in message

    def test_empty_eval_cases(self):
        """Test validation with empty eval_cases."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": []
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "empty" in message

    def test_missing_eval_id(self):
        """Test validation with missing eval_id in case."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [{"conversation": []}]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "eval_id" in message

    def test_missing_conversation(self):
        """Test validation with missing conversation."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [{"eval_id": "case-1"}]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "conversation" in message

    def test_conversation_not_list(self):
        """Test validation when conversation is not a list."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [
                {
                    "eval_id": "case-1",
                    "conversation": "not a list"
                }
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "must be a list" in message

    def test_missing_user_content(self):
        """Test validation with missing user_content."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [
                {
                    "eval_id": "case-1",
                    "conversation": [{"final_response": "resp"}]
                }
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "user_content" in message

    def test_missing_final_response(self):
        """Test validation with missing final_response."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [
                {
                    "eval_id": "case-1",
                    "conversation": [{"user_content": "question"}]
                }
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "final_response" in message

    def test_missing_intermediate_data(self):
        """Test validation with missing intermediate_data."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [
                {
                    "eval_id": "case-1",
                    "conversation": [
                        {
                            "user_content": "q",
                            "final_response": "r"
                        }
                    ]
                }
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "intermediate_data" in message

    def test_missing_tool_uses(self):
        """Test validation with missing tool_uses."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [
                {
                    "eval_id": "case-1",
                    "conversation": [
                        {
                            "user_content": "q",
                            "final_response": "r",
                            "intermediate_data": {}
                        }
                    ]
                }
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "tool_uses" in message

    def test_tool_uses_not_list(self):
        """Test validation when tool_uses is not a list."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [
                {
                    "eval_id": "case-1",
                    "conversation": [
                        {
                            "user_content": "q",
                            "final_response": "r",
                            "intermediate_data": {"tool_uses": "not a list"}
                        }
                    ]
                }
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "must be a list" in message

    def test_missing_tool_name(self):
        """Test validation with missing tool name."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [
                {
                    "eval_id": "case-1",
                    "conversation": [
                        {
                            "user_content": "q",
                            "final_response": "r",
                            "intermediate_data": {"tool_uses": [{"args": {}}]}
                        }
                    ]
                }
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "tool name" in message

    def test_missing_tool_args(self):
        """Test validation with missing tool args."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [
                {
                    "eval_id": "case-1",
                    "conversation": [
                        {
                            "user_content": "q",
                            "final_response": "r",
                            "intermediate_data": {"tool_uses": [{"name": "tool1"}]}
                        }
                    ]
                }
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "tool args" in message

    def test_multiple_cases(self):
        """Test validation with multiple valid cases."""
        data = {
            "eval_set_id": "test-1",
            "name": "Test",
            "eval_cases": [
                {
                    "eval_id": f"case-{i}",
                    "conversation": [
                        {
                            "user_content": f"q{i}",
                            "final_response": f"r{i}",
                            "intermediate_data": {"tool_uses": []}
                        }
                    ]
                }
                for i in range(3)
            ]
        }
        with patch('builtins.open', mock_open(read_data=json.dumps(data))):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is True
            assert "3 cases" in message

    def test_file_read_exception(self):
        """Test validation with file read exception."""
        with patch('builtins.open', side_effect=IOError("File error")):
            valid, message = validate_test_file(Path("test.json"))
            assert valid is False
            assert "Error" in message

