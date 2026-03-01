"""FFmpeg 视频合并管线（从 storyboard 项目移植）"""

import logging
import shutil
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

FFMPEG_TIMEOUT_SECONDS = 60 * 20
FFPROBE_TIMEOUT_SECONDS = 20
DEFAULT_WIDTH = 1920
DEFAULT_HEIGHT = 1080
DEFAULT_CLIP_DURATION = 5.0
ALLOWED_TRANSITION_TYPES = {
    "none",
    "fade",
    "dissolve",
    "wipeleft",
    "wiperight",
    "slideleft",
    "slideright",
}


@dataclass
class TransitionConfig:
    type: str = "none"
    duration: float = 1.0


@dataclass
class VideoClip:
    url: str
    duration: float = 0.0
    start_time: float = 0.0
    end_time: float = 0.0
    transition: TransitionConfig | None = None


@dataclass
class ClipProcessDetail:
    index: int
    source_url: str
    source_duration: float
    requested_start: float
    requested_end: float
    applied_start: float
    applied_end: float
    final_duration: float
    transition_type: str
    transition_duration: float


@dataclass
class MergeResult:
    output_path: str
    output_duration: float
    clips: list[ClipProcessDetail]


@dataclass
class PrecheckClipDetail:
    index: int
    source_url: str
    source_duration: float
    requested_start: float
    requested_end: float
    applied_start: float
    applied_end: float
    effective_duration: float
    width: int
    height: int
    has_audio: bool
    transition_type: str
    transition_duration: float


@dataclass
class PrecheckResult:
    clips_count: int
    estimated_output_duration: float
    target_width: int
    target_height: int
    has_any_audio: bool
    clips: list[PrecheckClipDetail]
    warnings: list[str]


def merge_videos(clips: list[VideoClip], output_file: str) -> MergeResult:
    if not clips:
        raise ValueError("clips is empty")
    _validate_transition_types(clips)

    output_path = Path(output_file).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="storyboard-merge-") as temp_dir:
        temp_root = Path(temp_dir)
        trimmed: list[Path] = []
        processed_clips: list[VideoClip] = []
        details: list[ClipProcessDetail] = []

        for index, clip in enumerate(clips):
            source_path = _download_or_copy(clip.url, temp_root / f"source_{index}.mp4")
            source_duration = _probe_duration(source_path)
            applied_start, applied_end = _normalize_trim_range(
                source_duration=source_duration,
                requested_start=clip.start_time,
                requested_end=clip.end_time,
            )

            trim_path = temp_root / f"trim_{index}.mp4"
            _trim_video(
                source_path,
                trim_path,
                applied_start,
                applied_end,
            )
            trimmed.append(trim_path)
            final_duration = _probe_duration(trim_path)

            transition = clip.transition or TransitionConfig()
            processed_clips.append(
                VideoClip(
                    url=str(trim_path),
                    duration=final_duration,
                    start_time=0.0,
                    end_time=0.0,
                    transition=transition,
                )
            )
            details.append(
                ClipProcessDetail(
                    index=index,
                    source_url=clip.url,
                    source_duration=source_duration,
                    requested_start=clip.start_time,
                    requested_end=clip.end_time,
                    applied_start=applied_start,
                    applied_end=applied_end,
                    final_duration=final_duration,
                    transition_type=transition.type,
                    transition_duration=transition.duration,
                )
            )

        _validate_transition_durations(processed_clips)

        if _has_transitions(processed_clips):
            _merge_with_xfade(trimmed, processed_clips, output_path)
        else:
            _concat_without_transitions(trimmed, output_path)

    output_duration = _probe_duration(output_path)
    return MergeResult(
        output_path=str(output_path),
        output_duration=output_duration,
        clips=details,
    )


