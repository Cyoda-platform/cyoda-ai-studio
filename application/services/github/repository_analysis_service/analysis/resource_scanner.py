"""Resource scanning for versioned entities, workflows, and requirements."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResourceScanner:
    """Scanner for repository resources (entities, workflows, requirements)."""

    def __init__(self):
        pass

    def is_textual_file(self, filename: str) -> bool:
        """Check if a file is a textual format based on extension."""
        filename_lower = filename.lower()
        textual_extensions = {
            ".pdf",
            ".docx",
            ".xlsx",
            ".pptx",
            ".xml",
            ".json",
            ".txt",
            ".yml",
            ".yaml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".properties",
            ".env",
            ".md",
            ".markdown",
            ".rst",
            ".tex",
            ".latex",
            ".sql",
            ".dockerfile",
            ".gitignore",
            ".gitattributes",
            ".editorconfig",
            ".htaccess",
            ".robots",
            ".mk",
            ".cmake",
            ".gradle",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".cs",
            ".rs",
            ".go",
            ".swift",
            ".dart",
            ".hs",
            ".ml",
            ".fs",
            ".clj",
            ".elm",
            ".r",
            ".jl",
            ".f90",
            ".f95",
            ".php",
            ".rb",
            ".scala",
            ".lua",
            ".nim",
            ".zig",
            ".v",
            ".d",
            ".cr",
            ".ex",
            ".exs",
            ".erl",
            ".hrl",
        }
        files_without_extension = {"dockerfile", "makefile"}

        for ext in textual_extensions:
            if filename_lower.endswith(ext):
                return True
        if filename_lower in files_without_extension:
            return True
        return False

    def _load_json_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load and parse JSON file.

        Args:
            file_path: Path to JSON file.

        Returns:
            Parsed JSON content or None if parsing fails.
        """
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return None

    def _create_resource_dict(
        self,
        name: str,
        resource_type: str,
        repo_path_obj: Path,
        file_path: Path,
        content: Dict[str, Any],
        version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create resource dictionary with metadata.

        Args:
            name: Resource name.
            resource_type: Type of resource (entity, workflow, etc.).
            repo_path_obj: Repository root path.
            file_path: Path to resource file.
            content: Parsed JSON content.
            version: Version string (optional).

        Returns:
            Resource dictionary with metadata.
        """
        res_dict = {
            "name": name,
            "version": version,
            "path": str(file_path.relative_to(repo_path_obj)),
            "content": content,
        }

        # Extract entity name for workflows
        if resource_type == "workflow" and isinstance(content, dict):
            entity_name = content.get("entity_name") or content.get("entityName")
            if entity_name:
                res_dict["entity_name"] = entity_name

        return res_dict

    def _find_resource_file(
        self, directory: Path, resource_name: str
    ) -> Optional[Path]:
        """Find resource JSON file in directory.

        Searches for exact match first, then case-insensitive match,
        then single JSON file fallback.

        Args:
            directory: Directory to search.
            resource_name: Name of resource to find.

        Returns:
            Path to resource file or None if not found.
        """
        # Try exact match
        exact = directory / f"{resource_name}.json"
        if exact.exists():
            return exact

        # Try case-insensitive match
        json_files = list(directory.glob("*.json"))
        for j in json_files:
            if j.stem.lower() == resource_name.lower():
                return j

        # Fallback: single JSON file
        if len(json_files) == 1:
            return json_files[0]

        return None

    def _scan_version_directories(
        self,
        resource_dir: Path,
        resource_name: str,
        resource_type: str,
        repo_path_obj: Path,
    ) -> List[Dict[str, Any]]:
        """Scan version directories within resource directory.

        Args:
            resource_dir: Path to resource directory.
            resource_name: Name of resource.
            resource_type: Type of resource (entity, workflow, etc.).
            repo_path_obj: Repository root path.

        Returns:
            List of resource dictionaries from all versions.
        """
        resources = []
        version_dirs = [
            d
            for d in resource_dir.iterdir()
            if d.is_dir() and d.name.startswith("version_")
        ]

        if not version_dirs:
            return resources

        # Sort by version number
        def sort_key(d: Path) -> int:
            try:
                return int(d.name.split("_")[1])
            except Exception:
                return 0

        for v_dir in sorted(version_dirs, key=sort_key):
            res_file = self._find_resource_file(v_dir, resource_name)
            if not res_file:
                continue

            content = self._load_json_file(res_file)
            if content is None:
                continue

            res_dict = self._create_resource_dict(
                name=resource_name,
                resource_type=resource_type,
                repo_path_obj=repo_path_obj,
                file_path=res_file,
                content=content,
                version=v_dir.name,
            )
            resources.append(res_dict)

        return resources

    def _scan_direct_files(
        self,
        resource_dir: Path,
        resource_name: str,
        resource_type: str,
        repo_path_obj: Path,
    ) -> List[Dict[str, Any]]:
        """Scan for resource files directly in directory (no version subdirs).

        Args:
            resource_dir: Path to resource directory.
            resource_name: Name of resource.
            resource_type: Type of resource (entity, workflow, etc.).
            repo_path_obj: Repository root path.

        Returns:
            List with single resource dictionary if found.
        """
        res_file = self._find_resource_file(resource_dir, resource_name)
        if not res_file:
            return []

        content = self._load_json_file(res_file)
        if content is None:
            return []

        res_dict = self._create_resource_dict(
            name=resource_name,
            resource_type=resource_type,
            repo_path_obj=repo_path_obj,
            file_path=res_file,
            content=content,
        )
        return [res_dict]

    def scan_versioned_resources(
        self, resources_dir: Path, resource_type: str, repo_path_obj: Path
    ) -> List[Dict[str, Any]]:
        """Scan for versioned resources (entities, workflows, etc.).

        Supports both versioned (with version_ subdirectories) and flat directory structures.
        Searches for JSON files matching resource naming patterns.

        Args:
            resources_dir: Path to resources directory.
            resource_type: Type of resource (entity, workflow, etc.).
            repo_path_obj: Repository root path (for relative paths).

        Returns:
            List of resource dictionaries with metadata and content.
        """
        resources = []
        if not resources_dir.exists():
            logger.info(
                f"📁 {resource_type.title()} directory not found: {resources_dir}"
            )
            return resources

        for item in sorted(resources_dir.iterdir()):
            # Skip private items
            if item.name.startswith("_"):
                continue

            # Handle flat JSON files
            if item.is_file() and item.suffix == ".json":
                content = self._load_json_file(item)
                if content is None:
                    continue

                res_dict = self._create_resource_dict(
                    name=item.stem,
                    resource_type=resource_type,
                    repo_path_obj=repo_path_obj,
                    file_path=item,
                    content=content,
                )
                resources.append(res_dict)

            # Handle directories with versioned or flat structures
            elif item.is_dir():
                resource_name = item.name

                # Try scanning version directories first
                version_resources = self._scan_version_directories(
                    item, resource_name, resource_type, repo_path_obj
                )
                if version_resources:
                    resources.extend(version_resources)
                    continue

                # Fallback: scan for files directly in directory
                direct_resources = self._scan_direct_files(
                    item, resource_name, resource_type, repo_path_obj
                )
                resources.extend(direct_resources)

        return resources
