#!/usr/bin/env python3
"""
OpenAPI to LLM Text Converter

Converts OpenAPI specifications to LLM-friendly text formats.
Creates both a full detailed version and a condensed llms.txt version.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class OpenAPIConverter:
    """Converts OpenAPI specifications to LLM-friendly text formats."""

    def __init__(self, openapi_spec: Dict[str, Any]):
        """
        Initialize converter with OpenAPI specification.

        Args:
            openapi_spec: Parsed OpenAPI specification as a dictionary
        """
        self.spec = openapi_spec
        self.info = self.spec.get("info", {})
        self.servers = self.spec.get("servers", [])
        self.paths = self.spec.get("paths", {})
        self.components = self.spec.get("components", {})
        self.tags = self.spec.get("tags", [])
        self.security = self.spec.get("security", [])

    @classmethod
    def from_file(cls, file_path: str) -> "OpenAPIConverter":
        """
        Create converter from an OpenAPI JSON file.

        Args:
            file_path: Path to OpenAPI JSON file

        Returns:
            OpenAPIConverter instance
        """
        with open(file_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
        return cls(spec)

    def generate_full_llm_txt(self) -> str:
        """Generate comprehensive LLM-friendly text documentation."""
        output = []

        # Header
        output.append(f"# {self.info.get('title', 'API Documentation')}")
        output.append("")
        output.append(f"Version: {self.info.get('version', 'N/A')}")
        output.append(f"OpenAPI Version: {self.spec.get('openapi', 'N/A')}")
        output.append("")

        # Description
        if description := self.info.get("description"):
            output.append("## Overview")
            output.append("")
            output.append(description)
            output.append("")

        # Contact Information
        if contact := self.info.get("contact"):
            output.append("## Contact Information")
            output.append("")
            for key, value in contact.items():
                if key.startswith("x-"):
                    key = key[2:].title()
                output.append(f"- {key.title()}: {value}")
            output.append("")

        # Servers
        if self.servers:
            output.append("## Servers")
            output.append("")
            for server in self.servers:
                url = server.get("url", "")
                desc = server.get("description", "")
                output.append(f"- {url}")
                if desc:
                    output.append(f"  {desc}")
            output.append("")

        # Security
        if self.security:
            output.append("## Security")
            output.append("")
            for sec_req in self.security:
                for sec_name in sec_req.keys():
                    output.append(f"- {sec_name}")
            output.append("")

        # Tags/Categories
        if self.tags:
            output.append("## API Categories")
            output.append("")
            for tag in self.tags:
                name = tag.get("name", "")
                desc = tag.get("description", "")
                output.append(f"### {name}")
                if desc:
                    output.append("")
                    output.append(desc)
                output.append("")

        # Endpoints
        output.append("## API Endpoints")
        output.append("")
        output.append("The following endpoints are available:")
        output.append("")

        for path, path_item in sorted(self.paths.items()):
            output.extend(self._format_path(path, path_item))

        # Schemas
        if schemas := self.components.get("schemas", {}):
            output.append("## Data Schemas")
            output.append("")
            output.append("The following data structures are used throughout the API:")
            output.append("")

            for schema_name, schema_def in sorted(schemas.items()):
                output.extend(self._format_schema(schema_name, schema_def))

        # Security Schemes
        if security_schemes := self.components.get("securitySchemes", {}):
            output.append("## Authentication Schemes")
            output.append("")
            for scheme_name, scheme_def in security_schemes.items():
                output.extend(self._format_security_scheme(scheme_name, scheme_def))

        return "\n".join(output)

    def generate_condensed_llms_txt(self) -> str:
        """Generate condensed llms.txt format documentation."""
        output = []

        # Header
        output.append(f"# {self.info.get('title', 'API')}")
        output.append("")

        # Summary blockquote
        summary = self._extract_summary()
        if summary:
            output.append(f"> {summary}")
            output.append("")

        # Core capabilities
        output.append("## Core Capabilities")
        output.append("")

        # Extract key capabilities from tags
        for tag in self.tags[:5]:  # Limit to top 5 categories
            name = tag.get("name", "")
            desc = tag.get("description", "").split("\n")[0]  # First line only
            if desc:
                output.append(f"- **{name}**: {desc[:200]}...")
        output.append("")

        # Authentication
        output.append("## Authentication")
        output.append("")
        output.append("- OAuth 2.0 Client Credentials (Bearer Token)")
        output.append(
            "- Create M2M user → Obtain token → Include in Authorization header"
        )
        output.append("")

        # Endpoint summary
        output.append("## API Endpoints")
        output.append("")

        # Group by tag
        endpoints_by_tag = {}
        for path, path_item in self.paths.items():
            for method in ["get", "post", "put", "patch", "delete"]:
                if operation := path_item.get(method):
                    tags = operation.get("tags", ["Other"])
                    tag = tags[0] if tags else "Other"

                    if tag not in endpoints_by_tag:
                        endpoints_by_tag[tag] = []

                    summary = operation.get("summary", "")
                    endpoints_by_tag[tag].append(f"{method.upper()} {path}: {summary}")

        # Output top endpoints per category
        for tag, endpoints in sorted(endpoints_by_tag.items()):
            output.append(f"### {tag}")
            output.append("")
            for endpoint in endpoints[:10]:  # Limit to 10 per category
                output.append(f"- `{endpoint}`")
            if len(endpoints) > 10:
                output.append(f"- ... and {len(endpoints) - 10} more")
            output.append("")

        # Key schemas
        if schemas := self.components.get("schemas", {}):
            output.append("## Key Data Schemas")
            output.append("")

            # List important schemas
            important_schemas = [
                name
                for name in schemas.keys()
                if any(
                    keyword in name.lower()
                    for keyword in ["entity", "response", "request", "account", "user"]
                )
            ][
                :15
            ]  # Limit to 15

            for schema_name in sorted(important_schemas):
                schema_def = schemas[schema_name]
                desc = schema_def.get("description", "").split("\n")[0]
                if desc:
                    output.append(f"- `{schema_name}`: {desc[:150]}")
                else:
                    output.append(f"- `{schema_name}`")
            output.append("")

        # Contact
        if contact := self.info.get("contact"):
            output.append("## Resources")
            output.append("")
            if url := contact.get("url"):
                output.append(f"- [Official Website]({url})")
            if email := contact.get("email"):
                output.append(f"- Support: {email}")
            if discord := contact.get("x-discord"):
                output.append(f"- [Discord Community]({discord})")
            output.append("")

        return "\n".join(output)

    def _format_path(self, path: str, path_item: Dict[str, Any]) -> List[str]:
        """Format an API path and its operations."""
        output = []

        for method in ["get", "post", "put", "patch", "delete", "options", "head"]:
            if operation := path_item.get(method):
                output.append(f"### {method.upper()} {path}")
                output.append("")

                # Summary
                if summary := operation.get("summary"):
                    output.append(f"**Summary:** {summary}")
                    output.append("")

                # Description
                if description := operation.get("description"):
                    output.append(description)
                    output.append("")

                # Operation ID
                if op_id := operation.get("operationId"):
                    output.append(f"**Operation ID:** `{op_id}`")
                    output.append("")

                # Tags
                if tags := operation.get("tags"):
                    output.append(f"**Tags:** {', '.join(tags)}")
                    output.append("")

                # Parameters
                if parameters := operation.get("parameters"):
                    output.append("**Parameters:**")
                    output.append("")
                    for param in parameters:
                        param_name = param.get("name", "unnamed")
                        param_in = param.get("in", "")
                        required = " (required)" if param.get("required") else ""
                        param_desc = param.get("description", "")
                        param_type = self._get_parameter_type(param)

                        output.append(
                            f"- `{param_name}` ({param_in}){required}: {param_type}"
                        )
                        if param_desc:
                            output.append(f"  {param_desc}")
                    output.append("")

                # Request Body
                if request_body := operation.get("requestBody"):
                    output.append("**Request Body:**")
                    output.append("")
                    if desc := request_body.get("description"):
                        output.append(desc)
                        output.append("")

                    required = " (required)" if request_body.get("required") else ""
                    output.append(f"Content{required}:")

                    for content_type, content in request_body.get(
                        "content", {}
                    ).items():
                        output.append(f"- `{content_type}`")
                        if schema := content.get("schema"):
                            schema_ref = self._get_schema_reference(schema)
                            output.append(f"  Schema: {schema_ref}")
                    output.append("")

                # Responses
                if responses := operation.get("responses"):
                    output.append("**Responses:**")
                    output.append("")
                    for status_code, response in sorted(responses.items()):
                        resp_desc = response.get("description", "")
                        output.append(f"- **{status_code}**: {resp_desc}")

                        if content := response.get("content"):
                            for content_type, content_schema in content.items():
                                if schema := content_schema.get("schema"):
                                    schema_ref = self._get_schema_reference(schema)
                                    output.append(f"  - `{content_type}`: {schema_ref}")
                    output.append("")

                output.append("---")
                output.append("")

        return output

    def _get_parameter_type(self, param: Dict[str, Any]) -> str:
        """Extract parameter type information."""
        if schema := param.get("schema"):
            return self._get_schema_type(schema)
        return "any"

    def _get_schema_type(self, schema: Dict[str, Any]) -> str:
        """Extract schema type information."""
        if "$ref" in schema:
            return schema["$ref"].split("/")[-1]

        schema_type = schema.get("type", "any")

        if schema_type == "array":
            items_type = self._get_schema_type(schema.get("items", {}))
            return f"array<{items_type}>"

        if schema_type == "object":
            return "object"

        return schema_type

    def _get_schema_reference(self, schema: Dict[str, Any]) -> str:
        """Get schema reference or type description."""
        if "$ref" in schema:
            return f"`{schema['$ref'].split('/')[-1]}`"

        schema_type = self._get_schema_type(schema)
        return f"`{schema_type}`"

    def _format_schema(self, name: str, schema_def: Dict[str, Any]) -> List[str]:
        """Format a schema definition."""
        output = []

        output.append(f"### {name}")
        output.append("")

        # Description
        if description := schema_def.get("description"):
            output.append(description)
            output.append("")

        # Type
        schema_type = schema_def.get("type", "object")
        output.append(f"**Type:** `{schema_type}`")
        output.append("")

        # Properties
        if properties := schema_def.get("properties"):
            required_fields = set(schema_def.get("required", []))
            output.append("**Properties:**")
            output.append("")

            for prop_name, prop_def in sorted(properties.items()):
                required = " (required)" if prop_name in required_fields else ""
                prop_type = self._get_schema_type(prop_def)
                prop_desc = prop_def.get("description", "")

                output.append(f"- `{prop_name}`: {prop_type}{required}")
                if prop_desc:
                    output.append(f"  {prop_desc}")

                # Enum values
                if enum_values := prop_def.get("enum"):
                    output.append(
                        f"  Allowed values: {', '.join(map(str, enum_values))}"
                    )

            output.append("")

        # Enum
        if enum_values := schema_def.get("enum"):
            output.append("**Allowed Values:**")
            output.append("")
            for value in enum_values:
                output.append(f"- `{value}`")
            output.append("")

        # All Of, Any Of, One Of
        for combo_type in ["allOf", "anyOf", "oneOf"]:
            if combo_schemas := schema_def.get(combo_type):
                output.append(f"**{combo_type.title()}:**")
                output.append("")
                for sub_schema in combo_schemas:
                    schema_ref = self._get_schema_reference(sub_schema)
                    output.append(f"- {schema_ref}")
                output.append("")

        output.append("---")
        output.append("")

        return output

    def _format_security_scheme(self, name: str, scheme: Dict[str, Any]) -> List[str]:
        """Format a security scheme definition."""
        output = []

        output.append(f"### {name}")
        output.append("")

        scheme_type = scheme.get("type", "")
        output.append(f"**Type:** {scheme_type}")
        output.append("")

        if description := scheme.get("description"):
            output.append(description)
            output.append("")

        # HTTP specific
        if scheme_type == "http":
            if http_scheme := scheme.get("scheme"):
                output.append(f"**Scheme:** {http_scheme}")
            if bearer_format := scheme.get("bearerFormat"):
                output.append(f"**Bearer Format:** {bearer_format}")
            output.append("")

        # OAuth2 specific
        if scheme_type == "oauth2":
            if flows := scheme.get("flows"):
                output.append("**Flows:**")
                output.append("")
                for flow_type, flow_def in flows.items():
                    output.append(f"- {flow_type}")
                    if token_url := flow_def.get("tokenUrl"):
                        output.append(f"  Token URL: {token_url}")
                    if auth_url := flow_def.get("authorizationUrl"):
                        output.append(f"  Authorization URL: {auth_url}")
                output.append("")

        output.append("---")
        output.append("")

        return output

    def _extract_summary(self) -> str:
        """Extract a concise summary from the description."""
        description = self.info.get("description", "")
        if not description:
            return ""

        # Get first meaningful sentence
        lines = description.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 20:
                # Truncate at sentence or 200 chars
                if "." in line:
                    return line.split(".")[0] + "."
                return line[:200] + "..." if len(line) > 200 else line

        return "API documentation"
