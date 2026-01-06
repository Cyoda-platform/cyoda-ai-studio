
● Refactoring Plan: application/agents/github/tools.py

Critical Constraints

🔴 REGRESSION PREVENTION IS PRIORITY #1

1. ✅ All code changes ONLY in application/agents/github/
2. ✅ Run tests/unit/agents/github/test_github_tools.py after EVERY step
3. ✅ Maintain 81% coverage (1254/1557 lines) - DO NOT DROP
4. ✅ All 258 tests MUST pass at every step
5. ✅ Backward compatible imports throughout migration

  ---
Current State

application/agents/github/
├── agent.py           (200 lines)
├── prompts.py         (100 lines)
└── tools.py           (3719 lines) ❌ MONOLITHIC

tests/unit/agents/github/
└── test_github_tools.py (5330 lines, 258 tests, 81% coverage) ✅

  ---
Target State

application/agents/github/
├── agent.py           (200 lines)
├── prompts.py         (100 lines)
├── tools.py           (~90 lines) ✅ THIN REGISTRY
└── tool_definitions/
├── common/
├── repository/
├── git/
├── analysis/
├── search/
├── codegen/
└── command/

  ---
Phased Migration Strategy

Phase 0: Preparation (No Code Changes)
# Before starting, identify which functions can be safely moved
pytest tests/unit/agents/github/test_github_tools.py --cov=application/agents/github/tools --cov-report=term-missing > coverage_baseline.txt

# Create safe migration list based on coverage
# Phase 1-3: Only move functions with >85% coverage
# Phase 4-5: Add tests for <75% coverage functions before moving them
Goal: Set up safety infrastructure

Step 0.1: Create Test Runner Script

# Create run_tests.sh in application/agents/github/
cat > application/agents/github/run_tests.sh << 'EOF'
#!/bin/bash
echo "Running GitHub agent tests..."
python -m pytest tests/unit/agents/github/test_github_tools.py \
--cov=application.agents.github.tools \
--cov-report=term \
--no-cov-on-fail \
-v
EOF

chmod +x application/agents/github/run_tests.sh

Verify:
./application/agents/github/run_tests.sh
# Expected: 258 passed, 81% coverage

Step 0.2: Create Baseline Coverage Report

python -m pytest tests/unit/agents/github/test_github_tools.py \
--cov=application.agents.github.tools \
--cov-report=html:coverage_baseline \
--cov-report=term > baseline_coverage.txt

Success Criteria:
- ✅ All 258 tests pass
- ✅ Coverage: 81% (1254/1557 lines)
- ✅ Baseline saved for comparison

  ---
Phase 1: Create Directory Structure (No Functional Changes)

Goal: Set up directories without moving any code yet

Step 1.1: Create tool_definitions/ Structure

cd application/agents/github/

# Create directory structure
mkdir -p tool_definitions/common/{models,formatters,utils,constants}
mkdir -p tool_definitions/repository/{tools,helpers}
mkdir -p tool_definitions/git/{tools,helpers}
mkdir -p tool_definitions/analysis/{tools,helpers}
mkdir -p tool_definitions/search/helpers
mkdir -p tool_definitions/codegen/{tools,helpers}
mkdir -p tool_definitions/command/helpers

# Create all __init__.py files
touch tool_definitions/__init__.py
touch tool_definitions/common/__init__.py
touch tool_definitions/common/{models,formatters,utils,constants}/__init__.py
touch tool_definitions/{repository,git,analysis,search,codegen,command}/__init__.py
touch tool_definitions/repository/{tools,helpers}/__init__.py
touch tool_definitions/git/{tools,helpers}/__init__.py
touch tool_definitions/analysis/{tools,helpers}/__init__.py
touch tool_definitions/search/helpers/__init__.py
touch tool_definitions/codegen/{tools,helpers}/__init__.py
touch tool_definitions/command/helpers/__init__.py

Test:
./run_tests.sh

Success Criteria:
- ✅ All 258 tests still pass
- ✅ Coverage unchanged (81%)
- ✅ Directory structure created

Step 1.2: Create STRUCTURE.md Documentation

cat > tool_definitions/STRUCTURE.md << 'EOF'
# GitHub Agent Tools - Folder Structure

[Document structure following environment agent pattern]
EOF

Test:
./run_tests.sh

Success Criteria:
- ✅ All 258 tests still pass

  ---
