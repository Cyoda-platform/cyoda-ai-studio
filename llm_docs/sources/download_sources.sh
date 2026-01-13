#!/bin/bash
# Download source files for LLM documentation generation

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Downloading Cyoda OpenAPI specification..."
curl -s -o "$SCRIPT_DIR/openapi.json" \
    https://raw.githubusercontent.com/Cyoda-platform/cyoda-docs/main/public/openapi/openapi.json
echo "✓ Downloaded openapi.json ($(wc -l < "$SCRIPT_DIR/openapi.json") lines)"

echo ""
echo "Downloading Cyoda documentation sitemap..."
curl -s -o "$SCRIPT_DIR/sitemap.xml" \
    "https://www.xml-sitemaps.com/download/docs.cyoda.net-2d2b78d89/sitemap.xml?view=1"
echo "✓ Downloaded sitemap.xml ($(wc -l < "$SCRIPT_DIR/sitemap.xml") lines)"

echo ""
echo "All sources downloaded successfully!"
echo "  - $SCRIPT_DIR/openapi.json"
echo "  - $SCRIPT_DIR/sitemap.xml"
