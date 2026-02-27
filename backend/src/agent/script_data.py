"""Script detail parser for frontend ScriptView data."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import SystemMessage

from src.agent.nodes import _extract_json, _to_text, get_llm
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


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


def _merge_named_items(
    base_items: list[dict[str, str]],
    llm_items: list[dict[str, str]],
    *,
    include_keys: tuple[str, ...],
) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in [*base_items, *llm_items]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        row: dict[str, str] = {"id": str(len(merged) + 1), "name": name}
        for key in include_keys:
            row[key] = str(item.get(key) or "").strip()
        merged.append(row)
    return merged


def _opening_narration(synopsis: str) -> str:
    sentences = [s.strip() for s in re.split(r"[。！？]", synopsis) if s.strip()]
    if not sentences:
        return ""
    return "，".join(sentences[:2]).rstrip("，") + "！"


def _normalize_llm_shots(shots: Any, synopsis: str) -> list[dict[str, Any]]:
    if not isinstance(shots, list):
        return []

    normalized: list[dict[str, Any]] = []
    opening = _opening_narration(synopsis)
    for idx, item in enumerate(shots, start=1):
        if not isinstance(item, dict):
            continue
        shot_name = str(item.get("shotName") or item.get("name") or "").strip()
        visual_desc = str(item.get("visualDesc") or item.get("description") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if not summary:
            first_sentence = re.split(r"[。；\n]", visual_desc)[0].strip() if visual_desc else ""
            summary = first_sentence[:80] if first_sentence else visual_desc[:80]
        if not shot_name and not visual_desc:
            continue
        narration = str(item.get("narration") or "").strip()
        has_narration = bool(item.get("hasNarration"))
        if idx == 1 and not narration and opening:
            narration = opening
            has_narration = True
        normalized.append(
            {
                "id": idx,
                "duration": str(item.get("duration") or "3.0s").strip() or "3.0s",
                "summary": summary,
                "narration": narration,
                "hasNarration": has_narration,
                "visualDesc": visual_desc,
                "shotName": shot_name or f"镜头{idx}",
            }
        )
    return normalized


def _decode_json_value(text: str) -> Any:
    raw = text.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    fenced_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", raw)
    for block in fenced_blocks:
        candidate = block.strip()
        if not candidate:
            continue
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    decoder = json.JSONDecoder()
    starts = [i for i in (raw.find("{"), raw.find("[")) if i >= 0]
    if not starts:
        return None
    start = min(starts)
    try:
        value, _ = decoder.raw_decode(raw[start:])
        return value
    except Exception:
        return None


def _normalize_aigc_spec(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None

    if isinstance(value, list):
        value = {"shots": value}
    if not isinstance(value, dict):
        return None

    shots_raw = value.get("shots")
    if not isinstance(shots_raw, list):
        shots_raw = []

    shots: list[dict[str, Any]] = []
    for idx, shot in enumerate(shots_raw, start=1):
        if not isinstance(shot, dict):
            continue
        render_spec = shot.get("render_spec")
        if not isinstance(render_spec, dict):
            render_spec = {}
        sid = shot.get("id")
        try:
            shot_id = int(sid)
        except Exception:
            shot_id = idx
        shots.append(
            {
                "id": shot_id,
                "name": str(shot.get("name") or "").strip() or f"镜头{idx}",
                "director_brief": str(shot.get("director_brief") or "").strip(),
                "render_spec": render_spec,
            }
        )

    global_negative = value.get("global_negative")
    if not isinstance(global_negative, list):
        global_negative = []

    normalized = {
        "density": str(value.get("density") or "balanced").strip() or "balanced",
        "global_negative": [str(x).strip() for x in global_negative if str(x).strip()],
        "shots": shots,
    }
    return normalized


def _extract_aigc_spec_from_markdown(final_copy: str) -> dict[str, Any] | None:
    normalized = _clean_markdown(final_copy)
    section = re.search(
        r"(?:^|\n)\s*(?:#{1,3}\s*)?AIGC执行规格(?:\s*\(JSON\)|\s*（JSON）)?\s*\n([\s\S]*?)(?=\n\s*#{1,3}\s+\S|\Z)",
        normalized,
    )
    if not section:
        return None
    value = _decode_json_value(section.group(1))
    return _normalize_aigc_spec(value)


def _extract_script_data_with_llm(
    *,
    final_copy: str,
    synopsis: str,
    shots_text: str,
    style_text: str,
) -> dict[str, Any]:
    if not settings.script_data_llm_enabled or not final_copy.strip():
        return {}

    prompt = f"""你是“剧本结构化信息抽取器”。
你需要从给定剧本文本中抽取前端 ScriptView 所需字段，并严格输出一个 JSON 对象，不要输出任何解释或 markdown。

