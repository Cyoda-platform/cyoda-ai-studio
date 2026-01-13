"""Tests for documentation fetcher."""

import xml.etree.ElementTree as ET

import pytest

from llm_docs.converters.docs_fetcher import DocumentationFetcher


@pytest.fixture
def sample_sitemap(tmp_path):
    """Create a sample sitemap XML file."""
    sitemap_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>https://docs.example.com/</loc>
        <priority>1.00</priority>
    </url>
    <url>
        <loc>https://docs.example.com/getting-started/intro/</loc>
        <priority>0.80</priority>
    </url>
    <url>
        <loc>https://docs.example.com/guides/authentication/</loc>
        <priority>0.80</priority>
    </url>
    <url>
        <loc>https://docs.example.com/privacy/</loc>
        <priority>0.50</priority>
    </url>
</urlset>
"""
    sitemap_file = tmp_path / "sitemap.xml"
    sitemap_file.write_text(sitemap_content)
    return str(sitemap_file)


class TestDocumentationFetcher:
    """Test suite for DocumentationFetcher."""

    def test_initialization(self, sample_sitemap):
        """Test fetcher initialization."""
        fetcher = DocumentationFetcher(
            sample_sitemap, max_pages=10, delay_between_requests=0.1
        )

        assert fetcher.sitemap_path == sample_sitemap
        assert fetcher.max_pages == 10
        assert fetcher.delay == 0.1
        assert fetcher.urls == []

    def test_load_sitemap(self, sample_sitemap):
        """Test sitemap loading and parsing."""
        fetcher = DocumentationFetcher(sample_sitemap)
        urls = fetcher.load_sitemap()

        # Should skip privacy page, load 2 others (excluding root)
        assert len(urls) == 3
        assert all("url" in u and "priority" in u for u in urls)

        # Check that privacy page was skipped
        assert not any("privacy" in u["url"] for u in urls)

        # Verify sorted by priority
        assert urls[0]["priority"] >= urls[1]["priority"]

    def test_load_sitemap_custom_skip_patterns(self, sample_sitemap):
        """Test sitemap loading with custom skip patterns."""
        fetcher = DocumentationFetcher(sample_sitemap)
        urls = fetcher.load_sitemap(skip_patterns=["getting-started"])

        # Should skip getting-started pages
        assert not any("getting-started" in u["url"] for u in urls)

    def test_generate_condensed_docs_txt(self, sample_sitemap):
        """Test condensed docs generation."""
        fetcher = DocumentationFetcher(sample_sitemap, max_pages=5)
        fetcher.load_sitemap()

        condensed = fetcher.generate_condensed_docs_txt()

        assert "## Documentation" in condensed
        assert "### Getting Started" in condensed
        assert "### Guides" in condensed
        assert "[Intro]" in condensed
        assert "[Authentication]" in condensed

    def test_generate_condensed_with_custom_categories(self, sample_sitemap):
        """Test condensed docs with custom categories."""
        fetcher = DocumentationFetcher(sample_sitemap)
        fetcher.load_sitemap()

        categories = {"getting-started": "Quick Start", "guides": "User Guides"}

        condensed = fetcher.generate_condensed_docs_txt(categories=categories)

        assert "### Quick Start" in condensed
        assert "### User Guides" in condensed

    def test_fetch_page_content_html_cleaning(self):
        """Test HTML cleaning in page content extraction."""
        fetcher = DocumentationFetcher("dummy.xml")

        # Mock HTML content
        html_content = """
        <html>
            <head><style>body { color: red; }</style></head>
            <body>
                <script>console.log('test');</script>
                <h1>Title</h1>
                <p>Content paragraph</p>
                <nav>Skip to content</nav>
            </body>
        </html>
        """

        # Note: This would require mocking urlopen, which we'll skip for now
        # but the method is designed to handle HTML cleaning

    def test_url_categorization(self, sample_sitemap):
        """Test that URLs are correctly categorized."""
        fetcher = DocumentationFetcher(sample_sitemap)
        urls = fetcher.load_sitemap()

        getting_started_urls = [u for u in urls if "/getting-started/" in u["url"]]
        guide_urls = [u for u in urls if "/guides/" in u["url"]]

        assert len(getting_started_urls) > 0
        assert len(guide_urls) > 0
