"""
Shared types and models for GitHub operations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from common.config.config import CLIENT_GIT_BRANCH


class GitHubPermission(str, Enum):
    PULL = "pull"
    PUSH = "push"
    ADMIN = "admin"
    MAINTAIN = "maintain"
    TRIAGE = "triage"


class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    WAITING = "waiting"


class WorkflowConclusion(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"
    NEUTRAL = "neutral"


class ProgrammingLanguage(str, Enum):
    PYTHON = "python"
    JAVA = "java"


@dataclass
class GitOperationResult:
    success: bool
    message: str
    had_changes: Optional[bool] = None
    diff: Optional[str] = None
    error: Optional[str] = None


@dataclass
class RepositoryInfo:
    name: str
    owner: str
    full_name: str
    url: str
    default_branch: str
    private: bool
    description: Optional[str] = None


@dataclass
class WorkflowRunInfo:
    run_id: int
    workflow_id: int
    status: WorkflowStatus
    conclusion: Optional[WorkflowConclusion]
    html_url: str
    created_at: str
    updated_at: str
    head_branch: str
    head_sha: str


@dataclass
class BranchInfo:
    name: str
    sha: str
    protected: bool
    repository_name: str


@dataclass
class CollaboratorInfo:
    username: str
    permission: GitHubPermission
    repository: str
    owner: str


@dataclass
class GitConfig:
    user_name: str
    user_email: str
    pull_rebase: bool = False


@dataclass
class CloneOptions:
    repository_name: str
    branch_id: str
    base_branch: str = CLIENT_GIT_BRANCH
    create_new_branch: bool = True


@dataclass
class PushOptions:
    branch_id: str
    repository_name: str
    commit_message: str
    files_to_add: Optional[List[str]] = None
    add_all: bool = False


@dataclass
class PullOptions:
    branch_id: str
    repository_name: str
    strategy: str = "recursive"
    strategy_option: str = "theirs"
