#!/usr/bin/env python3
"""
Documentation Fetcher

Fetches and converts web documentation from sitemaps into LLM-friendly text formats.
"""

import re
import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen


class DocumentationFetcher:
    """Fetches and converts web documentation into LLM-friendly text formats."""

    def __init__(
        self,
        sitemap_path: str,
        max_pages: int = 25,
        delay_between_requests: float = 0.5,
    ):
        """
        Initialize documentation fetcher.

        Args:
            sitemap_path: Path to sitemap XML file
            max_pages: Maximum number of pages to fetch
            delay_between_requests: Delay in seconds between HTTP requests
        """
        self.sitemap_path = sitemap_path
        self.max_pages = max_pages
        self.delay = delay_between_requests
        self.urls = []

    def load_sitemap(
        self, skip_patterns: Optional[List[str]] = None
    ) -> List[Dict[str, any]]:
        """
        Load and parse sitemap XML file.

        Args:
            skip_patterns: List of URL patterns to skip (e.g., ['imprint', 'privacy'])

        Returns:
            List of URL dictionaries with 'url' and 'priority' keys
        """
        if skip_patterns is None:
            skip_patterns = ["imprint", "cookies", "privacy", "terms", "legal"]

        tree = ET.parse(self.sitemap_path)
        root = tree.getroot()

        # Handle XML namespace
        namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        urls = []
        for url_elem in root.findall("ns:url", namespace):
            loc = url_elem.find("ns:loc", namespace)
            priority = url_elem.find("ns:priority", namespace)

            if loc is not None:
                url = loc.text
                # Skip URLs matching skip patterns
                if not any(pattern in url for pattern in skip_patterns):
                    urls.append(
                        {
                            "url": url,
                            "priority": (
                                float(priority.text) if priority is not None else 0.5
                            ),
                        }
                    )

        # Sort by priority (highest first)
        urls.sort(key=lambda x: x["priority"], reverse=True)
        self.urls = urls
        return urls

    def fetch_page_content(self, url: str) -> str:
        """
        Fetch and extract text content from a documentation page.

        Args:
            url: URL to fetch

        Returns:
            Extracted text content
        """
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; DocFetcher/1.0)"}
            req = Request(url, headers=headers)

            with urlopen(req, timeout=10) as response:
                html = response.read().decode("utf-8")

            # Simple text extraction (remove HTML tags)
            # Remove script and style elements
            html = re.sub(
                r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
            )
            html = re.sub(
                r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
            )

            # Remove HTML tags
            text = re.sub(r"<[^>]+>", "", html)

            # Clean up whitespace
            text = re.sub(r"\n\s*\n", "\n\n", text)
            text = re.sub(r"[ \t]+", " ", text)

            # Extract main content (heuristic: skip navigation/header/footer)
            lines = text.split("\n")
            content_lines = []

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Skip common navigation/header phrases
                if any(
                    skip in line.lower()
                    for skip in [
                        "skip to content",
                        "search",
                        "menu",
                        "navigation",
                        "cookie",
                        "all rights reserved",
                        "© 20",
                    ]
                ):
                    continue

                content_lines.append(line)

            return "\n".join(content_lines)

        except Exception as e:
            print(f"  ⚠ Error fetching {url}: {e}")
            return ""

    def generate_full_docs_txt(
        self,
        title: str = "Platform Documentation",
        categories: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Generate comprehensive documentation from fetched pages.

        Args:
            title: Title for the documentation
            categories: Dictionary mapping URL patterns to category titles

        Returns:
            Full documentation text
        """
        if categories is None:
            categories = {
                "getting-started": "Getting Started",
                "guides": "Guides",
                "concepts": "Concepts",
                "architecture": "Architecture",
                "cloud": "Cloud Services",
                "schemas": "Schema Reference",
            }

        output = []

        output.append(f"# {title}")
        output.append("")
        output.append(
            "The following documentation provides comprehensive guides and references."
        )
        output.append("")

        # Organize pages by category
        categorized_pages = {key: [] for key in categories.keys()}

        print(
            f"Fetching content from {min(self.max_pages, len(self.urls))} documentation pages..."
        )

        for i, url_data in enumerate(self.urls[: self.max_pages]):
            url = url_data["url"]

            # Skip root pages
            if url.endswith(".net/") or url.endswith(".com/"):
                continue

            # Categorize
            category_key = None
            for key in categories.keys():
                if f"/{key}/" in url:
                    category_key = key
                    break

            if not category_key:
                continue

            print(f"  [{i+1}/{self.max_pages}] Fetching: {url}")
            content = self.fetch_page_content(url)

            if content:
                # Extract page title from URL
                page_name = url.rstrip("/").split("/")[-1].replace("-", " ").title()

                categorized_pages[category_key].append(
                    {
                        "title": page_name,
                        "url": url,
                        "content": content[:3000],  # Limit content per page
                    }
                )

            # Be polite to the server
            time.sleep(self.delay)

        # Generate output by category
        for category_key, category_title in categories.items():
            pages = categorized_pages.get(category_key, [])
            if not pages:
                continue

            output.append(f"## {category_title}")
            output.append("")

            for page in pages:
                output.append(f"### {page['title']}")
                output.append("")
                output.append(f"Source: {page['url']}")
                output.append("")
                output.append(page["content"])
                output.append("")
                output.append("---")
                output.append("")

        return "\n".join(output)

    def generate_condensed_docs_txt(
        self, categories: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate condensed documentation with links.

        Args:
            categories: Dictionary mapping URL patterns to category titles

        Returns:
            Condensed documentation text
        """
        if categories is None:
            categories = {
                "getting-started": "Getting Started",
                "guides": "Guides",
                "concepts": "Concepts",
                "architecture": "Architecture",
                "cloud": "Cloud Services",
                "schemas": "Schema Reference",
            }

        output = []

        output.append("## Documentation")
        output.append("")

        for category_key, category_title in categories.items():
            category_urls = [u for u in self.urls if f"/{category_key}/" in u["url"]]

            if not category_urls:
                continue

            output.append(f"### {category_title}")
            output.append("")

            for url_data in category_urls[:8]:  # Limit to 8 per category
                url = url_data["url"]
                page_name = url.rstrip("/").split("/")[-1].replace("-", " ").title()
                output.append(f"- [{page_name}]({url})")

            if len(category_urls) > 8:
                output.append(f"- ... and {len(category_urls) - 8} more")

            output.append("")

        return "\n".join(output)
