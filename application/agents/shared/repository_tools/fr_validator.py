"""Functional Requirements Validator.

This module validates that consolidated functional requirements documents
match the content from source documents.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FRValidator:
    """Validates functional requirements consolidation."""

    @staticmethod
    def _read_file_content(file_path: str) -> Optional[str]:
        """Read file content safely.

        Args:
            file_path: Path to file

        Returns:
            File content or None if error
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None

    @staticmethod
    async def _extract_key_requirements_with_llm(
        content: str, source_name: str, llm_client: Optional[Any] = None
    ) -> List[Dict[str, str]]:
        """Extract key requirements from document using LLM.

        Args:
            content: Document content
            source_name: Source document name
            llm_client: LLM client for extraction

        Returns:
            List of requirements with metadata
        """
        if not llm_client:
            return FRValidator._extract_key_requirements_with_regex(
                content, source_name
            )

        prompt = f"""Extract the key functional requirements from this document.
For each requirement, provide:
1. A brief title/summary (max 10 words)
2. Category (e.g., "User Management", "Data Processing", "API", etc.)
3. Priority if mentioned (High/Medium/Low)

Format your response as a structured list.

Document: {source_name}

Content:
{content[:5000]}  # Limit to first 5000 chars for efficiency
"""

        try:
            response = await llm_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text if response.content else ""

            # Parse LLM response to extract requirements
            requirements = []
            current_req = None

            for line in response_text.split("\n"):
                line = line.strip()
                if not line:
                    continue

                # Look for requirement markers
                if line.startswith(("-", "*", "•")) or line[0].isdigit():
                    # New requirement
                    if current_req:
                        requirements.append(current_req)

                    # Extract title
                    title = line.lstrip("-*•0123456789. ").strip()
                    current_req = {
                        "title": title[:100],  # Limit length
                        "source": source_name,
                        "category": "General",
                        "priority": "Medium",
                    }

            # Add last requirement
            if current_req:
                requirements.append(current_req)

            logger.info(
                f"Extracted {len(requirements)} key requirements from {source_name} using LLM"
            )
            return requirements

        except Exception as e:
            logger.warning(f"LLM extraction failed, falling back to regex: {e}")
            return FRValidator._extract_key_requirements_with_regex(
                content, source_name
            )

    @staticmethod
    def _extract_key_requirements_with_regex(
        content: str, source_name: str
    ) -> List[Dict[str, str]]:
        """Extract key requirements using regex patterns.

        Args:
            content: Document content
            source_name: Source document name

        Returns:
            List of requirements
        """
        requirements = []

        # Look for common requirement patterns
        patterns = [
            r"(?:requirement|req|feature)[\s#]*\d+[:\s]+(.+)",  # REQ-001: Title
            r"^[-*]\s+(.+)$",  # Bullet points
            r"^\d+\.\s+(.+)$",  # Numbered lists
        ]

        import re

        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:  # Skip very short lines
                continue

            for pattern in patterns:
                match = re.match(pattern, line, re.IGNORECASE | re.MULTILINE)
                if match:
                    title = match.group(1).strip()
                    if len(title) > 10:  # Only meaningful requirements
                        requirements.append(
                            {
                                "title": title[:100],
                                "source": source_name,
                                "category": "General",
                                "priority": "Medium",
                            }
                        )
                    break

        logger.info(
            f"Extracted {len(requirements)} key requirements from {source_name} using regex"
        )
        return requirements

    @staticmethod
    async def _check_requirement_in_consolidated(
        requirement: Dict[str, str],
        consolidated_content: str,
        llm_client: Optional[Any] = None,
    ) -> Tuple[bool, float]:
        """Check if requirement is present in consolidated FR.

        Args:
            requirement: Requirement to check
            consolidated_content: Consolidated FR content
            llm_client: LLM client for semantic matching

        Returns:
            Tuple of (is_present, confidence_score)
        """
        req_title = requirement["title"].lower()

        # Simple keyword matching as fallback
        if req_title in consolidated_content.lower():
            return True, 0.9

        # Check for partial matches (at least 50% of words)
        req_words = set(req_title.split())
        content_lower = consolidated_content.lower()
        matching_words = sum(1 for word in req_words if word in content_lower)

        if len(req_words) > 0:
            match_ratio = matching_words / len(req_words)
            if match_ratio >= 0.5:
                return True, match_ratio

        return False, 0.0

    @staticmethod
    async def validate_fr_consolidation(
        source_documents_dir: str,
        consolidated_fr_path: str,
        llm_client: Optional[Any] = None,
    ) -> Tuple[bool, str]:
        """Validate that consolidated FR matches source documents.

        Args:
            source_documents_dir: Directory containing uploaded source documents
            consolidated_fr_path: Path to consolidated FR document
            llm_client: Optional LLM client for advanced validation

        Returns:
            Tuple of (validation_passed, report_message)
        """
        logger.info(
            f"Validating FR consolidation: {source_documents_dir} -> {consolidated_fr_path}"
        )

        # Read consolidated FR
        consolidated_content = FRValidator._read_file_content(consolidated_fr_path)
        if not consolidated_content:
            return False, "ERROR: Could not read consolidated FR document"

        # Find source documents
        source_dir = Path(source_documents_dir)
        if not source_dir.exists():
            return (
                False,
                f"ERROR: Source documents directory not found: {source_documents_dir}",
            )

        source_files = list(source_dir.glob("*.md")) + list(source_dir.glob("*.txt"))
        if not source_files:
            logger.warning("No source documents found for comparison")
            return (
                True,
                "✅ No source documents to validate against (FR created from scratch)",
            )

        # Extract key requirements from each source document
        all_requirements = []
        source_summaries = []

        for source_file in source_files:
            content = FRValidator._read_file_content(str(source_file))
            if not content:
                continue

            requirements = await FRValidator._extract_key_requirements_with_llm(
                content, source_file.name, llm_client
            )
            all_requirements.extend(requirements)
            source_summaries.append(
                {
                    "name": source_file.name,
                    "requirement_count": len(requirements),
                }
            )

        if not all_requirements:
            return True, "✅ No specific requirements extracted from source documents"

        logger.info(
            f"Extracted {len(all_requirements)} total requirements from {len(source_files)} source documents"
        )

        # Check each requirement against consolidated FR
        matched_requirements = []
        missing_requirements = []

        for req in all_requirements:
            is_present, confidence = (
                await FRValidator._check_requirement_in_consolidated(
                    req, consolidated_content, llm_client
                )
            )

            if is_present:
                matched_requirements.append({**req, "confidence": confidence})
            else:
                missing_requirements.append(req)

        # Calculate match percentage
        match_percentage = (
            len(matched_requirements) / len(all_requirements) * 100
            if all_requirements
            else 100
        )

        # Build report
        validation_passed = match_percentage >= 70  # 70% threshold

        report_lines = []

        if validation_passed:
            report_lines.append("✅ **FR Consolidation Validation: PASSED**")
        else:
            report_lines.append("⚠️ **FR Consolidation Validation: REVIEW NEEDED**")

        report_lines.append("")
        report_lines.append("### Summary")
        report_lines.append(f"- **Source Documents**: {len(source_files)} files")
        report_lines.append(
            f"- **Key Requirements Identified**: {len(all_requirements)}"
        )
        report_lines.append(
            f"- **Requirements Matched**: {len(matched_requirements)} ({match_percentage:.1f}%)"
        )
        report_lines.append(f"- **Potentially Missing**: {len(missing_requirements)}")
        report_lines.append("")

        # Source documents breakdown
        if source_summaries:
            report_lines.append("### Source Documents")
            for summary in source_summaries:
                report_lines.append(
                    f"- **{summary['name']}**: {summary['requirement_count']} requirements extracted"
                )
            report_lines.append("")

        # Show matched requirements (limit to 5 for brevity)
        if matched_requirements:
            report_lines.append(
                f"### ✅ Matched Requirements ({len(matched_requirements)})"
            )
            for req in matched_requirements[:5]:
                confidence_icon = "✅" if req["confidence"] >= 0.8 else "⚡"
                report_lines.append(
                    f"   {confidence_icon} {req['title'][:80]} (from {req['source']})"
                )
            if len(matched_requirements) > 5:
                report_lines.append(f"   ...and {len(matched_requirements) - 5} more")
            report_lines.append("")

        # Show missing requirements
        if missing_requirements:
            report_lines.append(
                f"### ⚠️ Potentially Missing Requirements ({len(missing_requirements)})"
            )
            for req in missing_requirements[:10]:
                report_lines.append(f"   - {req['title'][:80]} (from {req['source']})")
            if len(missing_requirements) > 10:
                report_lines.append(f"   ...and {len(missing_requirements) - 10} more")
            report_lines.append("")

        # Recommendations
        report_lines.append("### 💡 Recommendations")
        if validation_passed:
            report_lines.append(
                "✅ Consolidated FR appears to cover most source requirements"
            )
            if missing_requirements:
                report_lines.append(
                    "ℹ️ Review potentially missing items to ensure they were intentionally excluded or merged"
                )
        else:
            report_lines.append(
                "⚠️ Significant requirements may be missing from consolidated FR"
            )
            report_lines.append(
                "📝 Recommend reviewing source documents and regenerating FR with more complete coverage"
            )
            report_lines.append(
                "🔍 Consider consolidating requirements document-by-document for better traceability"
            )

        report = "\n".join(report_lines)
        logger.info(f"FR Validation complete: {match_percentage:.1f}% match")

        return validation_passed, report
