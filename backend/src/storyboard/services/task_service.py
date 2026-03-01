"""AsyncTask CRUD 服务"""

import json
import logging
import uuid

from sqlalchemy.orm import Session

from src.core.database import AsyncTaskDB

logger = logging.getLogger(__name__)


def create_task(session: Session, task_type: str, resource_id: str) -> AsyncTaskDB:
    """创建一条 pending 状态的异步任务。"""
    task = AsyncTaskDB(
        id=str(uuid.uuid4()),
        type=task_type,
        status="pending",
        progress=0,
        resource_id=resource_id,
        message="",
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    logger.info("task created: %s type=%s resource=%s", task.id, task_type, resource_id)
    return task


def update_status(session: Session, task_id: str, status: str, progress: int, message: str) -> None:
    """更新任务状态/进度/消息。"""
    task = session.get(AsyncTaskDB, task_id)
    if not task:
        logger.warning("task %s not found for status update", task_id)
        return
    task.status = status
    task.progress = progress
    task.message = message
    session.commit()


def update_error(session: Session, task_id: str, error_message: str) -> None:
    """标记任务失败。"""
    task = session.get(AsyncTaskDB, task_id)
    if not task:
        return
    task.status = "failed"
    task.progress = 0
    task.error = error_message
    session.commit()
    logger.error("task %s failed: %s", task_id, error_message)


def update_result(session: Session, task_id: str, result_dict: dict) -> None:
    """标记任务完成并保存结果。"""
    task = session.get(AsyncTaskDB, task_id)
    if not task:
        return
    task.status = "completed"
    task.progress = 100
    task.result = json.dumps(result_dict, ensure_ascii=False)
    session.commit()
    logger.info("task %s completed", task_id)
