"""Episode / Storyboard 查询服务"""

import logging

from sqlalchemy.orm import Session

from src.core.database import EpisodeDB, StoryboardDB

logger = logging.getLogger(__name__)


def get_episode_or_raise(session: Session, episode_id: int) -> EpisodeDB:
    """按 ID 查询 Episode，不存在则抛出 ValueError。"""
    episode = session.get(EpisodeDB, episode_id)
    if not episode:
        raise ValueError(f"episode {episode_id} not found")
    return episode


def get_episode_by_thread(session: Session, thread_id: str) -> EpisodeDB | None:
    """按 thread_id 查询最新 Episode。"""
    return (
        session.query(EpisodeDB)
        .filter(EpisodeDB.thread_id == thread_id)
        .order_by(EpisodeDB.created_at.desc())
        .first()
    )


def list_storyboards(session: Session, episode_id: int) -> list[StoryboardDB]:
    """按 storyboard_number 排序返回分镜列表。"""
    return (
        session.query(StoryboardDB)
        .filter(StoryboardDB.episode_id == episode_id)
        .order_by(StoryboardDB.storyboard_number)
        .all()
    )
