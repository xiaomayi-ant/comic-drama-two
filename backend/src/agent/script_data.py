"""Script detail parser for frontend ScriptView data."""

from __future__ import annotations

import re
from typing import Any


def _clean_markdown(text: str) -> str:
    cleaned = re.sub(r"^```[^\n]*\n?", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE)
    return cleaned.strip()


def _split_sections(text: str) -> tuple[str, str, str]:
    normalized = _clean_markdown(text)
    shot_match = re.search(r"(?:^|\n)\s*(?:#{1,3}\s*)?分镜设计", normalized)
    style_match = re.search(r"(?:^|\n)\s*(?:#{1,3}\s*)?视觉风格", normalized)

    shot_idx = shot_match.start() if shot_match else -1
    style_idx = style_match.start() if style_match else -1

    synopsis = ""
    shots = ""
    style = ""
    if shot_idx != -1 and style_idx != -1:
        synopsis = normalized[:shot_idx].strip()
        shots = normalized[shot_idx:style_idx].strip()
        style = normalized[style_idx:].strip()
    elif shot_idx != -1:
        synopsis = normalized[:shot_idx].strip()
        shots = normalized[shot_idx:].strip()
    elif style_idx != -1:
        synopsis = normalized[:style_idx].strip()
        style = normalized[style_idx:].strip()
    else:
        synopsis = normalized

    synopsis = re.sub(r"^(?:#{1,3}\s*)?剧本概览\s*", "", synopsis, flags=re.MULTILINE)
    synopsis = re.sub(r"^故事核心[：:]\s*", "", synopsis, flags=re.MULTILINE)
    shots = re.sub(r"^(?:#{1,3}\s*)?分镜设计\s*", "", shots, flags=re.MULTILINE).strip()
    style = re.sub(r"^(?:#{1,3}\s*)?视觉风格\s*", "", style, flags=re.MULTILINE).strip()
    return synopsis.strip(), shots, style


def _extract_characters(synopsis: str, shots_text: str) -> list[dict[str, str]]:
    name_blacklist = {
        "勿外传", "元朝末年", "武当山", "明教", "太极", "乾坤", "九阳", "武林", "天下",
        "江湖", "中原", "少林", "峨眉", "昆仑", "崆峒", "巅峰", "山巅", "金殿", "云雾",
        "寒气", "真气", "神功", "剑法", "掌法", "拳法", "内力", "冰封", "特写", "远景",
        "全景", "中景", "近景", "俯拍", "仰拍", "画面", "镜头", "背景", "前景", "构图",
        "色调", "光影", "整体", "风格", "质感", "氛围", "情绪", "动作", "场景",
    }
    all_text = f"{synopsis}\n{shots_text}"
    role_pattern = re.compile(r"([^\s，。、；：\"\"''（）【】\d]{2,4})(?:[（(]([^）)]+)[）)])")
    is_chinese = re.compile(r"^[\u4e00-\u9fff]+$")
    found: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in role_pattern.finditer(all_text):
        name = match.group(1).strip()
        desc = match.group(2).strip()
        if (
            name not in seen
            and is_chinese.fullmatch(name)
            and name not in name_blacklist
            and 2 <= len(name) <= 4
        ):
            seen.add(name)
            found.append({"id": str(len(found) + 1), "name": name, "description": desc})
    return found


def _extract_scenes(synopsis: str, shots_text: str) -> list[dict[str, str]]:
    all_text = f"{synopsis}\n{shots_text}"
    suffix_pattern = (
        r"(?:山巅|金殿|山谷|广场|大殿|客栈|庭院|山洞|峡谷|河畔|湖边|林中|密林|竹林|雪地|荒野|城楼|擂台|战场)"
    )
    patterns = [
        re.compile(rf"([^\s，。；：\"\"''（）【】]{{2,8}}{suffix_pattern})"),
        re.compile(r"场景[：:]\s*([^；。\n,，]+)"),
    ]
    scenes: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in pattern.finditer(all_text):
            raw = (match.group(1) or "").strip()
            for part in re.split(r"[,，、]", raw):
                name = part.strip().removeprefix("的")
                if 2 <= len(name) <= 12 and name not in seen:
                    seen.add(name)
                    scenes.append({"id": str(len(scenes) + 1), "name": name, "description": ""})
    return scenes