Phase 2: Extract Constants (First Code Move)

Goal: Move magic strings to constants without changing behavior

Step 2.1: Create Constants File

File: tool_definitions/common/constants/constants.py

"""Named constants for GitHub agent tools."""

# File extensions
JSON_EXT = ".json"
MD_EXT = ".md"
PY_EXT = ".py"
JAVA_EXT = ".java"

# Project types
PYTHON = "python"
JAVA = "java"

# Directory names
ENTITY_DIR = "entity"
WORKFLOW_DIR = "workflow"
PROCESSOR_DIR = "processor"
ROUTE_DIR = "route"
FUNCTIONAL_REQUIREMENTS_DIR = "functional_requirements"
VERSION_PREFIX = "version_"

# Git commands
GIT_ADD = "add"
GIT_COMMIT = "commit"
GIT_PUSH = "push"
GIT_PULL = "pull"
GIT_STATUS = "status"
GIT_DIFF = "diff"

# Search types
SEARCH_CONTENT = "content"
SEARCH_FILENAME = "filename"
SEARCH_STRUCTURE = "structure"
SEARCH_FILETYPE = "filetype"

# Status values
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_RUNNING = "running"

# Special markers
STOP_ON_ERROR = "[STOP_ON_ERROR]"  # Already exists in tools.py

Test:
./run_tests.sh

Success Criteria:
- ✅ All 258 tests pass
- ✅ File created, but not used yet (no imports)

Step 2.2: Create Config File

File: tool_definitions/common/constants/config.py

