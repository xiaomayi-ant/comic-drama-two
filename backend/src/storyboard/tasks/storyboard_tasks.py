"""Celery 分镜生成任务"""

import logging

from src.core.celery_app import celery_app
from src.core.database import get_database
from src.storyboard.services import storyboard_service, task_service

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.generate_storyboard")
def generate_storyboard_task(task_id: str, episode_id: int) -> None:
    """验证 episode 存在，更新进度，返回分镜数量。"""
    db = get_database()
    session = db.get_session()

    try:
        task_service.update_status(session, task_id, "processing", 20, "开始生成分镜...")

        episode = storyboard_service.get_episode_or_raise(session, episode_id)

        task_service.update_status(session, task_id, "processing", 60, "分镜解析完成，正在保存...")

        storyboards = storyboard_service.list_storyboards(session, episode_id)
        count = len(storyboards)

        task_service.update_result(session, task_id, {
            "count": count,
            "total_duration": episode.duration,
            "episode_id": episode_id,
        })
        logger.info("generate_storyboard completed: episode=%d, storyboards=%d", episode_id, count)
    except Exception as exc:
        task_service.update_error(session, task_id, str(exc))
        logger.error("generate_storyboard failed: %s", exc)
    finally:
        session.close()
