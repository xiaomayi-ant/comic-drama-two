"""Celery AIGC 生成任务：文生图 + 文生视频"""

import logging

from src.core.celery_app import celery_app
from src.core.database import get_database
from src.retrieval.oss_manager import oss_manager
from src.storyboard.services import storyboard_service, task_service
from src.storyboard.services.aigc_client import generate_image, generate_video

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.generate_aigc", bind=True, max_retries=1)
def generate_aigc_task(self, task_id: str, episode_id: int) -> None:
    """为 episode 下每条分镜生成图片和视频，写入 DB。"""
    db = get_database()
    session = db.get_session()

    try:
        task_service.update_status(session, task_id, "processing", 5, "正在查询分镜数据...")

        storyboards = storyboard_service.list_storyboards(session, episode_id)
        total = len(storyboards)
        if total == 0:
            task_service.update_result(session, task_id, {
                "episode_id": episode_id,
                "generated": 0,
                "message": "该剧集没有分镜数据",
            })
            return

        success_count = 0
        fail_count = 0

        for idx, sb in enumerate(storyboards):
            progress = 5 + int((idx / total) * 90)
            task_service.update_status(
                session, task_id, "processing", progress,
                "正在生成第 %d/%d 条分镜 AIGC..." % (idx + 1, total),
            )

            # --- 文生图 ---
            try:
                if sb.image_prompt:
                    oss_key = generate_image(sb.image_prompt)
                    sb.image_url = oss_key
                    session.commit()
                    logger.info("storyboard %d image done: %s", sb.storyboard_number, oss_key)
                else:
                    logger.warning("storyboard %d has no image_prompt, skipping image generation", sb.storyboard_number)
            except Exception as exc:
                fail_count += 1
                logger.error("storyboard %d image generation failed: %s", sb.storyboard_number, exc)
                continue  # 跳过视频生成，继续下一条

            # --- 文生视频 ---
            try:
                if sb.video_prompt:
                    image_full_url = None
                    if sb.image_url:
                        image_full_url = oss_manager.get_url(sb.image_url, expires=3600)
                    video_oss_key = generate_video(prompt=sb.video_prompt, image_url=image_full_url)
                    sb.video_url = video_oss_key
                    session.commit()
                    logger.info("storyboard %d video done: %s", sb.storyboard_number, video_oss_key)
                else:
                    logger.warning("storyboard %d has no video_prompt, skipping video generation", sb.storyboard_number)
            except Exception as exc:
                fail_count += 1
                logger.error("storyboard %d video generation failed: %s", sb.storyboard_number, exc)
                continue

            success_count += 1

        task_service.update_result(session, task_id, {
            "episode_id": episode_id,
            "total": total,
            "success": success_count,
            "failed": fail_count,
        })
        logger.info(
            "generate_aigc completed: episode=%d total=%d success=%d failed=%d",
            episode_id, total, success_count, fail_count,
        )
    except Exception as exc:
        task_service.update_error(session, task_id, str(exc))
        logger.error("generate_aigc failed: %s", exc)
    finally:
        session.close()
