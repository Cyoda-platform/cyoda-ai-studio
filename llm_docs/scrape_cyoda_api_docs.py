#!/usr/bin/env python3
"""
Script to scrape all API pages from Cyoda API documentation.
Fetches the OpenAPI spec and extracts all endpoints and documentation.
Outputs full API documentation map to the outputs directory.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

import requests


def fetch_openapi_spec(url: str) -> Dict[str, Any]:
    """Fetch the OpenAPI specification."""
    print(f"Fetching OpenAPI spec from {url}")
    response = requests.get(url)
    response.raise_for_status()
    return response.json()


def format_endpoint_doc(path: str, method: str, operation: Dict[str, Any]) -> str:
    """Format an API endpoint into readable documentation."""
    doc_lines = []

    doc_lines.append("=" * 80)
    doc_lines.append(f"Endpoint: {method.upper()} {path}")
    doc_lines.append("=" * 80)
    doc_lines.append("")

    # Summary
    if "summary" in operation:
        doc_lines.append(f"Summary: {operation['summary']}")
        doc_lines.append("")

    # Description
    if "description" in operation:
        doc_lines.append(f"Description: {operation['description']}")
        doc_lines.append("")

    # Tags
    if "tags" in operation:
        doc_lines.append(f"Tags: {', '.join(operation['tags'])}")
        doc_lines.append("")

    # Operation ID
    if "operationId" in operation:
        doc_lines.append(f"Operation ID: {operation['operationId']}")
        doc_lines.append("")

    # Parameters
    if "parameters" in operation and operation["parameters"]:
        doc_lines.append("Parameters:")
        for param in operation["parameters"]:
            param_name = param.get("name", "")
            param_in = param.get("in", "")
            param_required = (
                " (required)" if param.get("required", False) else " (optional)"
            )
            param_desc = param.get("description", "")
            param_type = (
                param.get("schema", {}).get("type", "")
                if "schema" in param
                else param.get("type", "")
            )

            doc_lines.append(f"  - {param_name} ({param_in}){param_required}")
            if param_type:
                doc_lines.append(f"    Type: {param_type}")
            if param_desc:
                doc_lines.append(f"    Description: {param_desc}")
            doc_lines.append("")

    # Request Body
    if "requestBody" in operation:
        doc_lines.append("Request Body:")
        request_body = operation["requestBody"]
        if "description" in request_body:
            doc_lines.append(f"  Description: {request_body['description']}")
        if "required" in request_body:
            doc_lines.append(f"  Required: {request_body['required']}")

        if "content" in request_body:
            for content_type, content_schema in request_body["content"].items():
                doc_lines.append(f"  Content-Type: {content_type}")
                if "schema" in content_schema:
                    doc_lines.append(
                        f"  Schema: {json.dumps(content_schema['schema'], indent=4)}"
                    )
        doc_lines.append("")

    # Responses
    if "responses" in operation:
        doc_lines.append("Responses:")
        for status_code, response in operation["responses"].items():
            doc_lines.append(f"  {status_code}:")
            if "description" in response:
                doc_lines.append(f"    Description: {response['description']}")
            if "content" in response:
                for content_type, content_schema in response["content"].items():
                    doc_lines.append(f"    Content-Type: {content_type}")
                    if "schema" in content_schema:
                        schema_str = json.dumps(content_schema["schema"], indent=6)
                        doc_lines.append(f"    Schema: {schema_str}")
            doc_lines.append("")

    # Security
    if "security" in operation:
        doc_lines.append("Security:")
        for security_req in operation["security"]:
            doc_lines.append(f"  {json.dumps(security_req, indent=4)}")
        doc_lines.append("")

    doc_lines.append("")
    return "\n".join(doc_lines)


def scrape_cyoda_api_docs():
    """Scrape all API documentation from OpenAPI spec."""

    openapi_url = "https://docs.cyoda.net/openapi/openapi.json"
    base_url = "https://docs.cyoda.net/api-reference/scalar/"
    output_dir = Path("llm_docs/outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting to scrape Cyoda API documentation")
    print(f"OpenAPI spec URL: {openapi_url}")
    print(f"Output directory: {output_dir}")
    print("")

    # Fetch OpenAPI spec
    try:
        spec = fetch_openapi_spec(openapi_url)
    except Exception as e:
        print(f"Error fetching OpenAPI spec: {e}")
        return

    print(f"OpenAPI version: {spec.get('openapi', 'unknown')}")
    print(f"API title: {spec.get('info', {}).get('title', 'unknown')}")
    print(f"API version: {spec.get('info', {}).get('version', 'unknown')}")
    print("")

    # Save the full OpenAPI spec
    spec_file = output_dir / "openapi_spec.json"
    with open(spec_file, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)
    print(f"Saved full OpenAPI spec to {spec_file}")
    print("")

    # Extract all endpoints
    paths = spec.get("paths", {})
    print(f"Found {len(paths)} API paths")
    print("")

    # Process each endpoint
    all_endpoints = []
    endpoint_docs = []

    for path, path_item in paths.items():
        for method in ["get", "post", "put", "patch", "delete", "options", "head"]:
            if method in path_item:
                operation = path_item[method]

                # Extract endpoint info
                endpoint_info = {
                    "path": path,
                    "method": method.upper(),
                    "summary": operation.get("summary", ""),
                    "description": operation.get("description", ""),
                    "operationId": operation.get("operationId", ""),
                    "tags": operation.get("tags", []),
                }

                all_endpoints.append(endpoint_info)

                # Format documentation
                doc_text = format_endpoint_doc(path, method, operation)
                endpoint_docs.append(doc_text)

                print(f"[{len(all_endpoints)}] {method.upper()} {path}")
                if operation.get("summary"):
                    print(f"    {operation['summary']}")

    print("")
    print(f"Processed {len(all_endpoints)} endpoints")
    print("")

    # Save all endpoints in one file
    all_endpoints_file = output_dir / "all_api_endpoints.txt"
    with open(all_endpoints_file, "w", encoding="utf-8") as f:
        f.write(f"CYODA API DOCUMENTATION\n")
        f.write(f"{'=' * 80}\n\n")
        f.write(f"Total Endpoints: {len(all_endpoints)}\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("\n\n".join(endpoint_docs))

    print(f"Saved all endpoints documentation to {all_endpoints_file}")

    # Save endpoints map
    map_data = {
        "api_title": spec.get("info", {}).get("title", ""),
        "api_version": spec.get("info", {}).get("version", ""),
        "openapi_version": spec.get("openapi", ""),
        "base_url": base_url,
        "openapi_spec_url": openapi_url,
        "scraped_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_endpoints": len(all_endpoints),
        "endpoints": all_endpoints,
        "servers": spec.get("servers", []),
        "tags": spec.get("tags", []),
    }

    map_file = output_dir / "api_docs_map.json"
    with open(map_file, "w", encoding="utf-8") as f:
        json.dump(map_data, f, indent=2, ensure_ascii=False)

    print(f"Saved API map to {map_file}")

    # Group by tags
    tags_map = {}
    for endpoint in all_endpoints:
        for tag in endpoint.get("tags", ["Untagged"]):
            if tag not in tags_map:
                tags_map[tag] = []
            tags_map[tag].append(endpoint)

    # Save grouped by tags
    tags_file = output_dir / "api_endpoints_by_tag.txt"
    with open(tags_file, "w", encoding="utf-8") as f:
        f.write(f"CYODA API ENDPOINTS GROUPED BY TAG\n")
        f.write(f"{'=' * 80}\n\n")

        for tag, endpoints in sorted(tags_map.items()):
            f.write(f"\n## {tag}\n")
            f.write(f"{'-' * 80}\n")
            for endpoint in endpoints:
                f.write(f"{endpoint['method']:7} {endpoint['path']}\n")
                if endpoint["summary"]:
                    f.write(f"        {endpoint['summary']}\n")
            f.write("\n")

    print(f"Saved endpoints grouped by tag to {tags_file}")

    # Create sitemap for LLMs
    sitemap_file = output_dir / "cyoda-api-sitemap-llms.txt"
    with open(sitemap_file, "w", encoding="utf-8") as f:
        f.write(f"# Cyoda API Reference\n\n")
        f.write(f"Base URL: `{base_url}`\n")
        f.write(f"OpenAPI Spec: `{openapi_url}`\n\n")

        for tag, endpoints in sorted(tags_map.items()):
            f.write(f"## {tag}\n\n")
            for endpoint in endpoints:
                # Create URL-safe tag and path
                tag_safe = tag.replace(", ", "-").replace(" ", "-")
                path_safe = endpoint["path"].replace("{", "%7B").replace("}", "%7D")
                method = endpoint["method"]

                # Build the URL
                url = f"{base_url}#tag/{tag_safe}/{method}{path_safe}"

                # Write the line
                f.write(f"- [{method} {endpoint['path']}]({url})")
                if endpoint["summary"]:
                    f.write(f" - {endpoint['summary']}")
                f.write("\n")
            f.write("\n")

    print(f"Saved API sitemap for LLMs to {sitemap_file}")

    # Create descriptions document for LLMs
    descriptions_file = output_dir / "cyoda-api-descriptions-llms.txt"
    with open(descriptions_file, "w", encoding="utf-8") as f:
        f.write(f"# Cyoda API Reference - Sections\n\n")
        f.write(f"Base URL: `{base_url}`\n")
        f.write(f"OpenAPI Spec: `{openapi_url}`\n\n")

        f.write("## API Sections\n\n")

        # Create a map of tag descriptions from spec
        tags_info = spec.get("tags", [])
        tag_descriptions = {
            tag.get("name", ""): tag.get("description", "") for tag in tags_info
        }

        # Iterate through all tags found in endpoints
        for tag in sorted(tags_map.keys()):
            # Create URL-safe tag identifier (lowercase, spaces/commas to hyphens)
            tag_url_safe = tag.lower().replace(", ", "-").replace(" ", "-")

            # Build the description URL
            desc_url = f"{base_url}#description/{tag_url_safe}"

            # Write the section
            f.write(f"### [{tag}]({desc_url})\n\n")

            # Add description if available from OpenAPI spec
            if tag in tag_descriptions and tag_descriptions[tag]:
                f.write(f"{tag_descriptions[tag].strip()}\n\n")
            else:
                # Otherwise show endpoint count
                endpoint_count = len(tags_map[tag])
                f.write(f"{endpoint_count} endpoints\n\n")

    print(f"Saved API descriptions for LLMs to {descriptions_file}")

    # Print summary
    print("")
    print("=" * 80)
    print("SCRAPING COMPLETE!")
    print("=" * 80)
    print(f"Total endpoints: {len(all_endpoints)}")
    print(f"Total tags: {len(tags_map)}")
    print(f"Output directory: {output_dir}")
    print("")
    print("Generated files:")
    print(f"  - {sitemap_file.name} (API sitemap with navigation links for LLMs)")
    print(
        f"  - {descriptions_file.name} (API section descriptions with navigation links)"
    )
    print(f"  - {spec_file.name} (Full OpenAPI spec)")
    print(f"  - {map_file.name} (API map with all endpoints)")
    print(f"  - {all_endpoints_file.name} (All endpoints documentation)")
    print(f"  - {tags_file.name} (Endpoints grouped by tag)")
    print("=" * 80)


if __name__ == "__main__":
    try:
        scrape_cyoda_api_docs()
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