"""Centralized configuration from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

@dataclass
class GitHubToolsConfig:
"""Configuration for GitHub agent tools."""
python_resources_path: str
java_resources_path: str
build_mode: str
augment_cli_script: str
github_public_repo_installation_id: str
cli_provider: str
augment_model: str
claude_model: str
gemini_model: str
repository_owner: str

      @classmethod
      def from_env(cls) -> GitHubToolsConfig:
          return cls(
              python_resources_path=os.getenv("PYTHON_RESOURCES_PATH", "application/resources"),
              java_resources_path=os.getenv("JAVA_RESOURCES_PATH", "src/main/resources"),
              build_mode=os.getenv("BUILD_MODE", "development"),
              augment_cli_script=os.getenv("AUGMENT_CLI_SCRIPT", "scripts/augment_cli.sh"),
              github_public_repo_installation_id=os.getenv("GITHUB_PUBLIC_REPO_INSTALLATION_ID", ""),
              cli_provider=os.getenv("CLI_PROVIDER", "augment"),
              augment_model=os.getenv("AUGMENT_MODEL", "haiku4.5"),
              claude_model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4"),
              gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp"),
              repository_owner=os.getenv("REPOSITORY_OWNER", "Cyoda-platform"),
          )

# Global configuration instance
config = GitHubToolsConfig.from_env()

Update: tool_definitions/common/constants/__init__.py

"""Constants and configuration."""

from .constants import *
from .config import config, GitHubToolsConfig

__all__ = [
# Config
"config",
"GitHubToolsConfig",
# Constants
"JSON_EXT",
"MD_EXT",
"PY_EXT",
"JAVA_EXT",
"PYTHON",
"JAVA",
"ENTITY_DIR",
"WORKFLOW_DIR",
"PROCESSOR_DIR",
"ROUTE_DIR",
"FUNCTIONAL_REQUIREMENTS_DIR",
"VERSION_PREFIX",
"GIT_ADD",
"GIT_COMMIT",
"GIT_PUSH",
"GIT_PULL",
"GIT_STATUS",
"GIT_DIFF",
"SEARCH_CONTENT",
"SEARCH_FILENAME",
"SEARCH_STRUCTURE",
"SEARCH_FILETYPE",
"STATUS_SUCCESS",
"STATUS_FAILED",
"STATUS_RUNNING",
"STOP_ON_ERROR",
]

Test:
./run_tests.sh

Success Criteria:
- ✅ All 258 tests pass
- ✅ Constants created but not imported yet

Step 2.3: Import STOP_ON_ERROR from Constants (Test Import)

Edit: tools.py (line 16-17)

Before:
# Stop on error marker (signals agent to halt execution)
STOP_ON_ERROR = "[STOP_ON_ERROR]"

After:
# Import STOP_ON_ERROR from constants (backward compatible)
from .tool_definitions.common.constants import STOP_ON_ERROR

Test:
./run_tests.sh

Success Criteria:
- ✅ All 258 tests pass
- ✅ First import working
- ✅ No behavior change

If tests fail: Revert immediately
git checkout tools.py

  ---
Phase 3: Extract First Helper Function (Minimal Risk)

Goal: Move one small, well-tested helper to verify pattern works

Step 3.1: Create First Helper File

File: tool_definitions/common/utils/validation.py

"""Input validation utilities."""

from __future__ import annotations

import re
from typing import Optional

def _validate_command_security(command: str, repository_path: str) -> dict:
"""Validate command for security concerns.

      This is extracted from tools.py with NO changes to logic.
      """
      # Copy EXACT code from tools.py _validate_command_security
      # DO NOT modify behavior
      # ... (exact copy)

Test:
./run_tests.sh

Success Criteria:
- ✅ All 258 tests pass (helper not used yet)

Step 3.2: Update tools.py to Import Helper

Edit: tools.py - Add import at top

# After other imports
from .tool_definitions.common.utils.validation import _validate_command_security

Comment out original _validate_command_security function:

# MOVED TO: tool_definitions/common/utils/validation.py
# def _validate_command_security(command: str, repository_path: str) -> dict:
#     """Validate command for security concerns."""
#     # ... original code commented out ...

Test:
./run_tests.sh

Success Criteria:
- ✅ All 258 tests pass
- ✅ Helper imported successfully
- ✅ Function behavior identical

If tests fail:
git checkout tools.py
git checkout tool_definitions/common/utils/validation.py

  ---
Phase 4: Incremental Function Migration (One at a Time)

Strategy: Move functions one at a time, test after EACH move

Step 4.1: Create Migration Tracking

File: tool_definitions/MIGRATION_STATUS.md

# Migration Status

## Completed
- [x] STOP_ON_ERROR constant
- [x] _validate_command_security

## In Progress
- [ ] 

## Pending
- [ ] _cleanup_temp_files
- [ ] _is_process_running
- [ ] _detect_project_type
- [ ] _scan_versioned_resources
- [ ] ... (list all functions)

Step 4.2: Migration Order (Priority by Risk)

Low Risk (Move First):
1. ✅ _validate_command_security (DONE)
2. _cleanup_temp_files - Simple, no dependencies
3. _is_process_running - Simple helper
4. _detect_project_type - Well-tested

Medium Risk (Move Second):
5. _scan_versioned_resources - More complex
6. _get_cli_config - Has config dependencies
7. Format functions - Multiple small functions

High Risk (Move Last):
8. _commit_and_push_changes - Complex, many dependencies
9. _monitor_cli_process - Very complex, async
10. analyze_repository_structure - Large function

Step 4.3: Template for Each Function Move

For EACH function:

# 1. Create helper file
# tool_definitions/{domain}/helpers/_function_name.py

# 2. Copy function EXACTLY (no changes)

# 3. Run tests
./run_tests.sh

# 4. Import in tools.py
# from .tool_definitions.{domain}.helpers._function_name import function_name

# 5. Comment out original

# 6. Run tests again
./run_tests.sh

# 7. If pass: commit, if fail: revert
git add -A
git commit -m "Move {function_name} to tool_definitions/{domain}"
# OR
git checkout .

  ---
Phase 5: Extract Tool Functions (Most Critical)

Goal: Move public tool functions to tool_definitions

Step 5.1: Move Simple Tool First (Test Pattern)

Start with: generate_branch_uuid - Simplest tool

File: tool_definitions/git/tools/generate_branch_tool.py

"""Tool for generating unique branch names."""

from __future__ import annotations

import uuid
from google.adk.tools.tool_context import ToolContext

async def generate_branch_uuid(tool_context: ToolContext) -> str:
"""Generate a unique branch name with UUID suffix.

      (EXACT copy from tools.py - NO CHANGES)
      """
      # ... exact code ...

Update: tool_definitions/git/tools/__init__.py

"""Git operation tools."""

from .generate_branch_tool import generate_branch_uuid

__all__ = ["generate_branch_uuid"]

Update: tool_definitions/git/__init__.py

"""Git operations."""

from .tools import generate_branch_uuid

__all__ = ["generate_branch_uuid"]

Update: tools.py - Add import

# Git tools
from .tool_definitions.git import generate_branch_uuid

Comment out original in tools.py

Test:
./run_tests.sh

Success Criteria:
- ✅ All 258 tests pass
- ✅ Tool moved successfully
- ✅ First tool pattern verified

If success: Continue with other tools
If failure: Revert and investigate

Step 5.2: Tool Migration Order

Simple Tools (Move First):
1. ✅ generate_branch_uuid
2. read_file_from_repository
3. get_repository_diff

Medium Complexity:
4. clone_repository
5. pull_repository_changes
6. save_file_to_repository
7. execute_unix_command

Complex Tools (Move Last):
8. search_repository_files
9. commit_and_push_changes
10. analyze_repository_structure
11. analyze_repository_structure_agentic
12. generate_code_with_cli
13. generate_application

  ---
Phase 6: Final Registry Creation (After All Functions Moved)

Goal: Create thin tools.py registry

Step 6.1: Create New tools.py

Only after ALL functions moved:

"""Tools for the GitHub Agent.

