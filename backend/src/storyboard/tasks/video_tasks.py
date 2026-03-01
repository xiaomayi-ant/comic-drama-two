"""Celery 视频合成任务（含重试）"""

import logging

from src.core.celery_app import celery_app
from src.core.database import get_database
from src.storyboard.services import task_service
from src.storyboard.utils.ffmpeg_runner import TransitionConfig, VideoClip, merge_videos

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.merge_episode_videos", bind=True, max_retries=2)
def merge_episode_videos_task(self, task_id: str, clips: list[dict], output_file: str) -> None:
    """合并视频片段，支持自动重试。"""
    db = get_database()
    session = db.get_session()

    try:
        task_service.update_status(session, task_id, "processing", 20, "开始准备视频片段...")

        clip_models: list[VideoClip] = []
        for item in clips:
            transition_raw = item.get("transition")
            transition = None
            if transition_raw:
                transition = TransitionConfig(
                    type=transition_raw.get("type", "none"),
                    duration=float(transition_raw.get("duration", 1.0)),
                )
            clip_models.append(
                VideoClip(
                    url=item["video_url"],
                    duration=float(item.get("duration", 0.0)),
                    start_time=float(item.get("start_time", 0.0)),
                    end_time=float(item.get("end_time", 0.0)),
                    transition=transition,
                )
            )

        task_service.update_status(session, task_id, "processing", 60, "开始FFmpeg合成...")
        merge_result = merge_videos(clip_models, output_file)

        task_service.update_result(session, task_id, {
            "merged_path": merge_result.output_path,
            "output_duration": merge_result.output_duration,
            "clips_count": len(clip_models),
            "retries": self.request.retries,
            "clip_details": [
                {
                    "index": d.index,
                    "source_url": d.source_url,
                    "source_duration": d.source_duration,
                    "requested_start": d.requested_start,
                    "requested_end": d.requested_end,
                    "applied_start": d.applied_start,
                    "applied_end": d.applied_end,
                    "final_duration": d.final_duration,
                    "transition_type": d.transition_type,
                    "transition_duration": d.transition_duration,
                }
                for d in merge_result.clips
            ],
        })
        logger.info("merge_episode_videos completed: %s", output_file)
    except Exception as exc:
        if self.request.retries < self.max_retries:
            task_service.update_status(
                session, task_id, "processing", 70,
                f"合成失败，准备重试({self.request.retries + 1}/{self.max_retries})",
            )
            raise self.retry(exc=exc, countdown=20)
        task_service.update_error(session, task_id, str(exc))
        logger.error("merge_episode_videos failed after retries: %s", exc)
    finally:
        session.close()
