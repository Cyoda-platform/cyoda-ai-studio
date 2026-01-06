"""File utility functions for GitHub agent tools.

This module provides utilities for file type detection and validation.
"""

from __future__ import annotations


def is_textual_file(filename: str) -> bool:
    """Check if a file is a textual format based on extension.

    Args:
        filename: The filename to check

    Returns:
        True if the file is a textual format, False otherwise
    """
    filename_lower = filename.lower()

    # Supported textual file extensions
    textual_extensions = {
        # Documents
        ".pdf", ".docx", ".xlsx", ".pptx", ".xml", ".json", ".txt",
        # Configuration
        ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".properties", ".env",
        # Documentation / Markup
        ".md", ".markdown", ".rst", ".tex", ".latex", ".sql",
        # System / Build
        ".dockerfile", ".gitignore", ".gitattributes",
        ".editorconfig", ".htaccess", ".robots",
        ".mk", ".cmake", ".gradle",
        # Programming Languages
        # Web
        ".js", ".ts", ".jsx", ".tsx",
        # Systems
        ".c", ".cpp", ".h", ".hpp", ".cs", ".rs", ".go",
        # Mobile
        ".swift", ".dart",
        # Functional
        ".hs", ".ml", ".fs", ".clj", ".elm",
        # Scientific
        ".r", ".jl", ".f90", ".f95",
        # Other
        ".php", ".rb", ".scala", ".lua", ".nim", ".zig", ".v",
        ".d", ".cr", ".ex", ".exs", ".erl", ".hrl"
    }

    # Files without extension (dockerfile, makefile, etc.)
    files_without_extension = {"dockerfile", "makefile"}

    # Check by extension
    for ext in textual_extensions:
        if filename_lower.endswith(ext):
            return True

    # Check files without extension
    if filename_lower in files_without_extension:
        return True

    return False
