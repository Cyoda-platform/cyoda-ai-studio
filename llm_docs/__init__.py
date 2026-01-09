"""
LLM Documentation Generator

This module provides tools to convert OpenAPI specifications and web documentation
into LLM-friendly text formats following the llms.txt specification.
"""

__version__ = "1.0.0"

from llm_docs.converters.docs_fetcher import DocumentationFetcher
from llm_docs.converters.openapi_converter import OpenAPIConverter

__all__ = ["OpenAPIConverter", "DocumentationFetcher"]
