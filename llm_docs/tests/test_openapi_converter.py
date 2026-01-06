"""Tests for OpenAPI converter."""

import pytest
from llm_docs.converters.openapi_converter import OpenAPIConverter


@pytest.fixture
def minimal_openapi_spec():
    """Minimal OpenAPI specification for testing."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0",
            "description": "A test API for unit testing.",
            "contact": {
                "name": "Test Team",
                "email": "test@example.com"
            }
        },
        "servers": [
            {"url": "https://api.example.com", "description": "Production server"}
        ],
        "paths": {
            "/test": {
                "get": {
                    "summary": "Get test data",
                    "operationId": "getTest",
                    "tags": ["Test"],
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/TestResponse"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "TestResponse": {
                    "type": "object",
                    "description": "Test response schema",
                    "properties": {
                        "id": {"type": "string", "description": "Unique identifier"},
                        "name": {"type": "string", "description": "Name field"}
                    },
                    "required": ["id"]
                }
            },
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        },
        "tags": [
            {"name": "Test", "description": "Test endpoints"}
        ]
    }


class TestOpenAPIConverter:
    """Test suite for OpenAPIConverter."""

    def test_initialization(self, minimal_openapi_spec):
        """Test converter initialization."""
        converter = OpenAPIConverter(minimal_openapi_spec)

        assert converter.spec == minimal_openapi_spec
        assert converter.info["title"] == "Test API"
        assert len(converter.paths) == 1
        assert len(converter.components["schemas"]) == 1

    def test_from_file(self, tmp_path, minimal_openapi_spec):
        """Test loading from file."""
        import json

        # Write spec to temp file
        spec_file = tmp_path / "openapi.json"
        with open(spec_file, 'w') as f:
            json.dump(minimal_openapi_spec, f)

        # Load from file
        converter = OpenAPIConverter.from_file(str(spec_file))

        assert converter.info["title"] == "Test API"

    def test_generate_full_llm_txt(self, minimal_openapi_spec):
        """Test full LLM text generation."""
        converter = OpenAPIConverter(minimal_openapi_spec)
        full_text = converter.generate_full_llm_txt()

        # Verify key sections are present
        assert "# Test API" in full_text
        assert "Version: 1.0.0" in full_text
        assert "## Overview" in full_text
        assert "## Contact Information" in full_text
        assert "## Servers" in full_text
        assert "## API Categories" in full_text
        assert "## API Endpoints" in full_text
        assert "### GET /test" in full_text
        assert "## Data Schemas" in full_text
        assert "### TestResponse" in full_text
        assert "## Authentication Schemes" in full_text

    def test_generate_condensed_llms_txt(self, minimal_openapi_spec):
        """Test condensed llms.txt generation."""
        converter = OpenAPIConverter(minimal_openapi_spec)
        condensed_text = converter.generate_condensed_llms_txt()

        # Verify key sections are present
        assert "# Test API" in condensed_text
        assert "## Core Capabilities" in condensed_text
        assert "## Authentication" in condensed_text
        assert "## API Endpoints" in condensed_text
        assert "## Key Data Schemas" in condensed_text
        assert "## Resources" in condensed_text
        assert "GET /test" in condensed_text

    def test_schema_type_extraction(self, minimal_openapi_spec):
        """Test schema type extraction."""
        converter = OpenAPIConverter(minimal_openapi_spec)

        # Test simple type
        assert converter._get_schema_type({"type": "string"}) == "string"

        # Test array type
        assert converter._get_schema_type({
            "type": "array",
            "items": {"type": "string"}
        }) == "array<string>"

        # Test reference
        assert converter._get_schema_type({
            "$ref": "#/components/schemas/TestResponse"
        }) == "TestResponse"

    def test_extract_summary(self, minimal_openapi_spec):
        """Test summary extraction."""
        converter = OpenAPIConverter(minimal_openapi_spec)
        summary = converter._extract_summary()

        assert "test api" in summary.lower()
        assert len(summary) > 0

    def test_format_schema(self, minimal_openapi_spec):
        """Test schema formatting."""
        converter = OpenAPIConverter(minimal_openapi_spec)
        schema_def = minimal_openapi_spec["components"]["schemas"]["TestResponse"]

        formatted = converter._format_schema("TestResponse", schema_def)
        formatted_text = "\n".join(formatted)

        assert "### TestResponse" in formatted_text
        assert "Test response schema" in formatted_text
        assert "`id`: string (required)" in formatted_text
        assert "`name`: string" in formatted_text

    def test_format_path(self, minimal_openapi_spec):
        """Test path formatting."""
        converter = OpenAPIConverter(minimal_openapi_spec)
        path_item = minimal_openapi_spec["paths"]["/test"]

        formatted = converter._format_path("/test", path_item)
        formatted_text = "\n".join(formatted)

        assert "### GET /test" in formatted_text
        assert "**Summary:** Get test data" in formatted_text
        assert "**Operation ID:** `getTest`" in formatted_text
        assert "**Tags:** Test" in formatted_text
        assert "**200**: Success" in formatted_text
