"""
GitHub Actions workflow operations.
"""

import asyncio
import io
import logging
import time
import zipfile
from typing import Optional, Dict, Any, List

# No config imports needed - all config is passed via constructor
from application.services.github.api.client import GitHubAPIClient
from application.services.github.models.types import WorkflowStatus, WorkflowConclusion, WorkflowRunInfo
from common.config.config import CLIENT_GIT_BRANCH

logger = logging.getLogger(__name__)


class WorkflowOperations:
    """Handles GitHub Actions workflow operations."""
    
    def __init__(self, client: Optional[GitHubAPIClient] = None):
        """Initialize workflow operations.
        
        Args:
            client: GitHub API client (creates new if not provided)
        """
        self.client = client or GitHubAPIClient()
    
    async def trigger_workflow(
        self,
        repository_name: str,
        workflow_id: str,
        ref: str = CLIENT_GIT_BRANCH,
        inputs: Optional[Dict[str, Any]] = None,
        owner: Optional[str] = None,
        tracker_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger a GitHub Actions workflow.
        
        Args:
            repository_name: Repository name
            workflow_id: Workflow ID or filename
            ref: Git reference (branch/tag)
            inputs: Workflow inputs
            owner: Repository owner (defaults to client owner)
            tracker_id: Unique tracker ID for monitoring
            
        Returns:
            Dict with run_id, tracker_id, and status
            
        Raises:
            Exception: If workflow trigger fails
        """
        owner = owner or self.client.owner
        tracker_id = tracker_id or f"tracker_{int(time.time())}"
        inputs = inputs or {}
        
        inputs["tracker_id"] = tracker_id
        
        dispatch_data = {
            "ref": ref,
            "inputs": inputs
        }
        
        response = await self.client.post(
            f"repos/{owner}/{repository_name}/actions/workflows/{workflow_id}/dispatches",
            data=dispatch_data
        )
        
        logger.info(f"Triggered workflow {workflow_id} in {owner}/{repository_name}")
        
        await self._wait_for_run_to_appear()
        
        run_id = await self._find_run_by_tracker_id(owner, repository_name, workflow_id, tracker_id)
        
        if not run_id:
            raise Exception(f"Workflow triggered but run not found with tracker_id: {tracker_id}")
        
        return {
            "status": "success",
            "message": f"Workflow '{workflow_id}' triggered successfully",
            "run_id": run_id,
            "tracker_id": tracker_id,
            "repository": f"{owner}/{repository_name}",
            "ref": ref
        }
    
    async def get_workflow_run_status(
        self,
        repository_name: str,
        run_id: int,
        owner: Optional[str] = None
    ) -> WorkflowRunInfo:
        """Get status of a workflow run.
        
        Args:
            repository_name: Repository name
            run_id: Workflow run ID
            owner: Repository owner (defaults to client owner)
            
        Returns:
            WorkflowRunInfo with run details
            
        Raises:
            Exception: If request fails
        """
        owner = owner or self.client.owner
        
        response = await self.client.get(
            f"repos/{owner}/{repository_name}/actions/runs/{run_id}"
        )
        
        if not response:
            raise Exception(f"Failed to get workflow run status for run_id: {run_id}")
        
        return WorkflowRunInfo(
            run_id=response["id"],
            workflow_id=response["workflow_id"],
            status=WorkflowStatus(response["status"]),
            conclusion=WorkflowConclusion(response["conclusion"]) if response.get("conclusion") else None,
            html_url=response["html_url"],
            created_at=response["created_at"],
            updated_at=response["updated_at"],
            head_branch=response["head_branch"],
            head_sha=response["head_sha"]
        )
    
    async def monitor_workflow_run(
        self,
        repository_name: str,
        run_id: int,
        owner: Optional[str] = None,
        poll_interval: int = 30,
        timeout_minutes: int = 60
    ) -> WorkflowRunInfo:
        """Monitor a workflow run until completion.
        
        Args:
            repository_name: Repository name
            run_id: Workflow run ID
            owner: Repository owner (defaults to client owner)
            poll_interval: Seconds between status checks
            timeout_minutes: Maximum time to wait
            
        Returns:
            Final WorkflowRunInfo
            
        Raises:
            Exception: If monitoring fails or times out
        """
        owner = owner or self.client.owner
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while True:
            run_info = await self.get_workflow_run_status(repository_name, run_id, owner)
            
            if run_info.status == WorkflowStatus.COMPLETED:
                logger.info(f"Workflow run {run_id} completed with conclusion: {run_info.conclusion}")
                return run_info
            
            elapsed = time.time() - start_time
            if elapsed > timeout_seconds:
                raise Exception(f"Workflow monitoring timed out after {timeout_minutes} minutes")
            
            logger.info(f"Workflow run {run_id} status: {run_info.status}, waiting {poll_interval}s...")
            await asyncio.sleep(poll_interval)
    
    async def run_workflow_and_wait(
        self,
        repository_name: str,
        workflow_id: str,
        ref: str = CLIENT_GIT_BRANCH,
        inputs: Optional[Dict[str, Any]] = None,
        owner: Optional[str] = None,
        timeout_minutes: int = 60
    ) -> WorkflowRunInfo:
        """Trigger workflow and wait for completion.
        
        Args:
            repository_name: Repository name
            workflow_id: Workflow ID or filename
            ref: Git reference
            inputs: Workflow inputs
            owner: Repository owner (defaults to client owner)
            timeout_minutes: Maximum time to wait
            
        Returns:
            Final WorkflowRunInfo
        """
        trigger_result = await self.trigger_workflow(
            repository_name, workflow_id, ref, inputs, owner
        )
        
        run_id = trigger_result["run_id"]
        
        return await self.monitor_workflow_run(
            repository_name, run_id, owner, timeout_minutes=timeout_minutes
        )
    
    async def get_workflow_logs(
        self,
        repository_name: str,
        run_id: int,
        owner: Optional[str] = None
    ) -> Dict[str, str]:
        """Get logs from a workflow run.
        
        Args:
            repository_name: Repository name
            run_id: Workflow run ID
            owner: Repository owner (defaults to client owner)
            
        Returns:
            Dict mapping job names to log content
        """
        owner = owner or self.client.owner
        
        logs_url = f"https://api.github.com/repos/{owner}/{repository_name}/actions/runs/{run_id}/logs"
        
        log_content = await self.client.download_file(logs_url)
        
        logs_dict = {}
        
        try:
            with zipfile.ZipFile(io.BytesIO(log_content)) as zip_file:
                for file_name in zip_file.namelist():
                    with zip_file.open(file_name) as log_file:
                        logs_dict[file_name] = log_file.read().decode('utf-8')
        except Exception as e:
            logger.error(f"Error extracting workflow logs: {e}")
            raise
        
        return logs_dict
    
    async def list_workflow_runs(
        self,
        repository_name: str,
        workflow_id: Optional[str] = None,
        owner: Optional[str] = None,
        status: Optional[WorkflowStatus] = None,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """List workflow runs.
        
        Args:
            repository_name: Repository name
            workflow_id: Filter by workflow ID
            owner: Repository owner (defaults to client owner)
            status: Filter by status
            per_page: Results per page
            
        Returns:
            List of workflow run data
        """
        owner = owner or self.client.owner
        
        params = {"per_page": per_page}
        if status:
            params["status"] = status.value
        
        if workflow_id:
            path = f"repos/{owner}/{repository_name}/actions/workflows/{workflow_id}/runs"
        else:
            path = f"repos/{owner}/{repository_name}/actions/runs"
        
        response = await self.client.get(path, params=params)
        
        return response.get("workflow_runs", []) if response else []
    
    async def cancel_workflow_run(
        self,
        repository_name: str,
        run_id: int,
        owner: Optional[str] = None
    ) -> bool:
        """Cancel a workflow run.
        
        Args:
            repository_name: Repository name
            run_id: Workflow run ID
            owner: Repository owner (defaults to client owner)
            
        Returns:
            True if successful
        """
        owner = owner or self.client.owner
        
        await self.client.post(
            f"repos/{owner}/{repository_name}/actions/runs/{run_id}/cancel"
        )
        
        logger.info(f"Cancelled workflow run {run_id}")
        return True

    async def _wait_for_run_to_appear(self, wait_seconds: int = 5):
        """Wait for workflow run to appear in GitHub.

        Args:
            wait_seconds: Seconds to wait
        """
        await asyncio.sleep(wait_seconds)

    async def _find_run_by_tracker_id(
        self,
        owner: str,
        repository_name: str,
        workflow_id: str,
        tracker_id: str,
        max_attempts: int = 10
    ) -> Optional[int]:
        """Find workflow run by tracker ID.

        Args:
            owner: Repository owner
            repository_name: Repository name
            workflow_id: Workflow ID
            tracker_id: Tracker ID to search for
            max_attempts: Maximum search attempts

        Returns:
            Run ID or None if not found
        """
        for attempt in range(max_attempts):
            runs = await self.list_workflow_runs(
                repository_name, workflow_id, owner, per_page=10
            )

            for run in runs:
                run_name = str(run.get("name", ""))
                commit_msg = str(run.get("head_commit", {}).get("message", ""))
                if tracker_id in run_name or tracker_id in commit_msg:
                    return run["id"]

            if attempt < max_attempts - 1:
                await asyncio.sleep(2)

        logger.warning(f"Could not find run with tracker_id: {tracker_id}")
        return None

