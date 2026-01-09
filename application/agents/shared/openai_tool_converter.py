"""
OpenAI Tool Converter

Converts function definitions to OpenAI function calling format.
"""

import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolConverter:
    """Convert functions to OpenAI tool definitions."""

    @staticmethod
    def convert_function_to_tool_definition(
        func: Callable,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert a function to OpenAI tool definition.

        Args:
            func: Function to convert
            description: Optional description override

        Returns:
            Tool definition dictionary for OpenAI API

        Raises:
            ValueError: If function signature is invalid
        """
        try:
            logger.debug(f"Converting function to tool: {func.__name__}")

            # Get function signature
            sig = inspect.signature(func)
            docstring = inspect.getdoc(func) or ""

            # Build parameters schema
            parameters = ToolConverter._build_parameters_schema(sig)

            # Build tool definition
            tool_def = {
                "type": "function",
                "function": {
                    "name": func.__name__,
                    "description": description or docstring.split("\n")[0],
                    "parameters": parameters,
                },
            }

            logger.debug(f"Tool definition created: {func.__name__}")
            return tool_def

        except Exception as e:
            logger.error(f"Failed to convert function to tool: {e}")
            raise

    @staticmethod
    def _build_parameters_schema(sig: inspect.Signature) -> Dict[str, Any]:
        """
        Build JSON schema for function parameters.

        Args:
            sig: Function signature

        Returns:
            JSON schema for parameters

        Raises:
            ValueError: If parameter types are invalid
        """
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            # Get parameter type
            param_type = ToolConverter._get_parameter_type(param)

            # Build property schema
            properties[param_name] = {
                "type": param_type,
                "description": (
                    param.annotation.__doc__
                    if hasattr(param.annotation, "__doc__")
                    else ""
                ),
            }

            # Check if required
            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    @staticmethod
    def _get_parameter_type(param: inspect.Parameter) -> str:
        """
        Get JSON schema type for parameter.

        Args:
            param: Function parameter

        Returns:
            JSON schema type string

        Raises:
            ValueError: If type is not supported
        """
        annotation = param.annotation

        if annotation == inspect.Parameter.empty:
            return "string"

        # Handle basic types
        if annotation == str:
            return "string"
        elif annotation == int:
            return "integer"
        elif annotation == float:
            return "number"
        elif annotation == bool:
            return "boolean"
        elif annotation == list or annotation == List:
            return "array"
        elif annotation == dict or annotation == Dict:
            return "object"

        # Handle Optional types
        if hasattr(annotation, "__origin__"):
            if annotation.__origin__ is list:
                return "array"
            elif annotation.__origin__ is dict:
                return "object"

        # Default to string
        logger.warning(f"Unknown parameter type {annotation}, defaulting to string")
        return "string"

    @staticmethod
    def convert_functions_to_tools(
        functions: List[Callable],
        descriptions: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convert multiple functions to OpenAI tool definitions.

        Args:
            functions: List of functions to convert
            descriptions: Optional dict of function name -> description

        Returns:
            List of tool definitions

        Raises:
            ValueError: If any function is invalid
        """
        descriptions = descriptions or {}
        tools = []

        for func in functions:
            description = descriptions.get(func.__name__)
            tool_def = ToolConverter.convert_function_to_tool_definition(
                func, description
            )
            tools.append(tool_def)

        logger.debug(f"Converted {len(tools)} functions to tools")
        return tools

    @staticmethod
    def extract_tool_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract tool calls from OpenAI response.

        Args:
            response: OpenAI API response

        Returns:
            List of tool calls with name and arguments

        Raises:
            ValueError: If response format is invalid
        """
        tool_calls = []

        try:
            if "choices" not in response:
                return tool_calls

            for choice in response["choices"]:
                if "message" not in choice:
                    continue

                message = choice["message"]
                if "tool_calls" not in message:
                    continue

                for tool_call in message["tool_calls"]:
                    tool_calls.append(
                        {
                            "id": tool_call.get("id"),
                            "name": tool_call.get("function", {}).get("name"),
                            "arguments": json.loads(
                                tool_call.get("function", {}).get("arguments", "{}")
                            ),
                        }
                    )

            logger.debug(f"Extracted {len(tool_calls)} tool calls from response")
            return tool_calls

        except Exception as e:
            logger.error(f"Failed to extract tool calls: {e}")
            raise

    @staticmethod
    def build_tool_result_message(
        tool_call_id: str,
        tool_name: str,
        result: Any,
    ) -> Dict[str, Any]:
        """
        Build tool result message for OpenAI API.

        Args:
            tool_call_id: ID of the tool call
            tool_name: Name of the tool
            result: Result from tool execution

        Returns:
            Tool result message

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            logger.debug(f"Building tool result message: {tool_name}")

            # Convert result to string if needed
            if isinstance(result, dict):
                result_str = json.dumps(result)
            elif isinstance(result, str):
                result_str = result
            else:
                result_str = str(result)

            return {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": result_str,
            }

        except Exception as e:
            logger.error(f"Failed to build tool result message: {e}")
            raise
