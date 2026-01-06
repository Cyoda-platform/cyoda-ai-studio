#!/usr/bin/env python3
"""
LLM Documentation Generator CLI

Command-line interface for generating LLM-friendly documentation from OpenAPI specs and web docs.
"""

import argparse
import sys
from pathlib import Path

from llm_docs.converters.openapi_converter import OpenAPIConverter
from llm_docs.converters.docs_fetcher import DocumentationFetcher


def generate_openapi_docs(
    openapi_file: str,
    output_dir: str,
    full_filename: str = "openapi-llm-full.txt",
    condensed_filename: str = "openapi-llms.txt"
):
    """
    Generate LLM documentation from OpenAPI specification.

    Args:
        openapi_file: Path to OpenAPI JSON file
        output_dir: Output directory for generated files
        full_filename: Filename for full documentation
        condensed_filename: Filename for condensed documentation
    """
    print("=" * 60)
    print("OpenAPI to LLM Documentation Converter")
    print("=" * 60)
    print()

    # Load and convert
    print(f"Loading OpenAPI spec from: {openapi_file}")
    converter = OpenAPIConverter.from_file(openapi_file)
    print(f"  ✓ Loaded: {converter.info.get('title', 'Unknown API')}")
    print()

    # Generate full version
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    full_path = output_path / full_filename
    print(f"Generating full documentation: {full_path}")
    full_txt = converter.generate_full_llm_txt()

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(full_txt)
    print(f"  ✓ Generated {len(full_txt)} characters")
    print()

    # Generate condensed version
    condensed_path = output_path / condensed_filename
    print(f"Generating condensed documentation: {condensed_path}")
    condensed_txt = converter.generate_condensed_llms_txt()

    with open(condensed_path, 'w', encoding='utf-8') as f:
        f.write(condensed_txt)
    print(f"  ✓ Generated {len(condensed_txt)} characters")
    print()

    print("=" * 60)
    print("OpenAPI Conversion Complete!")
    print("=" * 60)


def generate_web_docs(
    sitemap_file: str,
    output_dir: str,
    max_pages: int = 25,
    title: str = "Platform Documentation",
    full_filename: str = "docs-llm-full.txt",
    condensed_filename: str = "docs-llms.txt"
):
    """
    Generate LLM documentation from web sitemap.

    Args:
        sitemap_file: Path to sitemap XML file
        output_dir: Output directory for generated files
        max_pages: Maximum number of pages to fetch
        title: Title for the documentation
        full_filename: Filename for full documentation
        condensed_filename: Filename for condensed documentation
    """
    print("=" * 60)
    print("Web Documentation to LLM Text Converter")
    print("=" * 60)
    print()

    # Load sitemap
    print(f"Loading sitemap from: {sitemap_file}")
    fetcher = DocumentationFetcher(sitemap_file, max_pages=max_pages)
    urls = fetcher.load_sitemap()
    print(f"  ✓ Found {len(urls)} documentation pages")
    print()

    # Generate full version
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    full_path = output_path / full_filename
    print(f"Generating full documentation: {full_path}")
    full_txt = fetcher.generate_full_docs_txt(title=title)

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(full_txt)
    print(f"  ✓ Generated {len(full_txt)} characters")
    print()

    # Generate condensed version
    condensed_path = output_path / condensed_filename
    print(f"Generating condensed documentation: {condensed_path}")
    condensed_txt = fetcher.generate_condensed_docs_txt()

    with open(condensed_path, 'w', encoding='utf-8') as f:
        f.write(condensed_txt)
    print(f"  ✓ Generated {len(condensed_txt)} characters")
    print()

    print("=" * 60)
    print("Web Documentation Conversion Complete!")
    print("=" * 60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate LLM-friendly documentation from OpenAPI specs and web docs"
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # OpenAPI converter
    openapi_parser = subparsers.add_parser('openapi', help='Convert OpenAPI specification')
    openapi_parser.add_argument(
        'openapi_file',
        help='Path to OpenAPI JSON file'
    )
    openapi_parser.add_argument(
        '--output-dir',
        default='llm_docs/outputs',
        help='Output directory (default: llm_docs/outputs)'
    )
    openapi_parser.add_argument(
        '--full-filename',
        default='openapi-llm-full.txt',
        help='Filename for full documentation (default: openapi-llm-full.txt)'
    )
    openapi_parser.add_argument(
        '--condensed-filename',
        default='openapi-llms.txt',
        help='Filename for condensed documentation (default: openapi-llms.txt)'
    )

    # Web docs fetcher
    webdocs_parser = subparsers.add_parser('webdocs', help='Convert web documentation from sitemap')
    webdocs_parser.add_argument(
        'sitemap_file',
        help='Path to sitemap XML file'
    )
    webdocs_parser.add_argument(
        '--output-dir',
        default='llm_docs/outputs',
        help='Output directory (default: llm_docs/outputs)'
    )
    webdocs_parser.add_argument(
        '--max-pages',
        type=int,
        default=25,
        help='Maximum number of pages to fetch (default: 25)'
    )
    webdocs_parser.add_argument(
        '--title',
        default='Platform Documentation',
        help='Title for the documentation (default: Platform Documentation)'
    )
    webdocs_parser.add_argument(
        '--full-filename',
        default='docs-llm-full.txt',
        help='Filename for full documentation (default: docs-llm-full.txt)'
    )
    webdocs_parser.add_argument(
        '--condensed-filename',
        default='docs-llms.txt',
        help='Filename for condensed documentation (default: docs-llms.txt)'
    )

    # All (both OpenAPI and web docs)
    all_parser = subparsers.add_parser('all', help='Convert both OpenAPI and web documentation')
    all_parser.add_argument(
        'openapi_file',
        help='Path to OpenAPI JSON file'
    )
    all_parser.add_argument(
        'sitemap_file',
        help='Path to sitemap XML file'
    )
    all_parser.add_argument(
        '--output-dir',
        default='llm_docs/outputs',
        help='Output directory (default: llm_docs/outputs)'
    )
    all_parser.add_argument(
        '--max-pages',
        type=int,
        default=25,
        help='Maximum number of web pages to fetch (default: 25)'
    )

    args = parser.parse_args()

    if args.command == 'openapi':
        generate_openapi_docs(
            args.openapi_file,
            args.output_dir,
            args.full_filename,
            args.condensed_filename
        )
    elif args.command == 'webdocs':
        generate_web_docs(
            args.sitemap_file,
            args.output_dir,
            args.max_pages,
            args.title,
            args.full_filename,
            args.condensed_filename
        )
    elif args.command == 'all':
        generate_openapi_docs(
            args.openapi_file,
            args.output_dir,
            'openapi-llm-full.txt',
            'openapi-llms.txt'
        )
        print()
        generate_web_docs(
            args.sitemap_file,
            args.output_dir,
            args.max_pages,
            'Cyoda Platform Documentation',
            'cyoda-docs-llm-full.txt',
            'cyoda-docs-llms.txt'
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