抽取要求：
1) characters/scenes/props/shots 都是数组，不确定时返回空数组。
2) 角色、场景、道具名称要去重，避免把镜头词（特写/远景/全景等）当成角色。
3) shots 按叙事顺序输出，每个元素包含：
   - shotName: 镜头名称（如“开场远景”“主角特写”）
   - visualDesc: 画面描述
   - summary: 该镜头一句话摘要（<=80字）
   - narration: 旁白（没有就空字符串）
   - hasNarration: 布尔值
   - duration: 形如 "3.0s"
4) props 每项包含 name 和 type（关键道具/普通道具）。
5) style_text 若为空可返回空字符串。

输出 JSON 结构：
{{
  "synopsis": "故事梗概",
  "packagingStyle": "视觉包装风格",
  "characters": [{{"name": "xx", "description": "xx"}}],
  "scenes": [{{"name": "xx", "description": "xx"}}],
  "props": [{{"name": "xx", "type": "关键道具"}}],
  "shots": [
    {{
      "shotName": "xx",
      "visualDesc": "xx",
      "summary": "xx",
      "narration": "",
      "hasNarration": false,
      "duration": "3.0s"
    }}
  ],
  "aigcSpec": {{
    "density": "cinematic|balanced|strict",
    "global_negative": ["全局负向约束"],
    "shots": [
      {{
        "id": 1,
        "name": "镜头名称",
        "director_brief": "创意层一句话",
        "render_spec": {{}}
      }}
    ]
  }}
}}

输入信息：
synopsis（规则切分结果）:
{synopsis}

shots_text（规则切分结果）:
{shots_text}

style_text（规则切分结果）:
{style_text}

完整原文：
{final_copy}
"""
    try:
        llm = get_llm(temperature=0.0)
        response = llm.invoke([SystemMessage(content=prompt)])
        raw_text = _to_text(getattr(response, "content", response))
        parsed = _extract_json(raw_text) or {}
        return parsed if isinstance(parsed, dict) else {}
    except Exception as exc:
        logger.warning("script_data LLM extraction failed, fallback to regex only: %s", exc)
        return {}


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
    regex_shots = _parse_shots(shots_text, synopsis)
    regex_characters = _extract_characters(synopsis, shots_text)
    regex_scenes = _extract_scenes(synopsis, shots_text)
    regex_props = _extract_props(f"{synopsis}\n{shots_text}")

    llm_data = _extract_script_data_with_llm(
        final_copy=final_copy,
        synopsis=synopsis,
        shots_text=shots_text,
        style_text=style_text,
    )
    llm_synopsis = str(llm_data.get("synopsis") or "").strip() if isinstance(llm_data, dict) else ""
    llm_style = str(llm_data.get("packagingStyle") or "").strip() if isinstance(llm_data, dict) else ""
    llm_characters_raw = llm_data.get("characters") if isinstance(llm_data, dict) else None
    llm_scenes_raw = llm_data.get("scenes") if isinstance(llm_data, dict) else None
    llm_props_raw = llm_data.get("props") if isinstance(llm_data, dict) else None
    llm_shots_raw = llm_data.get("shots") if isinstance(llm_data, dict) else None
    llm_aigc_spec_raw = llm_data.get("aigcSpec") if isinstance(llm_data, dict) else None

    llm_characters = _merge_named_items(
        [],
        llm_characters_raw if isinstance(llm_characters_raw, list) else [],
        include_keys=("description",),
    )
    llm_scenes = _merge_named_items(
        [],
        llm_scenes_raw if isinstance(llm_scenes_raw, list) else [],
        include_keys=("description",),
    )
    llm_props = _merge_named_items(
        [],
        llm_props_raw if isinstance(llm_props_raw, list) else [],
        include_keys=("type",),
    )
    llm_shots = _normalize_llm_shots(llm_shots_raw, synopsis)
    llm_aigc_spec = _normalize_aigc_spec(llm_aigc_spec_raw)

    characters = _merge_named_items(
        regex_characters,
        llm_characters,
        include_keys=("description",),
    )
    scenes = _merge_named_items(
        regex_scenes,
        llm_scenes,
        include_keys=("description",),
    )
    props = _merge_named_items(
        regex_props,
        llm_props,
        include_keys=("type",),
    )
    shot_list = llm_shots if llm_shots else regex_shots
    shot_count = len(shot_list)

    duration_label = f"{duration_sec} 秒" if duration_sec else (f"{shot_count * 3} 秒" if shot_count else "24 秒")
    final_synopsis = llm_synopsis or synopsis
    final_style_text = llm_style or style_text
    markdown_aigc_spec = _extract_aigc_spec_from_markdown(final_copy)
    final_aigc_spec = llm_aigc_spec or markdown_aigc_spec

    return {
        "title": title or user_input[:20] or "剧本创作",
        "totalShots": shot_count or 8,
        "totalDuration": duration_label,
        "style": style_name or "日漫 电影质感",
        "requirements": user_input,
        "synopsis": final_synopsis or "暂无故事梗概",
        "packagingStyle": final_style_text or "暂无包装风格描述",
        "characters": characters,
        "scenes": scenes,
        "props": props,
        "shots": shot_list,
        "aigcSpec": final_aigc_spec,
    }

