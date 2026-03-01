"""Celery 应用实例"""

import logging

from celery import Celery

from src.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "storyboard_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "src.storyboard.tasks.storyboard_tasks",
        "src.storyboard.tasks.video_tasks",
        "src.storyboard.tasks.aigc_tasks",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_always_eager=settings.celery_task_always_eager,
)