def _extract_props(all_text: str) -> list[dict[str, str]]:
    patterns = [
        re.compile(r"(?:太极[剑拳]|乾坤大挪移|九阳[神真]功|明教令牌|屠龙[刀剑]|倚天[剑刀]|圣火令|冰魄银针|玄冥神掌|七伤拳)"),
        re.compile(r"物品[：:]\s*([^；。\n]+)"),
        re.compile(r"道具[：:]\s*([^；。\n]+)"),
    ]
    props: list[dict[str, str]] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in pattern.finditer(all_text):
            prop_text = (match.group(1) if match.groups() else match.group(0)).strip()
            for part in re.split(r"[,，、]", prop_text):
                item = part.strip()
                if 2 <= len(item) <= 8 and item not in seen:
                    seen.add(item)
                    ptype = "关键道具" if len(props) == 0 else "普通道具"
                    props.append({"id": str(len(props) + 1), "name": item, "type": ptype})
    return props


def _shot_lines(shots_text: str) -> list[tuple[str, str]]:
    shot_items: list[tuple[str, str]] = []
    for line in [ln.strip() for ln in shots_text.splitlines() if ln.strip()]:
        bullet_match = re.match(r"^[-*]\s*\*\*([^*]+)\*\*\s*[-：:]\s*(.+)$", line)
        if bullet_match:
            shot_items.append((bullet_match.group(1).strip(), bullet_match.group(2).strip()))
            continue
        bracket_match = re.match(r"^【(.+?)】\s*(.+)$", line)
        if bracket_match:
            shot_items.append((bracket_match.group(1).strip(), bracket_match.group(2).strip()))
            continue
    return shot_items


def _parse_shots(shots_text: str, synopsis: str) -> list[dict[str, Any]]:
    items = _shot_lines(shots_text)
    if not items:
        return []

    sentences = [s.strip() for s in re.split(r"[。！？]", synopsis) if s.strip()]
    opening = ""
    if sentences:
        opening = "，".join(sentences[:2]).rstrip("，") + "！"

    shots: list[dict[str, Any]] = []
    for idx, (shot_name, body) in enumerate(items, start=1):
        first_sentence = re.split(r"[。；\n]", body)[0].strip() if body else ""
        summary = first_sentence[:80] if first_sentence else body[:80]
        shots.append(
            {
                "id": idx,
                "duration": "3.0s",
                "summary": summary,
                "narration": opening if idx == 1 else "",
                "hasNarration": bool(idx == 1 and opening),
                "visualDesc": body,
                "shotName": shot_name,
            }
        )
    return shots


def build_script_data(
    *,
    final_copy: str,
    user_input: str,
    title: str | None = None,
    duration_sec: int | None = None,
    style_name: str | None = None,
) -> dict[str, Any]:
    """Convert script markdown text to UI-friendly structured data."""
    synopsis, shots_text, style_text = _split_sections(final_copy)
    shot_list = _parse_shots(shots_text, synopsis)
    shot_count = len(shot_list)

    duration_label = f"{duration_sec} 秒" if duration_sec else (f"{shot_count * 3} 秒" if shot_count else "24 秒")
    characters = _extract_characters(synopsis, shots_text)
    scenes = _extract_scenes(synopsis, shots_text)
    props = _extract_props(f"{synopsis}\n{shots_text}")

    return {
        "title": title or user_input[:20] or "剧本创作",
        "totalShots": shot_count or 8,
        "totalDuration": duration_label,
        "style": style_name or "日漫 电影质感",
        "requirements": user_input,
        "synopsis": synopsis or "暂无故事梗概",
        "packagingStyle": style_text or "暂无包装风格描述",
        "characters": characters,
        "scenes": scenes,
        "props": props,
        "shots": shot_list,
    }