def precheck_merge(clips: list[VideoClip]) -> PrecheckResult:
    if not clips:
        raise ValueError("clips is empty")
    _validate_transition_types(clips)

    warnings: list[str] = []
    details: list[PrecheckClipDetail] = []
    processed_clips: list[VideoClip] = []
    widths: list[int] = []
    heights: list[int] = []
    has_any_audio = False

    with tempfile.TemporaryDirectory(prefix="storyboard-precheck-") as temp_dir:
        temp_root = Path(temp_dir)
        for index, clip in enumerate(clips):
            source_path = _download_or_copy(clip.url, temp_root / f"source_{index}.mp4")
            source_duration = _probe_duration(source_path)
            width, height = _probe_resolution(source_path)
            has_audio = _has_audio_stream(source_path)
            has_any_audio = has_any_audio or has_audio
            widths.append(width)
            heights.append(height)

            applied_start, applied_end = _normalize_trim_range(
                source_duration=source_duration,
                requested_start=clip.start_time,
                requested_end=clip.end_time,
            )
            effective_duration = max(0.0, applied_end - applied_start) if applied_end > 0 else source_duration
            transition = clip.transition or TransitionConfig()
            processed_clips.append(
                VideoClip(
                    url=clip.url,
                    duration=effective_duration,
                    start_time=0.0,
                    end_time=0.0,
                    transition=transition,
                )
            )
            details.append(
                PrecheckClipDetail(
                    index=index,
                    source_url=clip.url,
                    source_duration=source_duration,
                    requested_start=clip.start_time,
                    requested_end=clip.end_time,
                    applied_start=applied_start,
                    applied_end=applied_end,
                    effective_duration=effective_duration,
                    width=width,
                    height=height,
                    has_audio=has_audio,
                    transition_type=transition.type,
                    transition_duration=transition.duration,
                )
            )
            if source_duration <= 0:
                warnings.append(f"clip {index}: failed to probe source duration")
            if not has_audio:
                warnings.append(f"clip {index}: no audio stream, silence track will be injected")

    _validate_transition_durations(processed_clips)

    target_width = max(widths) if widths else DEFAULT_WIDTH
    target_height = max(heights) if heights else DEFAULT_HEIGHT
    if any(w != target_width or h != target_height for w, h in zip(widths, heights)):
        warnings.append("clips have mixed resolutions and will be scaled/padded to a unified target")

    estimated_duration = sum(_clip_duration(c) for c in processed_clips)
    for idx in range(len(processed_clips) - 1):
        transition = processed_clips[idx].transition or TransitionConfig()
        if transition.type.lower() != "none":
            estimated_duration -= max(0.0, transition.duration)

    return PrecheckResult(
        clips_count=len(processed_clips),
        estimated_output_duration=max(0.0, estimated_duration),
        target_width=target_width,
        target_height=target_height,
        has_any_audio=has_any_audio,
        clips=details,
        warnings=warnings,
    )


def _download_or_copy(url: str, dest_path: Path) -> Path:
    if url.startswith("http://") or url.startswith("https://"):
        with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
            data = response.read()
            dest_path.write_bytes(data)
        return dest_path

    source = Path(url).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"input video not found: {url}")
    shutil.copy2(source, dest_path)
    return dest_path


