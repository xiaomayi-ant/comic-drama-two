"""通义万相 AIGC 客户端：文生图 + 文生视频 + OSS 转存"""

import logging
import time
import uuid

import requests
from dashscope import ImageSynthesis, VideoSynthesis

from src.core.config import settings
from src.retrieval.oss_manager import oss_manager

logger = logging.getLogger(__name__)


def generate_image(prompt: str) -> str:
    """文生图 → 转存 OSS → 返回 oss_key。"""
    model = settings.aigc_image_model
    size = settings.aigc_image_size
    logger.info("generate_image start: model=%s size=%s prompt=%.60s", model, size, prompt)

    resp = ImageSynthesis.call(
        model=model,
        prompt=prompt,
        n=1,
        size=size,
    )

    if resp.status_code != 200:
        raise RuntimeError(
            "ImageSynthesis failed: code=%s msg=%s" % (resp.status_code, resp.message)
        )

    image_url = resp.output.results[0].url
    logger.info("generate_image success, dashscope url=%.120s", image_url)

    oss_key = _transfer_to_oss(image_url, prefix="aigc/images/", suffix=".png")
    return oss_key


def generate_video(prompt: str, image_url: str | None = None) -> str:
    """文生视频（异步轮询） → 转存 OSS → 返回 oss_key。

    使用 wan2.5-t2v-preview 时为纯文生视频（有声），image_url 被忽略。
    如果配置的模型是 i2v 系列，则传入 image_url 做图生视频。
    """
    model = settings.aigc_video_model
    video_size = settings.aigc_image_size  # 复用图片尺寸设置（1280*720）
    poll_interval = settings.aigc_video_poll_interval
    max_wait = settings.aigc_video_max_wait

    is_t2v = "t2v" in model
    logger.info(
        "generate_video start: model=%s mode=%s size=%s prompt=%.80s",
        model, "t2v" if is_t2v else "i2v", video_size, prompt,
    )

    call_kwargs = dict(model=model, prompt=prompt, size=video_size)
    if not is_t2v and image_url:
        call_kwargs["img_url"] = image_url

    resp = VideoSynthesis.async_call(**call_kwargs)

    if resp.status_code != 200:
        raise RuntimeError(
            "VideoSynthesis.async_call failed: code=%s msg=%s"
            % (resp.status_code, resp.message)
        )

    task_id = resp.output.task_id
    logger.info("generate_video submitted, task_id=%s", task_id)

    elapsed = 0
    while elapsed < max_wait:
        time.sleep(poll_interval)
        elapsed += poll_interval

        status_resp = VideoSynthesis.fetch(task=task_id)
        task_status = status_resp.output.task_status

        if task_status == "SUCCEEDED":
            video_url = status_resp.output.video_url
            logger.info("generate_video succeeded, dashscope url=%.120s", video_url)
            oss_key = _transfer_to_oss(video_url, prefix="aigc/videos/", suffix=".mp4")
            return oss_key

        if task_status == "FAILED":
            raise RuntimeError(
                "VideoSynthesis task %s failed: %s"
                % (task_id, getattr(status_resp.output, "message", "unknown"))
            )

        logger.debug("generate_video polling: task=%s status=%s elapsed=%ds", task_id, task_status, elapsed)

    raise TimeoutError("VideoSynthesis task %s timed out after %ds" % (task_id, max_wait))


def _transfer_to_oss(source_url: str, prefix: str, suffix: str) -> str:
    """下载 DashScope 临时 URL 并转存到阿里云 OSS。"""
    oss_key = "%s%s%s" % (prefix, uuid.uuid4().hex, suffix)

    resp = requests.get(source_url, timeout=120)
    resp.raise_for_status()

    oss_manager.bucket.put_object(oss_key, resp.content)
    logger.info("transfer_to_oss done: %s (%d bytes)", oss_key, len(resp.content))

    return oss_key
