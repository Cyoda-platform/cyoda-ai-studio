# LLM Documentation Generator

A Python module for converting OpenAPI specifications and web documentation into LLM-friendly text formats following the [llms.txt specification](https://llmstxt.org/).

## Features

- **OpenAPI Converter**: Transforms OpenAPI 3.x specifications into comprehensive, LLM-readable documentation
- **Documentation Fetcher**: Extracts content from web documentation via sitemaps
- **Dual Output Formats**:
  - Full detailed documentation for deep understanding
  - Condensed `llms.txt` format for quick reference
- **Modular Design**: Separate converters for different source types
- **Comprehensive Tests**: Unit tests for all converters
- **CLI Interface**: Easy-to-use command-line tool

## Installation

```bash
# No additional dependencies required beyond standard library
# If you need to run tests:
pip install pytest
```

## Project Structure

```
llm_docs/
├── __init__.py              # Package initialization
├── converters/              # Converter modules
│   ├── __init__.py
│   ├── openapi_converter.py # OpenAPI to LLM text
│   └── docs_fetcher.py      # Web docs to LLM text
├── sources/                 # Source files
│   ├── download_sources.sh  # Script to download sources
│   ├── openapi.json         # OpenAPI specification
│   └── sitemap.xml          # Documentation sitemap
├── outputs/                 # Generated documentation
│   ├── openapi-llm-full.txt # Full OpenAPI docs
│   ├── openapi-llms.txt     # Condensed OpenAPI docs
│   ├── cyoda-docs-llm-full.txt # Full web docs
│   └── cyoda-docs-llms.txt  # Condensed web docs
├── tests/                   # Unit tests
│   ├── __init__.py
│   ├── test_openapi_converter.py
│   └── test_docs_fetcher.py
├── main.py                  # CLI entry point
└── README.md                # This file
```

## Usage

### Download Source Files

First, download the latest Cyoda OpenAPI specification and documentation sitemap:

```bash
cd llm_docs/sources
chmod +x download_sources.sh
./download_sources.sh
```

### Command Line Interface

The module provides a CLI for generating LLM documentation:

#### Convert OpenAPI Specification

```bash
python -m llm_docs.main openapi sources/openapi.json
```

With custom options:

```bash
python -m llm_docs.main openapi sources/openapi.json \
    --output-dir ./my-outputs \
    --full-filename my-api-full.txt \
    --condensed-filename my-api-llms.txt
```

#### Convert Web Documentation

```bash
python -m llm_docs.main webdocs sources/sitemap.xml \
    --max-pages 25 \
    --title "Cyoda Platform Documentation"
```

#### Convert Both (Recommended)

```bash
python -m llm_docs.main all sources/openapi.json sources/sitemap.xml
```

### Programmatic Usage

#### OpenAPI Converter

```python
from llm_docs.converters.openapi_converter import OpenAPIConverter

# Load from file
converter = OpenAPIConverter.from_file('sources/openapi.json')

# Generate full documentation
full_docs = converter.generate_full_llm_txt()
with open('outputs/api-full.txt', 'w') as f:
    f.write(full_docs)

# Generate condensed documentation
condensed_docs = converter.generate_condensed_llms_txt()
with open('outputs/api-llms.txt', 'w') as f:
    f.write(condensed_docs)
```

#### Documentation Fetcher

```python
from llm_docs.converters.docs_fetcher import DocumentationFetcher

# Initialize fetcher
fetcher = DocumentationFetcher(
    sitemap_path='sources/sitemap.xml',
    max_pages=25,
    delay_between_requests=0.5
)

# Load sitemap
urls = fetcher.load_sitemap()
print(f"Found {len(urls)} documentation pages")

# Generate full documentation
full_docs = fetcher.generate_full_docs_txt(
    title="Cyoda Platform Documentation"
)
with open('outputs/docs-full.txt', 'w') as f:
    f.write(full_docs)

# Generate condensed documentation
condensed_docs = fetcher.generate_condensed_docs_txt()
with open('outputs/docs-llms.txt', 'w') as f:
    f.write(condensed_docs)
```

## Running Tests

```bash
# Run all tests
pytest llm_docs/tests/

# Run specific test file
pytest llm_docs/tests/test_openapi_converter.py

# Run with coverage
pytest llm_docs/tests/ --cov=llm_docs --cov-report=html
```

## Output Formats

### Full Documentation (`*-llm-full.txt`)

Comprehensive documentation including:
- Complete API/documentation overview
- All endpoints with parameters, request/response schemas
- Detailed schema definitions
- Authentication mechanisms
- Full content from web pages (up to 3000 chars per page)

**Use case**: Deep understanding, training data, comprehensive reference

### Condensed Documentation (`*-llms.txt`)

Concise documentation following llms.txt spec:
- High-level overview and summary
- Key capabilities and features
- Endpoint listings by category
- Links to important schemas/pages
- Contact and resource information

**Use case**: Quick reference, context window optimization, LLM navigation

## Customization

### Custom Categories

Both converters support custom category organization:

```python
# Custom categories for documentation fetcher
custom_categories = {
    'api': 'API Reference',
    'tutorials': 'Tutorials',
    'advanced': 'Advanced Topics'
}

fetcher = DocumentationFetcher('sitemap.xml')
fetcher.load_sitemap()
condensed = fetcher.generate_condensed_docs_txt(categories=custom_categories)
```

### Skip Patterns

Filter out unwanted URLs from sitemaps:

```python
fetcher = DocumentationFetcher('sitemap.xml')
urls = fetcher.load_sitemap(
    skip_patterns=['privacy', 'legal', 'cookies', 'internal']
)
```

## Contributing

When adding new features:

1. Add converter logic to `converters/`
2. Write unit tests in `tests/`
3. Update CLI in `main.py`
4. Document usage in this README

## License

This module is part of the cyoda-ai-studio project.

## References

- [llms.txt Specification](https://llmstxt.org/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Cyoda Documentation](https://docs.cyoda.net/)
