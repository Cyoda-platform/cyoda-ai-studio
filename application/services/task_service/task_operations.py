"""Task creation and retrieval operations."""

import logging
from typing import Any, Dict, Optional

from application.entity.background_task import BackgroundTask
from common.service.entity_service import EntityService

logger = logging.getLogger(__name__)


def _build_task_entity(
    user_id: str,
    task_type: str,
    name: str,
    description: str,
    branch_name: Optional[str],
    language: Optional[str],
    user_request: Optional[str],
    conversation_id: Optional[str],
    repository_path: Optional[str],
    repository_type: Optional[str],
    repository_url: Optional[str],
    build_id: Optional[str],
    namespace: Optional[str],
    env_url: Optional[str],
    kwargs: dict,
) -> BackgroundTask:
    """Build BackgroundTask entity with all parameters."""
    task = BackgroundTask(
        user_id=user_id,
        task_type=task_type,
        name=name,
        description=description,
        status="pending",
        progress=0,
        branch_name=branch_name,
        language=language,
        user_request=user_request,
        conversation_id=conversation_id,
        repository_path=repository_path,
        repository_type=repository_type,
        repository_url=repository_url,
        build_id=build_id,
        namespace=namespace,
        env_url=env_url,
    )

    if kwargs:
        task.workflow_cache.update(kwargs)

    return task


async def create_task(
    entity_service: EntityService,
    user_id: str,
    task_type: str,
    name: str,
    description: str = "",
    branch_name: Optional[str] = None,
    language: Optional[str] = None,
    user_request: Optional[str] = None,
    conversation_id: Optional[str] = None,
    repository_path: Optional[str] = None,
    repository_type: Optional[str] = None,
    repository_url: Optional[str] = None,
    build_id: Optional[str] = None,
    namespace: Optional[str] = None,
    env_url: Optional[str] = None,
    **kwargs: Any,
) -> BackgroundTask:
    """Create a new background task."""
    task = _build_task_entity(
        user_id=user_id,
        task_type=task_type,
        name=name,
        description=description,
        branch_name=branch_name,
        language=language,
        user_request=user_request,
        conversation_id=conversation_id,
        repository_path=repository_path,
        repository_type=repository_type,
        repository_url=repository_url,
        build_id=build_id,
        namespace=namespace,
        env_url=env_url,
        kwargs=kwargs,
    )

    entity_data = task.model_dump(by_alias=False)
    response = await entity_service.save(
        entity=entity_data,
        entity_class=BackgroundTask.ENTITY_NAME,
        entity_version=str(BackgroundTask.ENTITY_VERSION),
    )

    saved_data = response.data if hasattr(response, "data") else response
    created_task = BackgroundTask(**saved_data)

    logger.info(
        f"✅ Created background task {created_task.technical_id} "
        f"(type={task_type}, user={user_id})"
    )

    return created_task


async def get_task(
    entity_service: EntityService, task_id: str
) -> Optional[BackgroundTask]:
    """Get a task by technical ID."""
    try:
        response = await entity_service.get_by_id(
            entity_id=task_id,
            entity_class=BackgroundTask.ENTITY_NAME,
            entity_version=str(BackgroundTask.ENTITY_VERSION),
        )

        if response and hasattr(response, "data"):
            return BackgroundTask(**response.data)
        elif response:
            return BackgroundTask(**response)
        return None
    except Exception as e:
        from common.exception import is_not_found

        if is_not_found(e):
            return None
        raise


__all__ = [
    "_build_task_entity",
    "create_task",
    "get_task",
]
