"""
Unit tests for OpenAI Tool Converter
"""

import json
import pytest

from application.agents.shared.openai_tool_converter import ToolConverter


def simple_function(name: str, age: int) -> str:
    """Get person info."""
    return f"{name} is {age} years old"


def function_with_defaults(name: str, age: int = 30) -> str:
    """Get person info with default age."""
    return f"{name} is {age} years old"


def function_no_params() -> str:
    """Function with no parameters."""
    return "Hello"


class TestConvertFunctionToToolDefinition:
    """Test function to tool definition conversion."""

    def test_convert_simple_function(self):
        """Test converting simple function."""
        tool_def = ToolConverter.convert_function_to_tool_definition(simple_function)
        assert tool_def["type"] == "function"
        assert tool_def["function"]["name"] == "simple_function"
        assert "parameters" in tool_def["function"]

    def test_convert_function_parameters(self):
        """Test function parameters are converted."""
        tool_def = ToolConverter.convert_function_to_tool_definition(simple_function)
        params = tool_def["function"]["parameters"]
        assert "properties" in params
        assert "name" in params["properties"]
        assert "age" in params["properties"]

    def test_convert_function_required_fields(self):
        """Test required fields are identified."""
        tool_def = ToolConverter.convert_function_to_tool_definition(simple_function)
        params = tool_def["function"]["parameters"]
        assert "required" in params
        assert "name" in params["required"]
        assert "age" in params["required"]

    def test_convert_function_with_defaults(self):
        """Test function with default parameters."""
        tool_def = ToolConverter.convert_function_to_tool_definition(
            function_with_defaults
        )
        params = tool_def["function"]["parameters"]
        assert "name" in params["required"]
        assert "age" not in params["required"]

    def test_convert_function_no_params(self):
        """Test function with no parameters."""
        tool_def = ToolConverter.convert_function_to_tool_definition(function_no_params)
        params = tool_def["function"]["parameters"]
        assert len(params["properties"]) == 0
        assert len(params["required"]) == 0

    def test_convert_function_description(self):
        """Test function description is extracted."""
        tool_def = ToolConverter.convert_function_to_tool_definition(simple_function)
        assert tool_def["function"]["description"] == "Get person info."

    def test_convert_function_custom_description(self):
        """Test custom description override."""
        tool_def = ToolConverter.convert_function_to_tool_definition(
            simple_function,
            description="Custom description"
        )
        assert tool_def["function"]["description"] == "Custom description"


class TestGetParameterType:
    """Test parameter type detection."""

    def test_get_parameter_type_string(self):
        """Test string type detection."""
        import inspect
        sig = inspect.signature(simple_function)
        param = sig.parameters["name"]
        param_type = ToolConverter._get_parameter_type(param)
        assert param_type == "string"

    def test_get_parameter_type_integer(self):
        """Test integer type detection."""
        import inspect
        sig = inspect.signature(simple_function)
        param = sig.parameters["age"]
        param_type = ToolConverter._get_parameter_type(param)
        assert param_type == "integer"

    def test_get_parameter_type_no_annotation(self):
        """Test parameter with no annotation defaults to string."""
        import inspect

        def func_no_annotation(x):
            pass

        sig = inspect.signature(func_no_annotation)
        param = sig.parameters["x"]
        param_type = ToolConverter._get_parameter_type(param)
        assert param_type == "string"


class TestConvertFunctionsToTools:
    """Test converting multiple functions."""

    def test_convert_multiple_functions(self):
        """Test converting multiple functions."""
        functions = [simple_function, function_no_params]
        tools = ToolConverter.convert_functions_to_tools(functions)
        assert len(tools) == 2
        assert tools[0]["function"]["name"] == "simple_function"
        assert tools[1]["function"]["name"] == "function_no_params"

    def test_convert_functions_with_descriptions(self):
        """Test converting with custom descriptions."""
        functions = [simple_function]
        descriptions = {"simple_function": "Custom description"}
        tools = ToolConverter.convert_functions_to_tools(functions, descriptions)
        assert tools[0]["function"]["description"] == "Custom description"


class TestExtractToolCalls:
    """Test extracting tool calls from response."""

    def test_extract_tool_calls_success(self):
        """Test extracting tool calls from response."""
        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "function": {
                                    "name": "get_weather",
                                    "arguments": '{"location": "NYC"}'
                                }
                            }
                        ]
                    }
                }
            ]
        }
        tool_calls = ToolConverter.extract_tool_calls(response)
        assert len(tool_calls) == 1
        assert tool_calls[0]["id"] == "call_123"
        assert tool_calls[0]["name"] == "get_weather"
        assert tool_calls[0]["arguments"]["location"] == "NYC"

    def test_extract_tool_calls_multiple(self):
        """Test extracting multiple tool calls."""
        response = {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "tool1",
                                    "arguments": '{}'
                                }
                            },
                            {
                                "id": "call_2",
                                "function": {
                                    "name": "tool2",
                                    "arguments": '{}'
                                }
                            }
                        ]
                    }
                }
            ]
        }
        tool_calls = ToolConverter.extract_tool_calls(response)
        assert len(tool_calls) == 2

    def test_extract_tool_calls_no_calls(self):
        """Test extracting when no tool calls present."""
        response = {"choices": [{"message": {}}]}
        tool_calls = ToolConverter.extract_tool_calls(response)
        assert len(tool_calls) == 0

    def test_extract_tool_calls_empty_response(self):
        """Test extracting from empty response."""
        response = {}
        tool_calls = ToolConverter.extract_tool_calls(response)
        assert len(tool_calls) == 0


class TestBuildToolResultMessage:
    """Test building tool result messages."""

    def test_build_tool_result_message_string(self):
        """Test building tool result with string."""
        message = ToolConverter.build_tool_result_message(
            "call_123",
            "get_weather",
            "Sunny, 72°F"
        )
        assert message["role"] == "tool"
        assert message["tool_call_id"] == "call_123"
        assert message["content"] == "Sunny, 72°F"

    def test_build_tool_result_message_dict(self):
        """Test building tool result with dict."""
        result = {"temperature": 72, "condition": "sunny"}
        message = ToolConverter.build_tool_result_message(
            "call_123",
            "get_weather",
            result
        )
        assert message["role"] == "tool"
        content = json.loads(message["content"])
        assert content["temperature"] == 72
        assert content["condition"] == "sunny"

    def test_build_tool_result_message_number(self):
        """Test building tool result with number."""
        message = ToolConverter.build_tool_result_message(
            "call_123",
            "calculate",
            42
        )
        assert message["role"] == "tool"
        assert message["content"] == "42"

