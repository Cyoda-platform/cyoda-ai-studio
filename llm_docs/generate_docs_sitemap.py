#!/usr/bin/env python3
"""
Script to generate cyoda-docs-llms.txt from sitemap.xml
Extracts all URLs and organizes them by category in a markdown format.
"""

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def parse_sitemap(sitemap_path):
    """Parse sitemap.xml and extract all URLs."""
    tree = ET.parse(sitemap_path)
    root = tree.getroot()

    # Handle XML namespace
    namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    urls = []
    for url_element in root.findall("ns:url", namespace):
        loc = url_element.find("ns:loc", namespace)
        if loc is not None:
            urls.append(loc.text)

    return urls


def categorize_urls(urls):
    """Organize URLs by category."""
    categories = defaultdict(list)

    for url in urls:
        # Remove base URL
        if url == "https://docs.cyoda.net/":
            continue

        # Extract path
        path = url.replace("https://docs.cyoda.net/", "").rstrip("/")

        if not path:
            continue

        # Determine category
        parts = path.split("/")
        category = parts[0]

        # Create a nice title from the path
        title = " ".join(parts[-1].split("-")).title()

        categories[category].append(
            {"url": url, "title": title, "path": path, "parts": parts}
        )

    return categories


def get_category_title(category):
    """Convert category slug to nice title."""
    titles = {
        "getting-started": "Getting Started",
        "guides": "Guides",
        "concepts": "Concepts",
        "architecture": "Architecture",
        "cloud": "Cloud Services",
        "schemas": "Schema Reference",
        "api-reference": "API Reference",
        "legal": "Legal",
        "imprint": "Legal",
        "cookies": "Legal",
        "privacy": "Legal",
        "terms": "Legal",
    }
    return titles.get(category, category.replace("-", " ").title())


def generate_markdown(categories):
    """Generate markdown content from categorized URLs."""
    output = []
    output.append("# Cyoda Documentation\n")

    # Define category order
    category_order = [
        "getting-started",
        "guides",
        "concepts",
        "architecture",
        "cloud",
        "schemas",
        "api-reference",
        "legal",
    ]

    # Group legal pages
    legal_pages = []
    for cat in ["imprint", "cookies", "privacy", "terms"]:
        if cat in categories:
            legal_pages.extend(categories[cat])
            del categories[cat]
    if legal_pages:
        categories["legal"] = legal_pages

    # Process categories in order
    for category in category_order:
        if category not in categories:
            continue

        items = categories[category]

        # Skip empty categories
        if not items:
            continue

        # Add category header
        output.append(f"## {get_category_title(category)}\n")

        # For schemas, organize hierarchically
        if category == "schemas":
            output.extend(format_schemas(items))
        else:
            # Sort items by path depth and then alphabetically
            items.sort(key=lambda x: (len(x["parts"]), x["path"]))

            for item in items:
                output.append(f"- [{item['title']}]({item['url']})")

        output.append("")  # Empty line after each category

    # Add any remaining categories not in the order
    for category, items in sorted(categories.items()):
        if category in category_order:
            continue

        output.append(f"## {get_category_title(category)}\n")
        items.sort(key=lambda x: (len(x["parts"]), x["path"]))

        for item in items:
            output.append(f"- [{item['title']}]({item['url']})")

        output.append("")

    return "\n".join(output)


def format_schemas(items):
    """Format schema items hierarchically."""
    lines = []

    # Build a tree structure
    tree = {}
    for item in items:
        path = item["path"]
        tree[path] = item

    # Sort by path to ensure parents come before children
    sorted_paths = sorted(tree.keys(), key=lambda x: (len(x.split("/")), x))

    # Track what we've printed to avoid duplicates
    printed = set()

    def print_item(path, depth=0):
        """Recursively print item and its children."""
        if path in printed:
            return []

        item = tree[path]
        indent = "  " * depth
        result = [f"{indent}- [{item['title']}]({item['url']})"]
        printed.add(path)

        # Find and print children
        children = []
        for other_path in sorted_paths:
            if other_path == path:
                continue
            # Check if other_path is a direct child of path
            if other_path.startswith(path + "/"):
                # Make sure it's a direct child, not a grandchild
                remainder = other_path[len(path) + 1 :]
                if "/" not in remainder:
                    children.append(other_path)

        # Sort children alphabetically
        children.sort()
        for child_path in children:
            if child_path not in printed:
                result.extend(print_item(child_path, depth + 1))

        return result

    # Start with top-level schema items (schemas/ only has 1 slash)
    for path in sorted_paths:
        if path.count("/") == 0:
            # This is a root item under schemas
            lines.extend(print_item(path, 0))

    return lines


def main():
    """Main function."""
    script_dir = Path(__file__).parent
    sitemap_path = script_dir / "sources" / "sitemap.xml"
    output_path = script_dir / "outputs" / "cyoda-docs-llms.txt"

    print(f"Parsing sitemap from: {sitemap_path}")

    # Parse sitemap
    urls = parse_sitemap(sitemap_path)
    print(f"Found {len(urls)} URLs")

    # Categorize URLs
    categories = categorize_urls(urls)
    print(f"Organized into {len(categories)} categories")

    # Generate markdown
    markdown = generate_markdown(categories)

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"\nGenerated {output_path}")
    print(f"Total lines: {len(markdown.splitlines())}")

    # Print summary
    print("\nCategories:")
    for category, items in sorted(categories.items()):
        print(f"  {category}: {len(items)} pages")


if __name__ == "__main__":
    main()
