#!/usr/bin/env python3
"""
OpenAPI Documentation Generator

Generates OpenAPI 3.0 specification from Pydantic models and route definitions.
Supports automatic schema generation from Pydantic models.

Usage:
    python scripts/generate_openapi_docs.py

Outputs:
    docs/api/openapi.json - OpenAPI specification
    docs/api/openapi.yaml - YAML version (optional)
"""

import json
import yaml
from typing import Dict, Any, List, Type, Optional
from pydantic import BaseModel
from datetime import datetime

# Import all Pydantic models
from application.routes.models.token_models import (
    GenerateTestTokenRequest,
    TokenResponse,
)
from application.routes.models.logs_models import (
    LogsAPIKeyRequest,
    LogsAPIKeyResponse,
    LogSearchRequest,
)
from application.routes.models.metrics_models import (
    GrafanaTokenRequest,
    GrafanaTokenResponse,
    PrometheusQueryRequest,
)


class OpenAPIGenerator:
    """Generate OpenAPI specification from Pydantic models and routes."""

    def __init__(self, title: str, version: str, description: str):
        self.title = title
        self.version = version
        self.description = description
        self.spec: Dict[str, Any] = {}

    def generate(self) -> Dict[str, Any]:
        """Generate complete OpenAPI specification."""
        self.spec = {
            "openapi": "3.0.3",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
                "contact": {
                    "name": "API Support",
                    "email": "support@example.com"
                }
            },
            "servers": [
                {
                    "url": "http://localhost:5000/api/v1",
                    "description": "Development server"
                },
                {
                    "url": "https://api.example.com/api/v1",
                    "description": "Production server"
                }
            ],
            "tags": [
                {"name": "tokens", "description": "Token generation and management"},
                {"name": "logs", "description": "Log search and API key management"},
                {"name": "metrics", "description": "Metrics and monitoring"},
                {"name": "chat", "description": "Chat conversation management"},
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                        "description": "JWT token obtained from /get_guest_token or /generate_test_token"
                    }
                },
                "responses": {
                    "ValidationError": {
                        "description": "Validation error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string", "example": "Validation failed"},
                                        "details": {
                                            "type": "object",
                                            "properties": {
                                                "errors": {
                                                    "type": "array",
                                                    "items": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "Unauthorized": {
                        "description": "Unauthorized - invalid or missing token",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string", "example": "Token expired"}
                                    }
                                }
                            }
                        }
                    },
                    "Forbidden": {
                        "description": "Forbidden - insufficient permissions",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string", "example": "Permission denied"}
                                    }
                                }
                            }
                        }
                    },
                    "InternalError": {
                        "description": "Internal server error",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "error": {"type": "string", "example": "Internal server error"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        # Generate schemas from Pydantic models
        self._add_schemas()

        # Define paths (routes)
        self._add_token_paths()
        self._add_logs_paths()
        self._add_metrics_paths()

        return self.spec

    def _add_schemas(self):
        """Add Pydantic model schemas to components."""
        models: List[Type[BaseModel]] = [
            GenerateTestTokenRequest,
            TokenResponse,
            LogsAPIKeyRequest,
            LogsAPIKeyResponse,
            LogSearchRequest,
            GrafanaTokenRequest,
            GrafanaTokenResponse,
            PrometheusQueryRequest,
        ]

        for model in models:
            schema = model.model_json_schema()
            # Remove internal fields
            schema.pop("title", None)
            schema.pop("$defs", None)
            self.spec["components"]["schemas"][model.__name__] = schema

    def _add_token_paths(self):
        """Add token-related paths."""
        self.spec["paths"]["/get_guest_token"] = {
            "get": {
                "tags": ["tokens"],
                "summary": "Generate guest token",
                "description": "Generate a temporary guest token for anonymous access",
                "operationId": "getGuestToken",
                "responses": {
                    "200": {
                        "description": "Guest token generated successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/TokenResponse"}
                            }
                        }
                    },
                    "500": {"$ref": "#/components/responses/InternalError"}
                }
            }
        }

        self.spec["paths"]["/generate_test_token"] = {
            "post": {
                "tags": ["tokens"],
                "summary": "Generate test token",
                "description": "Generate a test token for development/testing purposes",
                "operationId": "generateTestToken",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/GenerateTestTokenRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Test token generated successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/TokenResponse"}
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/ValidationError"},
                    "500": {"$ref": "#/components/responses/InternalError"}
                }
            }
        }

    def _add_logs_paths(self):
        """Add logs-related paths."""
        self.spec["paths"]["/logs/generate_api_key"] = {
            "post": {
                "tags": ["logs"],
                "summary": "Generate ELK API key",
                "description": "Generate an API key for Elasticsearch/Kibana access",
                "operationId": "generateLogsAPIKey",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/LogsAPIKeyRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "API key generated successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/LogsAPIKeyResponse"}
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/ValidationError"},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "500": {"$ref": "#/components/responses/InternalError"}
                }
            }
        }

        self.spec["paths"]["/logs/search"] = {
            "post": {
                "tags": ["logs"],
                "summary": "Search logs",
                "description": "Search Elasticsearch logs with optional filters",
                "operationId": "searchLogs",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/LogSearchRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Search results",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "hits": {
                                            "type": "array",
                                            "items": {"type": "object"}
                                        },
                                        "total": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/ValidationError"},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "500": {"$ref": "#/components/responses/InternalError"}
                }
            }
        }

    def _add_metrics_paths(self):
        """Add metrics-related paths."""
        self.spec["paths"]["/metrics/generate_grafana_token"] = {
            "post": {
                "tags": ["metrics"],
                "summary": "Generate Grafana token",
                "description": "Generate a service account token for Grafana access",
                "operationId": "generateGrafanaToken",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/GrafanaTokenRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Grafana token generated successfully",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/GrafanaTokenResponse"}
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/ValidationError"},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "500": {"$ref": "#/components/responses/InternalError"}
                }
            }
        }

        self.spec["paths"]["/metrics/query_prometheus"] = {
            "post": {
                "tags": ["metrics"],
                "summary": "Query Prometheus",
                "description": "Execute a Prometheus query",
                "operationId": "queryPrometheus",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/PrometheusQueryRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Query results",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "data": {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "400": {"$ref": "#/components/responses/ValidationError"},
                    "401": {"$ref": "#/components/responses/Unauthorized"},
                    "500": {"$ref": "#/components/responses/InternalError"}
                }
            }
        }

    def save_json(self, filepath: str):
        """Save specification as JSON."""
        with open(filepath, 'w') as f:
            json.dump(self.spec, f, indent=2)
        print(f"✅ OpenAPI JSON saved to: {filepath}")

    def save_yaml(self, filepath: str):
        """Save specification as YAML."""
        with open(filepath, 'w') as f:
            yaml.dump(self.spec, f, default_flow_style=False, sort_keys=False)
        print(f"✅ OpenAPI YAML saved to: {filepath}")


