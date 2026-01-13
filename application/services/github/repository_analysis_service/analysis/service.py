"""Core analysis logic and methods for repository scanning."""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from application.services.core.file_system_service import FileSystemService

from .models import SearchMatch
from .resource_scanner import ResourceScanner

logger = logging.getLogger(__name__)

# Resource paths from environment
PYTHON_RESOURCES_PATH = os.getenv("PYTHON_RESOURCES_PATH", "application/resources")
JAVA_RESOURCES_PATH = os.getenv("JAVA_RESOURCES_PATH", "src/main/resources")

# Search constants
SEARCH_TYPE_CONTENT = "content"
SEARCH_TYPE_FILENAME = "filename"
FIND_CONTENT_CMD = (
    "find . -name '{file_pattern}' -type f -exec grep -l -E '{pattern}' {{}} \\;"
)
FIND_FILES_CMD = "find . -name '{pattern}' -type f"
GREP_LINES_CMD = "grep -n -E '{pattern}' '{clean}'"
GREP_PARSE_ERROR = "Error parsing grep output"
SEARCH_COMPLETED_LOG = "Search completed successfully"
FILE_SIZE_DEFAULT = 0


class RepositoryAnalysisService:
    """Service for analyzing repository structure and content."""

    def __init__(self):
        self.fs_service = FileSystemService()
        self.scanner = ResourceScanner()

    def scan_versioned_resources(
        self, resources_dir: Path, resource_type: str, repo_path_obj: Path
    ) -> List[Dict[str, Any]]:
        """Wrapper for scanner.scan_versioned_resources (for test compatibility)."""
        return self.scanner.scan_versioned_resources(
            resources_dir, resource_type, repo_path_obj
        )

    def detect_project_type(self, repo_path: str) -> Dict[str, str]:
        """Detect project type (Python or Java) and return resource paths."""
        repo_path_obj = Path(repo_path)

        if (repo_path_obj / "application").exists():
            return {
                "type": "python",
                "resources_path": PYTHON_RESOURCES_PATH,
                "entities_path": f"{PYTHON_RESOURCES_PATH}/entity",
                "workflows_path": f"{PYTHON_RESOURCES_PATH}/workflow",
                "requirements_path": f"{PYTHON_RESOURCES_PATH}/functional_requirements",
            }

        if (repo_path_obj / "src" / "main").exists():
            return {
                "type": "java",
                "resources_path": JAVA_RESOURCES_PATH,
                "entities_path": f"{JAVA_RESOURCES_PATH}/entity",
                "workflows_path": f"{JAVA_RESOURCES_PATH}/workflow",
                "requirements_path": f"{JAVA_RESOURCES_PATH}/functional_requirements",
            }

        raise ValueError(f"Could not detect project type in {repo_path}")

    async def analyze_structure(
        self, repo_path: str, owner: str, name: str, branch: str
    ) -> Dict[str, Any]:
        """Perform full repository analysis."""
        paths = self.detect_project_type(repo_path)
        repo_path_obj = Path(repo_path)

        loop = asyncio.get_event_loop()

        entities = await loop.run_in_executor(
            None,
            self.scanner.scan_versioned_resources,
            repo_path_obj / paths["entities_path"],
            "entity",
            repo_path_obj,
        )

        workflows = await loop.run_in_executor(
            None,
            self.scanner.scan_versioned_resources,
            repo_path_obj / paths["workflows_path"],
            "workflow",
            repo_path_obj,
        )

        def _read_reqs():
            reqs = []
            req_dir = repo_path_obj / paths["requirements_path"]
            if req_dir.exists():
                for f in sorted(req_dir.glob("*")):
                    if f.is_file() and self.scanner.is_textual_file(f.name):
                        try:
                            with open(f, "r", encoding="utf-8") as file:
                                reqs.append(
                                    {
                                        "name": f.stem,
                                        "path": str(f.relative_to(repo_path_obj)),
                                        "content": file.read(),
                                    }
                                )
                        except Exception:
                            pass
            return reqs

        requirements = await loop.run_in_executor(None, _read_reqs)

        return {
            "project_type": paths["type"],
            "repository": {"owner": owner, "name": name, "branch": branch},
            "entities": entities,
            "workflows": workflows,
            "requirements": requirements,
        }

    async def _search_content(
        self, repo_path_obj: Path, pattern: str, file_pattern: str
    ) -> List[SearchMatch]:
        """Search for content matching pattern in files.

        Args:
            repo_path_obj: Repository path object
            pattern: Pattern to search for
            file_pattern: File name pattern

        Returns:
            List of SearchMatch objects
        """
        matches_list = []
        cmd = FIND_CONTENT_CMD.format(file_pattern=file_pattern, pattern=pattern)
        res = await self.fs_service.execute_unix_command(cmd, repo_path_obj)

        if not (res["success"] and res["stdout"]):
            return matches_list

        files = res["stdout"].strip().split("\n")
        for f in files:
            if not f:
                continue

            clean = f.lstrip("./") if f.startswith("./") else f
            grep_cmd = GREP_LINES_CMD.format(pattern=pattern, clean=clean)
            grep_res = await self.fs_service.execute_unix_command(
                grep_cmd, repo_path_obj
            )

            file_matches = []
            if grep_res["success"] and grep_res["stdout"]:
                for line in grep_res["stdout"].split("\n"):
                    if line.strip():
                        parts = line.split(":", 2)
                        if len(parts) >= 3:
                            try:
                                file_matches.append(
                                    {
                                        "line_number": int(parts[0]),
                                        "content": parts[2].strip(),
                                    }
                                )
                            except ValueError:
                                logger.debug(GREP_PARSE_ERROR)

            matches_list.append(SearchMatch(file=clean, matches=file_matches))

        return matches_list

    async def _search_filenames(
        self, repo_path_obj: Path, pattern: str
    ) -> List[SearchMatch]:
        """Search for files matching filename pattern.

        Args:
            repo_path_obj: Repository path object
            pattern: File name pattern

        Returns:
            List of SearchMatch objects
        """
        matches_list = []
        cmd = FIND_FILES_CMD.format(pattern=pattern)
        res = await self.fs_service.execute_unix_command(cmd, repo_path_obj)

        if not (res["success"] and res["stdout"]):
            return matches_list

        for f in res["stdout"].strip().split("\n"):
            if not f:
                continue

            clean = f.lstrip("./")
            try:
                size = (repo_path_obj / clean).stat().st_size
            except OSError:
                size = FILE_SIZE_DEFAULT

            matches_list.append(SearchMatch(file=clean, size=size, type="file"))

        return matches_list

    async def search_files(
        self, repo_path: str, pattern: str, file_pattern: str, search_type: str
    ) -> Dict[str, Any]:
        """Search repository files.

        Args:
            repo_path: Repository path
            pattern: Search pattern (regex or filename)
            file_pattern: File pattern to filter
            search_type: Type of search ("content" or "filename")

        Returns:
            Dictionary with search results and summary

        Example:
            >>> results = await service.search_files(
            ...     repo_path="/repo",
            ...     pattern="TODO",
            ...     file_pattern="*.py",
            ...     search_type="content"
            ... )
            >>> print(f"Found {results['summary']['total_matches']} matches")
        """
        repo_path_obj = Path(repo_path)

        # Step 1: Initialize results container
        matches = []

        # Step 2: Execute search based on type
        if search_type == SEARCH_TYPE_CONTENT:
            matches = await self._search_content(repo_path_obj, pattern, file_pattern)
        elif search_type == SEARCH_TYPE_FILENAME:
            matches = await self._search_filenames(repo_path_obj, pattern)

        # Step 3: Build summary
        summary = {"total_matches": len(matches), "search_completed": True}

        # Step 4: Return formatted results
        results = {
            "search_type": search_type,
            "search_pattern": pattern,
            "file_pattern": file_pattern,
            "repository_path": repo_path,
            "matches": [m.model_dump() for m in matches],
            "summary": summary,
        }

        logger.info(SEARCH_COMPLETED_LOG)
        return results

    async def validate_workflow(self, workflow_json: str, schema_path: Path) -> str:
        """Validate workflow JSON against schema."""
        import jsonschema

        if not schema_path.exists():
            return f"ERROR: Workflow schema not found at {schema_path}"

        with open(schema_path, "r") as f:
            schema_data = json.load(f)
        schema = schema_data.get("schema", schema_data)

        try:
            workflow = json.loads(workflow_json)
        except json.JSONDecodeError as e:
            return f"❌ Invalid JSON: {e}"

        try:
            if "workflows" in workflow and isinstance(workflow.get("workflows"), list):
                for wf in workflow["workflows"]:
                    jsonschema.validate(instance=wf, schema=schema)
            else:
                jsonschema.validate(instance=workflow, schema=schema)
            return "✅ Workflow validation passed!"
        except jsonschema.ValidationError as e:
            return f"❌ Validation failed: {e.message}"

    # Path helpers
    def get_entity_path(self, entity_name: str, version: int, project_type: str) -> str:
        if project_type == "python":
            return f"{PYTHON_RESOURCES_PATH}/entity/{entity_name}/version_{version}/{entity_name}.json"
        return f"{JAVA_RESOURCES_PATH}/entity/{entity_name}/version_{version}/{entity_name}.json"

    def get_workflow_path(
        self, workflow_name: str, project_type: str, version: int = 1
    ) -> str:
        folder = workflow_name.lower()
        if project_type == "python":
            return f"{PYTHON_RESOURCES_PATH}/workflow/{folder}/version_{version}/{workflow_name}.json"
        return f"{JAVA_RESOURCES_PATH}/workflow/{folder}/version_{version}/{workflow_name}.json"

    def get_requirements_path(self, requirements_name: str, project_type: str) -> str:
        if project_type == "python":
            return f"{PYTHON_RESOURCES_PATH}/functional_requirements/{requirements_name}.md"
        return f"{JAVA_RESOURCES_PATH}/functional_requirements/{requirements_name}.md"