This module serves as a Tool Registry that imports and re-exports tool implementations
from the tool_definitions/ package. Each tool is implemented in its own file for better
modularity and maintainability.
"""

from __future__ import annotations

import logging
from google.adk.tools.tool_context import ToolContext

# Make ToolContext available for type hint evaluation
__all__ = ["ToolContext"]

# Repository tools
from .tool_definitions.repository import (
clone_repository,
pull_repository_changes,
read_file_from_repository,
save_file_to_repository,
)

# Git tools
from .tool_definitions.git import (
commit_and_push_changes,
get_repository_diff,
generate_branch_uuid,
)

# Analysis tools
from .tool_definitions.analysis import (
analyze_repository_structure,
analyze_repository_structure_agentic,
)

# Search tools
from .tool_definitions.search import search_repository_files

# Code generation tools
from .tool_definitions.codegen import (
generate_code_with_cli,
generate_application,
)

# Command execution tools
from .tool_definitions.command import execute_unix_command

logger = logging.getLogger(__name__)

# All tool implementations have been migrated to individual files in tool_definitions/
# This module now serves purely as a tool registry that imports and re-exports tools

Test:
./run_tests.sh

Success Criteria:
- ✅ All 258 tests pass
- ✅ tools.py < 100 lines
- ✅ All imports working

  ---
Safety Mechanisms

After Every Step

# 1. Run tests
./run_tests.sh

# 2. Check coverage
python -m pytest tests/unit/agents/github/test_github_tools.py \
--cov=application.agents.github.tools \
--cov-report=term | grep "TOTAL"

# Expected: 81% (must not drop)

# 3. If tests fail
git status
git diff
git checkout .  # Revert everything

Rollback Points

Create git commit after each successful phase:

git add application/agents/github/
git commit -m "Phase X.Y: [description] - All tests passing"

If something breaks:
git log --oneline  # See commits
git reset --hard HEAD~1  # Go back one commit
./run_tests.sh  # Verify tests pass again

  ---
Testing Frequency

| Phase   | Test Frequency                         |
  |---------|----------------------------------------|
| Phase 0 | Once (baseline)                        |
| Phase 1 | After directory creation               |
| Phase 2 | After EACH constant/config file        |
| Phase 3 | After EACH helper function moved       |
| Phase 4 | After EACH function moved (critical!)  |
| Phase 5 | After EACH tool moved (most critical!) |
| Phase 6 | After creating new registry            |

Total test runs: ~50-60 times minimum

  ---
Success Metrics

Must Maintain Throughout

- ✅ 258 tests passing
- ✅ 81% coverage (1254/1557 lines)
- ✅ No new warnings or errors
- ✅ Same execution time for tests

Final State

- ✅ tools.py < 100 lines
- ✅ All functions in tool_definitions/
- ✅ Proper domain organization
- ✅ All tests still passing
- ✅ Coverage maintained or improved

  ---
Estimated Timeline

| Phase   | Time       | Risk Level                 |
  |---------|------------|----------------------------|
| Phase 0 | 30 min     | None                       |
| Phase 1 | 1 hour     | Low                        |
| Phase 2 | 2 hours    | Low-Medium                 |
| Phase 3 | 2 hours    | Medium                     |
| Phase 4 | 8-12 hours | High (many functions)      |
| Phase 5 | 8-12 hours | Very High (critical tools) |
| Phase 6 | 2 hours    | Medium                     |
| Total   | 3-4 days   | Requires caution           |

Recommendation: Move 3-5 functions per day, test thoroughly