def main():
    """Generate OpenAPI documentation."""
    print("🚀 Generating OpenAPI documentation...")

    generator = OpenAPIGenerator(
        title="Cyoda AI Studio API",
        version="1.0.0",
        description=(
            "REST API for Cyoda AI Studio providing endpoints for:\n"
            "- Token generation and authentication\n"
            "- Log search and management (Elasticsearch/Kibana)\n"
            "- Metrics and monitoring (Prometheus/Grafana)\n"
            "- Chat conversation management\n"
            "\n"
            "All endpoints (except token generation) require Bearer authentication."
        )
    )

    spec = generator.generate()

    # Create output directory
    import os
    os.makedirs("docs/api", exist_ok=True)

    # Save in both formats
    generator.save_json("docs/api/openapi.json")
    generator.save_yaml("docs/api/openapi.yaml")

    print("\n📚 Documentation generated successfully!")
    print("\nView documentation:")
    print("  - JSON: docs/api/openapi.json")
    print("  - YAML: docs/api/openapi.yaml")
    print("\nTo view interactively, use:")
    print("  - Swagger UI: https://editor.swagger.io/ (paste YAML)")
    print("  - Redoc: npx @redocly/cli preview-docs docs/api/openapi.yaml")


if __name__ == "__main__":
    main()
