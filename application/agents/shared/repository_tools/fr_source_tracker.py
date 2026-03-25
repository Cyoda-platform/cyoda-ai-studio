"""Functional Requirements Source Tracker.

This module adds source document tracking to consolidated FR documents.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FRSourceTracker:
    """Tracks source documents in consolidated functional requirements."""

    @staticmethod
    def add_source_references(
        consolidated_fr_content: str,
        source_documents: List[Dict[str, str]],
    ) -> str:
        """Add source document references to consolidated FR.

        Args:
            consolidated_fr_content: Original consolidated FR content
            source_documents: List of source document metadata
                            Each dict should have: {"name": str, "path": str}

        Returns:
            FR content with source references added
        """
        logger.info(f"Adding source references for {len(source_documents)} documents")

        # Add header section with source documents
        header = FRSourceTracker._create_source_header(source_documents)

        # Add source attribution footer
        footer = FRSourceTracker._create_source_footer(source_documents)

        # Combine with original content
        tracked_content = f"{header}\n\n{consolidated_fr_content}\n\n{footer}"

        logger.info("✅ Source references added to FR document")
        return tracked_content

    @staticmethod
    def _create_source_header(source_documents: List[Dict[str, str]]) -> str:
        """Create header section listing source documents.

        Args:
            source_documents: List of source document metadata

        Returns:
            Formatted header markdown
        """
        lines = [
            "# Functional Requirements",
            "",
            "## Source Documents",
            "",
            "This consolidated functional requirements document was generated from the following source documents:",
            "",
        ]

        for idx, doc in enumerate(source_documents, 1):
            doc_name = doc.get("name", f"Document {idx}")
            lines.append(f"{idx}. **{doc_name}**")

        lines.extend(
            [
                "",
                "---",
                "",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def _create_source_footer(source_documents: List[Dict[str, str]]) -> str:
        """Create footer section with source document details.

        Args:
            source_documents: List of source document metadata

        Returns:
            Formatted footer markdown
        """
        lines = [
            "---",
            "",
            "## Document Traceability",
            "",
            "### Source Document References",
            "",
        ]

        for idx, doc in enumerate(source_documents, 1):
            doc_name = doc.get("name", f"Document {idx}")
            doc_path = doc.get("path", "N/A")
            lines.append(f"**[{idx}] {doc_name}**")
            lines.append(f"  - Path: `{doc_path}`")
            lines.append("")

        lines.extend(
            [
                "### How to Use This Document",
                "",
                "- Each section consolidates requirements from one or more source documents",
                "- Review source documents for complete details and context",
                "- Contact the requirements author for clarifications",
                "",
            ]
        )

        return "\n".join(lines)

    @staticmethod
    def extract_source_documents_from_directory(
        source_dir: str,
    ) -> List[Dict[str, str]]:
        """Extract metadata for all source documents in directory.

        Args:
            source_dir: Directory containing source documents

        Returns:
            List of source document metadata dictionaries
        """
        source_path = Path(source_dir)
        if not source_path.exists():
            logger.warning(f"Source directory not found: {source_dir}")
            return []

        source_documents = []

        # Find all markdown and text files
        for file_path in source_path.glob("*.md"):
            source_documents.append(
                {
                    "name": file_path.name,
                    "path": str(file_path),
                    "type": "markdown",
                }
            )

        for file_path in source_path.glob("*.txt"):
            source_documents.append(
                {
                    "name": file_path.name,
                    "path": str(file_path),
                    "type": "text",
                }
            )

        logger.info(f"Found {len(source_documents)} source documents in {source_dir}")
        return source_documents

    @staticmethod
    def create_tracked_fr(
        consolidated_fr_content: str,
        source_dir: str,
        output_path: str,
    ) -> bool:
        """Create a consolidated FR with source tracking.

        Args:
            consolidated_fr_content: Original FR content
            source_dir: Directory containing source documents
            output_path: Path to write tracked FR

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract source documents
            source_documents = FRSourceTracker.extract_source_documents_from_directory(
                source_dir
            )

            if not source_documents:
                logger.warning(
                    "No source documents found, saving FR without source tracking"
                )
                tracked_content = consolidated_fr_content
            else:
                # Add source references
                tracked_content = FRSourceTracker.add_source_references(
                    consolidated_fr_content, source_documents
                )

            # Write to output
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(tracked_content)

            logger.info(f"✅ Created tracked FR at {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create tracked FR: {e}", exc_info=True)
            return False