def _trim_video(input_path: Path, output_path: Path, start_time: float, end_time: float) -> None:
    base_cmd = ["ffmpeg", "-y", "-i", str(input_path)]

    if end_time > start_time > 0:
        base_cmd.extend(["-ss", f"{start_time:.2f}", "-to", f"{end_time:.2f}"])
    elif start_time > 0:
        base_cmd.extend(["-ss", f"{start_time:.2f}"])

    base_cmd.extend(
        [
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )
    _run_cmd(base_cmd)


def _concat_without_transitions(input_files: list[Path], output_path: Path) -> None:
    list_file = output_path.parent / "ffmpeg_concat_list.txt"
    list_content = "\n".join([f"file '{path.resolve()}'" for path in input_files])
    list_file.write_text(list_content, encoding="utf-8")
    try:
        _run_cmd(
            [
                "ffmpeg",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                "-y",
                str(output_path),
            ]
        )
    finally:
        if list_file.exists():
            list_file.unlink()


def _merge_with_xfade(input_files: list[Path], clips: list[VideoClip], output_path: Path) -> None:
    args: list[str] = []
    for path in input_files:
        args.extend(["-i", str(path)])

    target_width, target_height = _get_target_resolution(input_files)

    durations = [_clip_duration(clip) for clip in clips]
    audio_streams = [_has_audio_stream(path) for path in input_files]

    video_filters: list[str] = _build_video_prepare_filters(
        len(input_files),
        target_width,
        target_height,
        clips,
    )
    audio_filters: list[str] = _build_audio_prepare_filters(
        len(input_files),
        clips,
        durations,
        audio_streams,
    )

    current_video_label = "[v0]"
    current_audio_label = "[a0]"
    offset = durations[0]

    for idx in range(len(input_files) - 1):
        transition = clips[idx].transition or TransitionConfig()
        transition_type = _map_transition_type(transition.type)
        duration = max(0.0, float(transition.duration))
        if transition.type.lower() == "none":
            duration = 0.001

        next_video = f"[v{idx + 1}]"
        out_video = f"[vxf{idx}]"
        video_filters.append(
            f"{current_video_label}{next_video}xfade=transition={transition_type}:duration={duration:.2f}:offset={max(0.0, offset - duration):.2f}{out_video}"
        )
        current_video_label = out_video

        next_audio = f"[a{idx + 1}]"
        out_audio = f"[axf{idx}]"
        audio_filters.append(f"{current_audio_label}{next_audio}acrossfade=d={duration:.2f}{out_audio}")
        current_audio_label = out_audio

        if idx + 1 < len(clips):
            offset += durations[idx + 1] - duration

    filter_parts = video_filters + audio_filters
    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", *args, "-filter_complex", filter_complex, "-map", current_video_label]
    if audio_filters:
        cmd.extend(["-map", current_audio_label, "-c:a", "aac", "-b:a", "128k"])

    cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-y", str(output_path)])
    _run_cmd(cmd)


def _run_cmd(cmd: list[str]) -> None:
    logger.debug("ffmpeg cmd: %s", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg command failed: {' '.join(cmd)}\n{proc.stderr}")


def _has_transitions(clips: list[VideoClip]) -> bool:
    for clip in clips:
        if clip.transition and clip.transition.type and clip.transition.type.lower() != "none":
            return True
    return False


def _map_transition_type(name: str) -> str:
    mapping = {
        "fade": "fade",
        "dissolve": "dissolve",
        "wipeleft": "wipeleft",
        "wiperight": "wiperight",
        "slideleft": "slideleft",
        "slideright": "slideright",
    }
    return mapping.get(name.lower(), "fade")


def _clip_duration(clip: VideoClip) -> float:
    if clip.end_time > clip.start_time:
        return clip.end_time - clip.start_time
    if clip.duration > 0:
        return clip.duration
    return DEFAULT_CLIP_DURATION


def _probe_duration(path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_SECONDS)
    if proc.returncode != 0:
        return 0.0
    raw = proc.stdout.strip()
    try:
        value = float(raw)
    except ValueError:
        return 0.0
    return max(0.0, value)


def _normalize_trim_range(source_duration: float, requested_start: float, requested_end: float) -> tuple[float, float]:
    if source_duration <= 0:
        return max(0.0, requested_start), max(0.0, requested_end)

    start = max(0.0, min(requested_start, max(0.0, source_duration - 0.05)))
    if requested_end > 0:
        end = max(0.0, min(requested_end, source_duration))
    else:
        end = source_duration

    if end <= start + 0.05:
        start = 0.0
        end = source_duration
    return start, end


def _validate_transition_types(clips: list[VideoClip]) -> None:
    for idx, clip in enumerate(clips):
        transition = clip.transition or TransitionConfig()
        t = transition.type.lower()
        if t not in ALLOWED_TRANSITION_TYPES:
            raise ValueError(
                f"invalid transition type at clip {idx}: {transition.type}. "
                f"allowed: {sorted(ALLOWED_TRANSITION_TYPES)}"
            )


def _validate_transition_durations(clips: list[VideoClip]) -> None:
    if len(clips) < 2:
        return
    for idx in range(len(clips) - 1):
        transition = clips[idx].transition or TransitionConfig()
        if transition.type.lower() == "none":
            continue
        left = _clip_duration(clips[idx])
        right = _clip_duration(clips[idx + 1])
        max_allowed = max(0.1, min(left, right) - 0.1)
        if transition.duration > max_allowed:
            raise ValueError(
                f"transition duration too long at clip {idx}: {transition.duration:.2f}s, "
                f"max allowed is {max_allowed:.2f}s (clip durations: {left:.2f}/{right:.2f})"
            )


def _get_target_resolution(input_files: list[Path]) -> tuple[int, int]:
    max_width = 0
    max_height = 0
    for path in input_files:
        width, height = _probe_resolution(path)
        max_width = max(max_width, width)
        max_height = max(max_height, height)

    if max_width <= 0 or max_height <= 0:
        return DEFAULT_WIDTH, DEFAULT_HEIGHT
    return max_width, max_height


def _probe_resolution(path: Path) -> tuple[int, int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_SECONDS)
    if proc.returncode != 0:
        return DEFAULT_WIDTH, DEFAULT_HEIGHT

    raw = proc.stdout.strip()
    parts = raw.split(",")
    if len(parts) != 2:
        return DEFAULT_WIDTH, DEFAULT_HEIGHT
    try:
        width = int(parts[0])
        height = int(parts[1])
    except ValueError:
        return DEFAULT_WIDTH, DEFAULT_HEIGHT
    if width <= 0 or height <= 0:
        return DEFAULT_WIDTH, DEFAULT_HEIGHT
    return width, height


def _has_audio_stream(path: Path) -> bool:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_type",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_SECONDS)
    if proc.returncode != 0:
        return False
    return proc.stdout.strip() == "audio"


def _build_video_prepare_filters(
    count: int,
    target_width: int,
    target_height: int,
    clips: list[VideoClip],
) -> list[str]:
    filters: list[str] = []
    for idx in range(count):
        tpad_duration = 0.0
        if idx < len(clips) - 1 and clips[idx].transition and clips[idx].transition.type.lower() != "none":
            tpad_duration = max(0.0, clips[idx].transition.duration)

        if tpad_duration > 0:
            filters.append(
                f"[{idx}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2,"
                f"tpad=stop_mode=clone:stop_duration={tpad_duration:.2f}[v{idx}]"
            )
        else:
            filters.append(
                f"[{idx}:v]scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[v{idx}]"
            )
    return filters


def _build_audio_prepare_filters(
    count: int,
    clips: list[VideoClip],
    durations: list[float],
    audio_streams: list[bool],
) -> list[str]:
    filters: list[str] = []
    for idx in range(count):
        pad_duration = 0.0
        if idx < len(clips) - 1 and clips[idx].transition and clips[idx].transition.type.lower() != "none":
            pad_duration = max(0.0, clips[idx].transition.duration)

        total_duration = max(0.1, durations[idx] + pad_duration)
        if not audio_streams[idx]:
            filters.append(
                f"anullsrc=channel_layout=stereo:sample_rate=44100:duration={total_duration:.2f}[a{idx}]"
            )
        elif pad_duration > 0:
            filters.append(f"[{idx}:a]apad=pad_dur={pad_duration:.2f}[a{idx}]")
        else:
            filters.append(f"[{idx}:a]acopy[a{idx}]")
    return filters
