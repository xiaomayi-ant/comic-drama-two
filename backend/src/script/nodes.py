"""剧本生成 Agent 节点定义"""

import json
import logging
from typing import Any, Optional

from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models.chat_models import BaseChatModel

from src.agent.prompts import SCRIPT_GENERATION_PROMPT
from src.novel.move_extractor import extract_moves_from_novel
from src.script.state import ScriptAgentState
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


def _to_text(content: Any) -> str:
    """Normalize LLM message content to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (bytes, bytearray)):
        try:
            return content.decode("utf-8", errors="ignore")
        except Exception:
            return str(content)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item.get("value") or ""))
            else:
                parts.append(str(item))
        return "\n".join(p for p in parts if p).strip()
    return str(content)


def _dbg(label: str, payload: Any, *, limit: int = 2000) -> None:
    """Debug logging controlled by env flags."""
    if not settings.debug_node_io:
        return
    try:
        text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    except Exception:
        text = str(payload)
    if limit and len(text) > limit:
        text = text[:limit] + "\n...(truncated)"
    logger.info(f"[DEBUG:{label}]\n{text}")


def _build_move_guidance_ir(
    *,
    user_input: str,
    move_codebook: Optional[dict[str, Any]],
    retrieval_results: Optional[list[dict[str, Any]]],
) -> tuple[dict[str, Any], str]:
    """构建供写作 LLM 参考的轻量 IR。"""
    ref_ids: list[str] = []
    if isinstance(retrieval_results, list):
        for r in retrieval_results:
            if not isinstance(r, dict):
                continue
            ref_ids.append(f"{r.get('novel_id', 'unknown')}#{r.get('node_id', 'unknown')}")

    moves_raw = move_codebook.get("moves", []) if isinstance(move_codebook, dict) else []
    move_guidance: list[dict[str, Any]] = []
    for idx, mv in enumerate(moves_raw):
        if not isinstance(mv, dict):
            continue
        refs: list[str] = []
        chapters = mv.get("chapters")
        if isinstance(chapters, list):
            for ch in chapters:
                try:
                    ch_idx = int(ch)
                except Exception:
                    continue
                # 如果 chapters 为检索结果序号，则映射到对应 ref_id
                if 1 <= ch_idx <= len(ref_ids):
                    rid = ref_ids[ch_idx - 1]
                    if rid not in refs:
                        refs.append(rid)
        if not refs and ref_ids:
            refs = ref_ids[: min(2, len(ref_ids))]

        move_guidance.append(
            {
                "move_id": mv.get("move_id"),
                "name": mv.get("name"),
                "description": mv.get("description"),
                "core_idea": mv.get("core_idea"),
                "emotional_beats": mv.get("emotional_beats") or [],
                "references": refs,
                "priority": "high" if idx < 3 else "medium",
            }
        )

    ir = {
        "narrative_intent": user_input,
        "move_guidance": move_guidance,
    }
    return ir, json.dumps(ir, ensure_ascii=False, indent=2)


def get_llm(temperature: Optional[float] = None) -> BaseChatModel:
    """获取 LLM 实例"""
    temp = temperature if temperature is not None else settings.model_temperature
    model = settings.model_name

    if settings.llm_provider.lower() == "openai":
        from langchain_openai import ChatOpenAI
        
        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temp,
        }
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        
        logger.info(f"使用 OpenAI LLM: model={model}")
        return ChatOpenAI(**kwargs)
    else:
        logger.info(f"使用 DashScope LLM: model={model}")
        kwargs: dict[str, Any] = {
            "model": model,
            "temperature": temp,
        }
        if settings.dashscope_base_url:
            kwargs["base_url"] = settings.dashscope_base_url
        return ChatTongyi(**kwargs)


def load_reference_node(state: ScriptAgentState) -> dict[str, Any]:
    """
    加载参考素材（通过 hybrid-search 语义检索）

    用用户输入作为 query 检索相关章节，提取 Move 结构，
    同时保留检索原文供 write_scenes_node 使用。
    检索服务不可用时降级为空结果，不阻断工作流。
    """
    logger.info("[Script] Load Reference Node")

    if not settings.enable_retrieval:
        logger.info("检索已禁用 (enable_retrieval=false)，直接使用 LLM 生成")
        return {
            "move_codebook": None,
            "retrieval_results": None,
            "reference_novel_data": None,
        }

    query = state.get("user_input", "")
    if not query:
        logger.info("无用户输入，跳过检索")
        return {
            "move_codebook": None,
            "retrieval_results": None,
            "reference_novel_data": None,
        }

    try:
        from src.retrieval.searcher import HybridSearcher

        searcher = HybridSearcher(settings)
        results = searcher.search(
            query,
            top_k=settings.retrieval_top_k,
            use_native=True,
            use_rerank=settings.retrieval_use_rerank,
            rerank_score_gap=settings.retrieval_rerank_gap,
        )

        # NOTE: RRF score 仅反映排名（1/(k+rank)），不适合做质量过滤。
        # 质量控制依赖 top_k 参数和后续 rerank（启用时）。

        if not results:
            logger.warning("检索未返回结果，直接使用 LLM 生成")
            return {
                "move_codebook": None,
                "retrieval_results": None,
                "reference_novel_data": None,
            }

        logger.info("检索到 %d 个相关章节", len(results))
        for idx, r in enumerate(results, start=1):
            novel_name = r.get("novel_name", "未知")
            novel_id = r.get("novel_id", "未知")
            node_id = r.get("node_id", "未知")
            chapter_title = r.get("tree_node", {}).get("title", "未知章节")
            logger.info(
                "检索命中[%d] novel=%s novel_id=%s node_id=%s title=%s",
                idx, novel_name, novel_id, node_id, chapter_title,
            )

        # 将检索结果转换为 novel_data 格式给 Move 提取器
        novel_data = {
            "title": "检索参考素材",
            "author": "多源",
            "chapters": [
                {
                    "chapter_num": i + 1,
                    "chapter_name": r.get("tree_node", {}).get("title", ""),
                    "content": r.get("content", ""),
                }
                for i, r in enumerate(results)
            ],
        }

        import asyncio

        move_codebook, codebook_id = asyncio.run(
            extract_moves_from_novel(novel_data)
        )

        if move_codebook:
            logger.info(
                "成功提取 Move 结构: %d 个 moves",
                len(move_codebook.get("moves", [])),
            )
        else:
            logger.warning("Move 提取失败，使用空的 move_codebook")

        return {
            "move_codebook": move_codebook,
            "retrieval_results": results,
            "reference_novel_data": novel_data,
        }

    except Exception as e:
        logger.warning("检索服务异常: %s，降级为空结果", e)
        return {
            "move_codebook": None,
            "retrieval_results": None,
            "reference_novel_data": None,
        }


def plan_story_node(state: ScriptAgentState, config: RunnableConfig) -> dict[str, Any]:
    """
    规划故事结构

    如果有参考小说的 Move 结构，则基于它规划
    如果没有，则直接进入剧本生成
    """
    logger.info("📝 [Script] Plan Story Node")

    user_input = state.get("user_input", "")
    user_instructions = state.get("user_instructions", "")
    target_chapters = state.get("target_chapters", 1)
    move_codebook = state.get("move_codebook")

    if not move_codebook:
        logger.info("无参考 Move，直接进入剧本生成")
        return {
            "plan_text": None,
        }

    # 有参考小说时，可以先用 LLM 规划一下故事结构（可选）
    # 这里可以复用 novel 的 plan_story_prompt，但暂时简化处理
    # 先直接进入剧本生成阶段

    return {
        "plan_text": None,
    }


def write_scenes_node(state: ScriptAgentState, config: RunnableConfig) -> dict[str, Any]:
    """
    生成剧本内容

    调用 SCRIPT_GENERATION_PROMPT 生成剧本
    """
    logger.info("✍️ [Script] Write Scenes Node")

    user_input = state.get("user_input", "")
    script_config = state.get("script_config", {})
    target_chapters = state.get("target_chapters", 1)
    move_codebook = state.get("move_codebook")

    try:
        llm = get_llm()

        # 构建剧本生成 Prompt
        ratio = script_config.get("ratio", "16:9")
        style = script_config.get("style", "动漫风")
        duration = script_config.get("duration", "系统推荐")
        narrator = script_config.get("narrator", "需要旁白")
        mood = script_config.get("mood", "温馨感人")
        density = script_config.get("density", "balanced")

        # 如果有多章/多场景需求，可以在 prompt 中说明
        chapters_hint = ""
        if target_chapters > 1:
            chapters_hint = f"\n注意：本剧本分为 {target_chapters} 个章节/场景，请为每个章节设计相应的分镜。"

        # 格式化检索结果为参考素材
        reference_text = ""
        retrieval_results = state.get("retrieval_results")
        if retrieval_results:
            parts = []
            for r in retrieval_results:
                title = r.get("tree_node", {}).get("title", "未知")
                novel = r.get("novel_name", "未知")
                summary = r.get("tree_node", {}).get("summary", "")
                content = r.get("content", "")[:800]
                ref_id = f"{r.get('novel_id', 'unknown')}#{r.get('node_id', 'unknown')}"
                parts.append(
                    f"【{novel} - {title}】\nref_id: {ref_id}\n摘要：{summary}\n内容片段：{content}"
                )
            reference_text = "\n\n".join(parts)

        move_guidance_ir_obj, move_guidance_ir_text = _build_move_guidance_ir(
            user_input=user_input,
            move_codebook=move_codebook if isinstance(move_codebook, dict) else None,
            retrieval_results=retrieval_results if isinstance(retrieval_results, list) else None,
        )

        script_prompt = SCRIPT_GENERATION_PROMPT.format(
            RATIO=ratio,
            STYLE=style,
            DURATION=duration,
            NARRATOR=narrator,
            MOOD=mood,
            DENSITY=density,
            USER_INPUT=user_input + chapters_hint,
            REFERENCE_MATERIALS=reference_text,
            MOVE_GUIDANCE_IR=move_guidance_ir_text,
        )

        if settings.debug_llm_io:
            _dbg("script_writing.input", script_prompt[:2000])

        # 使用流式调用，让 LangGraph astream_events 能捕获 on_chat_model_stream
        chunks = []
        for chunk in llm.stream(
            [SystemMessage(content=script_prompt)],
            config=config,
        ):
            chunk_text = _to_text(getattr(chunk, "content", chunk))
            if chunk_text:
                chunks.append(chunk_text)

        raw_text = "".join(chunks)

        if settings.debug_llm_io:
            _dbg("script_writing.raw", raw_text[:3000])

        logger.info(f"剧本生成完成，长度: {len(raw_text)} 字符")

        return {
            "draft_script": raw_text,
            "final_script": raw_text,
            "iteration_count": 1,
            "prompt_used": script_prompt,
            "move_guidance_ir": move_guidance_ir_obj,
        }

    except Exception as e:
        logger.exception(f"❌ 剧本生成失败: {e}")
        return {
            "draft_script": None,
            "final_script": None,
            "error": str(e),
            "iteration_count": 1,
        }


def finalize_node(state: ScriptAgentState) -> dict[str, Any]:
    """
    整理最终输出

    直接返回已有的 final_script
    """
    logger.info("✅ [Script] Finalize Node")

    final_script = state.get("final_script")
    if not final_script:
        return {
            "final_script": "抱歉，剧本生成失败",
        }

    return {
        "final_script": final_script,
    }
