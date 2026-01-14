"""Agent 节点逻辑模块"""

import json
import os
import re
from typing import Any, Optional

from langchain_community.chat_models import ChatTongyi
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel, Field

from src.agent.prompts import (
    COPYWRITING_BREAKDOWN_PROMPT,
    COPYWRITING_PROMPT,
    COPYWRITING_PROOFREADER_PROMPT,
    TEN_MOVE_LIVE_GEN_PROMPT,
    TEN_MOVE_LIVE_INV_PROMPT,
    TEN_MOVE_LIVE_PLAN_PROMPT,
)
from src.agent.state import (
    AgentState,
    BreakdownResult,
    IntentResult,
    IntentType,
    ProofreadResult,
)
from src.agent.ten_move import default_ten_move_schema, prune_moves_for_live_stream
from src.core.config import settings
from src.core.artifacts import persist_run_artifacts
from src.core.logger import get_logger

logger = get_logger(__name__)


def _to_text(content: Any) -> str:
    """Normalize LLM message content to text (some providers return list content)."""
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
        # Common shape: [{"type":"text","text":"..."}] or similar
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(
                    str(
                        item.get("text")
                        or item.get("content")
                        or item.get("value")
                        or ""
                    )
                )
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


# ============================================================
# LLM 初始化（支持 ChatTongyi 和 OpenAI，通过 settings.llm_provider 切换）
# ============================================================

def get_llm(temperature: Optional[float] = None) -> BaseChatModel:
    """
    获取 LLM 实例
    
    根据 settings.llm_provider 选择：
    - "dashscope": 使用 ChatTongyi（通义千问）
    - "openai": 使用 ChatOpenAI
    """
    temp = temperature if temperature is not None else settings.model_temperature
    
    if settings.llm_provider.lower() == "openai":
        from langchain_openai import ChatOpenAI
        
        kwargs: dict[str, Any] = {
            "model": settings.model_name,
            "temperature": temp,
        }
        # 支持自定义 base_url（用于代理或兼容 API）
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        
        logger.info(f"使用 OpenAI LLM: model={settings.model_name}")
        return ChatOpenAI(**kwargs)
    else:
        # 默认使用 ChatTongyi
        logger.info(f"使用 DashScope LLM: model={settings.model_name}")
        return ChatTongyi(
            model=settings.model_name,
            temperature=temp,
        )


# ============================================================
# 结构化输出模型定义
# ============================================================

class IntentAnalysisOutput(BaseModel):
    """意图分析结构化输出"""
    intent: str = Field(description="意图类型: copy_writing / copy_analysis / simple_chat")
    confidence: float = Field(description="置信度 0-1")
    extracted_topic: Optional[str] = Field(default=None, description="提取的主题")
    reasoning: str = Field(description="判断理由")


class ProofreadOutput(BaseModel):
    """评测结构化输出"""
    is_passed: bool = Field(description="是否通过评测")
    quality_score: float = Field(description="质量评分 1-10")
    feedback: str = Field(description="反馈建议")
    refined_copy: str = Field(description="润色后的文案")


class FieldItem(BaseModel):
    字段: str
    解析: str


class BreakdownStructuredOutput(BaseModel):
    """breakdown 节点结构化输出（严格 JSON schema）。"""

    model_config = {"populate_by_name": True}

    doc_goal: list[FieldItem] = Field(alias="一、文案目标")
    macro: list[FieldItem] = Field(alias="二、宏观结构")
    drive: list[FieldItem] = Field(alias="三、心理驱动")
    expression: list[FieldItem] = Field(alias="四、表达方式")
    trust: list[FieldItem] = Field(alias="五、信任与风险处理")
    friction: list[FieldItem] = Field(alias="六、摩擦分析")
    tone: list[FieldItem] = Field(alias="七、语气参数（1–5）")
    cta: list[FieldItem] = Field(alias="八、CTA 评估")
    summary: str = Field(alias="总结该文案成功的结构性原因")


class TenMoveGenOutput(BaseModel):
    """Ten-move 生成结构化输出。"""

    filled_schema: dict[str, Any]
    final_copy_text: str


class ReverseConfigOutput(BaseModel):
    """逆向工程结构化输出（匹配 inv_prompt 约束）。"""

    medium_guess: str
    move_sequence: list[int]
    omitted_moves: list[int]
    move_fusion_notes: str
    persuasion_strategy: dict[str, Any]
    style_constraints: dict[str, Any]
    reusable_system_prompt: str


# ============================================================
# 意图分析节点
# ============================================================

INTENT_ANALYSIS_PROMPT = """你是一个意图分析助手，负责判断用户输入的意图类型。

## 意图类型说明：
1. **copy_writing** - 文案仿写/创作：用户提供了参考文案并希望仿写，或者用户明确要求创作文案
2. **copy_analysis** - 文案分析：用户只是想分析/拆解一段文案的结构，不需要创作
3. **simple_chat** - 普通聊天：用户只是闲聊，问问题，不涉及文案相关

## 判断规则：
- 如果用户输入包含"仿写"、"帮我写"、"创作"、"生成文案"等词汇 → copy_writing
- 如果用户输入包含"分析"、"拆解"、"看看结构"等词汇，且有文案内容 → copy_analysis
- 如果用户只是提供了一段文案（无明确指令），默认为 copy_writing
- 如果用户在闲聊、问问题 → simple_chat

请严格按 JSON 格式输出。"""


def intent_analysis_node(state: AgentState) -> dict[str, Any]:
    """
    意图分析节点 - 判断用户意图类型
    
    Returns:
        intent_result: 意图分析结果
    """
    logger.info("🔍 执行意图分析节点 (Intent Analysis Node)")
    
    user_input = state["user_input"]
    user_instructions = state.get("user_instructions", "")
    
    # 构建分析内容
    analysis_content = f"用户输入：{user_input}"
    if user_instructions:
        analysis_content += f"\n用户指令：{user_instructions}"
    
    try:
        llm = get_llm(temperature=0.0)  # 意图分析用低温度
        structured_llm = llm.with_structured_output(IntentAnalysisOutput)
        
        result = structured_llm.invoke([
            SystemMessage(content=INTENT_ANALYSIS_PROMPT),
            HumanMessage(content=analysis_content),
        ])
        
        # 映射意图类型
        intent_map = {
            "copy_writing": IntentType.COPY_WRITING,
            "copy_analysis": IntentType.COPY_ANALYSIS,
            "simple_chat": IntentType.SIMPLE_CHAT,
        }
        intent_type = intent_map.get(result.intent, IntentType.SIMPLE_CHAT)
        
        intent_result = IntentResult(
            intent=intent_type,
            confidence=result.confidence,
            extracted_topic=result.extracted_topic,
            reasoning=result.reasoning,
        )
        
        logger.info(f"✅ 意图分析完成: intent={intent_type.value}, confidence={result.confidence}")
        
        return {
            "intent_result": intent_result.model_dump(),
        }
        
    except Exception as e:
        logger.exception(f"❌ 意图分析节点执行失败: {e}")
        # 降级处理：根据关键词简单判断
        fallback_intent = IntentType.COPY_WRITING  # 默认文案创作
        keywords_chat = ["你好", "什么是", "怎么", "为什么", "帮我"]
        if any(kw in user_input for kw in keywords_chat) and len(user_input) < 50:
            fallback_intent = IntentType.SIMPLE_CHAT
        
        return {
            "intent_result": IntentResult(
                intent=fallback_intent,
                confidence=0.5,
                reasoning=f"降级处理: {e}",
            ).model_dump(),
        }


# ============================================================
# 解析节点（使用结构化输出优化）
# ============================================================

def breakdown_node(state: AgentState) -> dict[str, Any]:
    """
    解析节点 - 对用户输入进行结构化拆解
    
    用于检测用户输入是否为文案结构，如果是则进行解析
    注意：不使用 with_structured_output（ChatTongyi 对 list content 兼容性差），
    改用普通 invoke + 手动 JSON 解析。
    """
    logger.info("📝 执行解析节点 (Breakdown Node)")
    
    user_input = state["user_input"]
    iteration_count = state.get("iteration_count", 0)
    _dbg("breakdown.input", {"user_input": user_input[:1000]})
    
    try:
        llm = get_llm(temperature=0.0)
        
        # 普通调用（不用 with_structured_output，避免 ChatTongyi 解析 list content 报错）
        response = llm.invoke(
            [
                SystemMessage(content=COPYWRITING_BREAKDOWN_PROMPT),
                HumanMessage(content=user_input),
            ]
        )
        
        # 兼容 content 为 list 的情况
        raw_text = _to_text(getattr(response, "content", response))
        if settings.debug_llm_io:
            _dbg("breakdown.llm_raw", raw_text[:2000])
        
        # 手动提取 JSON
        breakdown_json = _extract_json(raw_text)
        if settings.debug_llm_io:
            _dbg("breakdown.parsed_json", breakdown_json)
        
        # 判断是否为有效文案结构
        is_valid = bool(breakdown_json) and "一、文案目标" in breakdown_json
        
        # 提取结构类型
        structure_type = None
        if is_valid and "二、宏观结构" in breakdown_json:
            for item in breakdown_json.get("二、宏观结构", []):
                if isinstance(item, dict) and "是" in item.get("解析", "") and "否" not in item.get("解析", ""):
                    structure_type = item.get("字段")
                    break
        
        # 提取总结
        summary = breakdown_json.get("总结该文案成功的结构性原因", "")
        
        result = BreakdownResult(
            raw_json=breakdown_json,
            is_valid_copy=is_valid,
            structure_type=structure_type,
            summary=summary,
        )
        
        logger.info(f"✅ 解析完成: is_valid={is_valid}, structure_type={structure_type}")
        
        return {
            "breakdown_result": result.model_dump(),
            "iteration_count": iteration_count,
        }
        
    except Exception as e:
        logger.exception(f"❌ 解析节点执行失败: {e}")
        return {
            "breakdown_result": BreakdownResult(
                is_valid_copy=False,
                summary=f"解析失败: {e}",
            ).model_dump(),
            "iteration_count": iteration_count,
            "error": str(e),
        }


def _extract_json(text: str) -> dict:
    """从文本中提取 JSON 对象"""
    import re
    
    # 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试从代码块中提取
    json_pattern = r"```(?:json)?\s*([\s\S]*?)```"
    matches = re.findall(json_pattern, text)
    if matches:
        try:
            return json.loads(matches[0])
        except json.JSONDecodeError:
            pass
    
    # 尝试查找 { } 包围的内容
    brace_pattern = r"\{[\s\S]*\}"
    match = re.search(brace_pattern, text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    
    logger.warning("无法从响应中提取JSON，返回空字典")
    return {}


def _extract_json_and_tail(text: str) -> tuple[dict, str]:
    """提取第一个 JSON 对象，并返回 (json_obj, tail_text)。"""
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start < 0:
        return {}, text
    try:
        obj, end = decoder.raw_decode(text[start:])
        tail = text[start + end :].lstrip()
        if isinstance(obj, dict):
            return obj, tail
        return {}, text
    except Exception:
        return _extract_json(text), ""


def _resolve_target_duration_sec(schema_ir: dict[str, Any] | None, user_instructions: str | None) -> int:
    """
    Resolve target duration (seconds) for spoken scripts.

    Priority:
    - schema_ir.spoken_constraints.target_duration_sec (if valid)
    - parse from user_instructions like "60秒"
    - default 60
    """
    target_duration_sec = 60
    try:
        if schema_ir:
            v0 = (schema_ir.get("spoken_constraints") or {}).get("target_duration_sec")
            if isinstance(v0, int) and 10 <= v0 <= 180:
                target_duration_sec = v0
    except Exception:
        pass
    if user_instructions:
        m = re.search(r"(\d{2,3})\s*秒", user_instructions)
        if m:
            try:
                v = int(m.group(1))
                if 10 <= v <= 180:
                    target_duration_sec = v
            except ValueError:
                pass
    return target_duration_sec


def _apply_move_plan_to_schema(schema_ir: dict[str, Any], move_ids: list[int]) -> dict[str, Any]:
    """Reorder/filter move_sequence according to move_ids (keep original move templates)."""
    by_id: dict[int, dict[str, Any]] = {}
    for m in schema_ir.get("move_sequence", []) or []:
        try:
            mid = int(m.get("move_id"))
        except Exception:
            continue
        by_id[mid] = dict(m)
    new_seq: list[dict[str, Any]] = []
    for mid in move_ids:
        if mid in by_id:
            new_seq.append(by_id[mid])
    out = dict(schema_ir)
    out["move_sequence"] = new_seq
    return out


def move_plan_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """
    Dynamic move planning node.

    Goal: let the LLM decide which moves to use, in what order, and how to fuse them,
    instead of relying on a fixed prune template.
    """
    logger.info("🧭 执行 Move 规划节点 (Move Plan Node)")

    if not getattr(settings, "enable_move_planner", True):
        logger.info("Move planner disabled; skipping.")
        return {"move_plan": None}

    user_input = state.get("user_input", "")
    user_instructions = state.get("user_instructions") or ""
    schema_ir = state.get("schema_ir") or default_ten_move_schema()
    breakdown_result = state.get("breakdown_result") or {}
    reverse_config = state.get("reverse_config") or {}

    target_duration_sec = _resolve_target_duration_sec(schema_ir, user_instructions)

    breakdown_json = ""
    try:
        breakdown_json = json.dumps(breakdown_result.get("raw_json") or {}, ensure_ascii=False)
    except Exception:
        breakdown_json = ""
    reverse_json = ""
    try:
        reverse_json = json.dumps(reverse_config or {}, ensure_ascii=False)
    except Exception:
        reverse_json = ""

    prompt = TEN_MOVE_LIVE_PLAN_PROMPT
    prompt = prompt.replace("{TARGET_DURATION_SEC}", str(target_duration_sec))
    prompt = prompt.replace("{USER_INPUT}", user_input)
    prompt = prompt.replace("{USER_INSTRUCTIONS}", user_instructions)
    prompt = prompt.replace("{BREAKDOWN_JSON}", breakdown_json)
    prompt = prompt.replace("{REVERSE_CONFIG_JSON}", reverse_json)

    if settings.debug_llm_io:
        _dbg("move_plan.input", prompt[:4000])

    try:
        llm = get_llm(temperature=0.2)
        response = llm.invoke([SystemMessage(content=prompt)], config=config)
        raw_text = _to_text(getattr(response, "content", response))
        if settings.debug_llm_io:
            _dbg("move_plan.llm_raw", raw_text[:2000])

        plan = _extract_json(raw_text) or {}
    except Exception as e:
        logger.warning(f"⚠️ move_plan 规划失败，降级到固定裁剪: {e}")
        return {"move_plan": None}

    # Normalize / validate
    move_ids_raw = plan.get("move_ids") or []
    move_ids: list[int] = []
    try:
        for x in move_ids_raw:
            try:
                i = int(x)
            except Exception:
                continue
            if 1 <= i <= 10 and i not in move_ids:
                move_ids.append(i)
    except Exception:
        move_ids = []

    # Hard requirements
    for required in (1, 4, 9):
        if required not in move_ids:
            move_ids.append(required)

    # Keep a sane default ordering if model output is empty/garbled
    if not move_ids:
        move_ids = [1, 3, 4, 7, 9, 10]

    budgets = plan.get("move_budgets_sec") or {}
    normalized_budgets: dict[str, int] = {}
    # If budgets missing, allocate proportional defaults.
    if isinstance(budgets, dict) and budgets:
        for mid in move_ids:
            v = budgets.get(str(mid))
            if v is None:
                v = budgets.get(mid)  # type: ignore[call-arg]
            try:
                iv = int(v)
            except Exception:
                iv = 0
            if iv > 0:
                normalized_budgets[str(mid)] = iv
    if not normalized_budgets:
        base = max(10, target_duration_sec)
        per = max(3, int(base / max(1, len(move_ids))))
        for mid in move_ids:
            normalized_budgets[str(mid)] = per

    omitted = [i for i in range(1, 11) if i not in move_ids]
    plan_out = {
        "target_duration_sec": int(plan.get("target_duration_sec") or target_duration_sec),
        "move_ids": move_ids,
        "move_budgets_sec": normalized_budgets,
        "omitted_move_ids": plan.get("omitted_move_ids") or omitted,
        "fusion_notes": str(plan.get("fusion_notes") or "").strip(),
        "risk_notes": str(plan.get("risk_notes") or "").strip(),
    }

    logger.info(f"✅ Move 规划完成: moves={move_ids}")
    return {"move_plan": plan_out}


# ============================================================
# 写作节点（支持流式输出）
# ============================================================

def writing_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """
    写作节点 - 基于 Ten-move schema IR 生成直播带货口播文案
    
    注意：不使用 with_structured_output（ChatTongyi 对 list content 兼容性差），
    改用普通 invoke + 手动解析两段输出（FILLED_SCHEMA_JSON + FINAL_COPY_TEXT）。
    """
    logger.info("✍️ 执行写作节点 (Writing Node)")
    
    user_input = state["user_input"]
    user_instructions = state.get("user_instructions", "")
    breakdown_result = state.get("breakdown_result")
    proofread_result = state.get("proofread_result")
    iteration_count = state.get("iteration_count", 0)

    # 规划（IR）：构建 Ten-move schema（如果调用方传入则优先使用）
    base_schema_ir = state.get("schema_ir") or default_ten_move_schema()

    # 目标时长
    target_duration_sec = _resolve_target_duration_sec(base_schema_ir, user_instructions)

    # move 规划（动态优先；失败/关闭则确定性裁剪）
    move_plan = state.get("move_plan") or {}
    move_ids = move_plan.get("move_ids") if isinstance(move_plan, dict) else None
    if isinstance(move_ids, list) and move_ids:
        try:
            move_ids_int = [int(x) for x in move_ids]
            schema_ir = _apply_move_plan_to_schema(base_schema_ir, move_ids_int)
        except Exception:
            schema_ir = prune_moves_for_live_stream(base_schema_ir, target_duration_sec=target_duration_sec)
    else:
        schema_ir = prune_moves_for_live_stream(base_schema_ir, target_duration_sec=target_duration_sec)

    # 构建写作上下文（供模型填充 schema + 渲染口播）
    context_parts: list[str] = []
    context_parts.append(f"【用户输入/参考素材】\n{user_input}")
    if user_instructions:
        context_parts.append(f"【写作指令】\n{user_instructions}")
    if breakdown_result and breakdown_result.get("is_valid_copy"):
        context_parts.append(
            f"【结构拆解（供参考，不必原样复刻）】\n{json.dumps(breakdown_result.get('raw_json', {}), ensure_ascii=False)}"
        )
    reverse_config = state.get("reverse_config")
    if reverse_config:
        context_parts.append(
            f"【逆向配置（供参考，可适当吸收）】\n{json.dumps(reverse_config, ensure_ascii=False)}"
        )
    if move_plan:
        try:
            context_parts.append(
                f"【Move 规划（必须优先遵循，用于动态结构）】\n{json.dumps(move_plan, ensure_ascii=False)}"
            )
        except Exception:
            pass
    if proofread_result and iteration_count > 0:
        feedback = proofread_result.get("feedback", "")
        if feedback:
            context_parts.append(f"【上一轮评测反馈，请据此改进】\n{feedback}")

    schema_text = json.dumps(schema_ir, ensure_ascii=False)
    gen_prompt = TEN_MOVE_LIVE_GEN_PROMPT.replace("{PASTE_SCHEMA_JSON_HERE}", schema_text)
    user_content = gen_prompt + "\n\n" + "\n\n".join(context_parts)
    if settings.debug_llm_io:
        _dbg("writing.input", user_content)
    
    try:
        llm = get_llm()
        
        # 普通调用（不用 with_structured_output，避免 ChatTongyi 解析 list content 报错）
        response = llm.invoke(
            [
                SystemMessage(content=COPYWRITING_PROMPT),
                HumanMessage(content=user_content),
            ],
            config=config,
        )
        
        # 兼容 content 为 list 的情况
        raw_text = _to_text(getattr(response, "content", response))
        if settings.debug_llm_io:
            _dbg("writing.llm_raw", raw_text[:3000])
        
        # 手动解析两段输出：先提取 JSON（filled schema），剩余部分是 final copy
        filled_schema, tail_text = _extract_json_and_tail(raw_text)
        
        # 如果没解析到 JSON，用原始 schema_ir
        if not filled_schema:
            filled_schema = schema_ir
            tail_text = raw_text
        
        # 提取最终口播文案
        # 优先用 tail_text（JSON 之后的部分），如果为空则尝试从 move_sequence 拼接
        draft = tail_text.strip()
        
        # 去掉可能的标记前缀（如 "2) FINAL_COPY_TEXT" 或 "FINAL_COPY_TEXT:"）
        draft = re.sub(r"^[12]\)\s*FINAL_COPY_TEXT[:\s]*", "", draft, flags=re.IGNORECASE).strip()
        draft = re.sub(r"^FINAL_COPY_TEXT[:\s]*", "", draft, flags=re.IGNORECASE).strip()
        
        # 如果 draft 为空或太短，尝试从 filled_schema 的 move_sequence 拼接
        if len(draft) < 20:
            draft_from_moves = "\n".join(
                (m.get("content") or "").strip()
                for m in filled_schema.get("move_sequence", [])
                if (m.get("content") or "").strip()
            ).strip()
            if draft_from_moves:
                draft = draft_from_moves
        
        # 如果还是没有内容，说明模型可能没按格式输出，直接用 raw_text 去掉 JSON 部分
        if len(draft) < 20:
            # 尝试去掉 JSON 块后的内容
            no_json = re.sub(r"\{[\s\S]*?\}", "", raw_text, count=1).strip()
            if len(no_json) > 20:
                draft = no_json
        
        if settings.debug_llm_io:
            _dbg("writing.parsed_schema", filled_schema)
            _dbg("writing.parsed_copy", draft)
        
        new_iteration = iteration_count + 1
        
        logger.info(f"✅ 文案生成完成，长度: {len(draft)} 字符，迭代: {new_iteration}")
        
        return {
            "draft_copy": draft,
            "iteration_count": new_iteration,
            "schema_ir": filled_schema,
        }
        
    except Exception as e:
        logger.exception(f"❌ 写作节点执行失败: {e}")
        # 失败时也要递增迭代次数，防止无限循环
        return {
            "draft_copy": None,
            "iteration_count": iteration_count + 1,
            "error": str(e),
            "schema_ir": schema_ir,
        }


# ============================================================
# 评测节点（使用结构化输出）
# ============================================================

def proofread_node(state: AgentState, config: Optional[RunnableConfig] = None) -> dict[str, Any]:
    """
    评测节点 - 对生成的文案进行质量评测
    
    使用 with_structured_output 确保返回格式正确
    """
    logger.info("🔍 执行评测节点 (Proofread Node)")
    
    draft_copy = state.get("draft_copy")
    iteration_count = state.get("iteration_count", 0)
    
    if not draft_copy:
        logger.warning("⚠️ 无文案可评测")
        # 达到迭代上限时强制结束
        if iteration_count >= settings.max_iterations:
            return {
                "proofread_result": ProofreadResult(
                    is_passed=True,
                    feedback="无文案内容，达到最大迭代次数",
                    quality_score=0.0,
                ).model_dump(),
                "final_copy": "文案生成失败，请检查配置后重试。",
            }
        return {
            "proofread_result": ProofreadResult(
                is_passed=False,
                feedback="无文案内容可评测",
                quality_score=0.0,
            ).model_dump(),
        }
    
    try:
        llm = get_llm(temperature=0.0)
        structured_llm = llm.with_structured_output(ProofreadOutput)
        
        result = structured_llm.invoke([
            SystemMessage(content=COPYWRITING_PROOFREADER_PROMPT),
            HumanMessage(content=draft_copy),
        ])
        
        is_passed = result.is_passed
        quality_score = result.quality_score
        
        # 评分 >= 7 视为通过
        if quality_score >= 7.0:
            is_passed = True
        
        proofread_result = ProofreadResult(
            is_passed=is_passed,
            feedback=result.feedback,
            refined_copy=result.refined_copy,
            quality_score=quality_score,
        )
        
        logger.info(f"✅ 评测完成: is_passed={is_passed}, score={quality_score}, iteration={iteration_count}")
        
        # 如果通过或达到最大迭代次数，设置最终文案
        final_copy = None
        if is_passed or iteration_count >= settings.max_iterations:
            final_copy = result.refined_copy or draft_copy
            if not is_passed:
                logger.warning(f"⚠️ 达到最大迭代次数 {settings.max_iterations}，强制输出")
        
        out: dict[str, Any] = {
            "proofread_result": proofread_result.model_dump(),
            "final_copy": final_copy,
        }

        # 如果产生最终输出，则统一落盘（production + analysis + learning）
        if final_copy and not state.get("artifact_paths"):
            try:
                thread_id = "default"
                if config:
                    thread_id = (
                        config.get("configurable", {}).get("thread_id")  # type: ignore[union-attr]
                        or "default"
                    )
                project_root = os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..")
                )
                payload = {
                    "user_input": state.get("user_input"),
                    "user_instructions": state.get("user_instructions"),
                    "breakdown_result": state.get("breakdown_result"),
                    "analysis_report": state.get("analysis_report"),
                    "reverse_config": state.get("reverse_config"),
                    "schema_ir": state.get("schema_ir"),
                    "proofread_result": proofread_result.model_dump(),
                    "final_copy": final_copy,
                }
                paths = persist_run_artifacts(
                    project_root, thread_id=thread_id, payload=payload
                )
                out["artifact_paths"] = {
                    "run_json": paths.run_json,
                    "runs_jsonl": paths.runs_jsonl,
                }
            except Exception as e2:
                logger.warning(f"⚠️ 落盘失败（不影响主流程）: {e2}")

        return out
        
    except Exception as e:
        logger.exception(f"❌ 评测节点执行失败: {e}")
        # 发生错误时，如果达到迭代上限，直接使用草稿
        if iteration_count >= settings.max_iterations:
            return {
                "proofread_result": ProofreadResult(
                    is_passed=True,
                    feedback=f"评测出错: {e}，使用原始文案",
                    quality_score=5.0,
                ).model_dump(),
                "final_copy": draft_copy,
            }
        return {
            "proofread_result": ProofreadResult(
                is_passed=False,
                feedback=f"评测出错: {e}",
                quality_score=0.0,
            ).model_dump(),
            "error": str(e),
        }


# ============================================================
# analysis chain: report node (MVP: no extra LLM call)
# ============================================================

def analysis_report_node(state: AgentState) -> dict[str, Any]:
    """从 breakdown_result 生成面向口播的结构报告（MVP）。"""
    logger.info("📊 执行分析报告节点 (Analysis Report Node)")
    br = state.get("breakdown_result") or {}
    raw = br.get("raw_json") or {}
    summary = br.get("summary") or raw.get("总结该文案成功的结构性原因") or ""
    report = "【结构分析报告（口播向）】\n"
    if summary:
        report += f"- 结构性原因：{summary}\n"
    if raw:
        report += "\n【结构拆解 JSON】\n" + json.dumps(raw, ensure_ascii=False, indent=2)
    return {"analysis_report": report}


# ============================================================
# learning chain: reverse engineer node (LLM)
# ============================================================

def reverse_engineer_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """
    对输入参考文案做逆向工程，产出隐藏配置 JSON。
    
    注意：不使用 with_structured_output（ChatTongyi 对 list content 兼容性差），
    改用普通 invoke + 手动 JSON 解析。
    """
    logger.info("🧠 执行逆向工程节点 (Reverse Engineer Node)")
    target_copy = state.get("user_input", "")
    prompt = TEN_MOVE_LIVE_INV_PROMPT.replace("{PASTE_TARGET_COPY_HERE}", target_copy)
    if settings.debug_llm_io:
        _dbg("reverse.input", prompt)
    try:
        llm = get_llm(temperature=0.0)
        
        # 普通调用（不用 with_structured_output，避免 ChatTongyi 解析 list content 报错）
        response = llm.invoke([SystemMessage(content=prompt)], config=config)
        
        # 兼容 content 为 list 的情况
        raw_text = _to_text(getattr(response, "content", response))
        if settings.debug_llm_io:
            _dbg("reverse.llm_raw", raw_text[:2000])
        
        # 手动提取 JSON
        cfg = _extract_json(raw_text)
        if settings.debug_llm_io:
            _dbg("reverse.parsed_config", cfg)
        
        return {"reverse_config": cfg}
    except Exception as e:
        logger.exception(f"❌ 逆向工程失败: {e}")
        return {"reverse_config": {"error": str(e)}}


# ============================================================
# 简单聊天节点
# ============================================================

def simple_chat_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """
    简单聊天节点 - 直接 LLM 回复
    """
    logger.info("💬 执行简单聊天节点 (Simple Chat Node)")
    
    user_input = state["user_input"]
    
    try:
        llm = get_llm()
        
        response = llm.invoke(
            [HumanMessage(content=user_input)],
            config=config,
        )
        
        # 兼容 content 为 list 的情况
        content = _to_text(getattr(response, "content", response))
        
        logger.info(f"✅ 聊天回复完成，长度: {len(content)} 字符")
        
        return {
            "final_copy": content,
        }
        
    except Exception as e:
        logger.exception(f"❌ 聊天节点执行失败: {e}")
        return {
            "final_copy": f"抱歉，处理您的请求时出错了: {e}",
            "error": str(e),
        }


# ============================================================
# 路由函数
# ============================================================

def route_by_intent(state: AgentState) -> str:
    """
    根据意图路由到不同的处理流程
    
    Returns:
        "copy_flow": 文案创作流程
        "analysis_flow": 文案分析流程
        "chat_flow": 简单聊天流程
    """
    intent_result = state.get("intent_result", {})
    intent = intent_result.get("intent", IntentType.SIMPLE_CHAT.value)
    
    logger.info(f"🔀 路由决策: intent={intent}")
    
    if intent == IntentType.COPY_WRITING.value:
        return "copy_flow"
    elif intent == IntentType.COPY_ANALYSIS.value:
        return "analysis_flow"
    else:
        return "chat_flow"


def should_continue(state: AgentState) -> str:
    """
    条件路由函数 - 决定是继续迭代还是结束
    
    Returns:
        "continue": 回到写作节点继续迭代
        "end": 结束工作流，输出最终文案
    """
    proofread_result = state.get("proofread_result", {})
    iteration_count = state.get("iteration_count", 0)
    final_copy = state.get("final_copy")
    
    # 如果已有最终文案，结束
    if final_copy:
        logger.info("✅ 评测通过或达到最大迭代，结束工作流")
        return "end"
    
    # 如果达到最大迭代次数，结束
    if iteration_count >= settings.max_iterations:
        logger.warning(f"⚠️ 达到最大迭代次数 {settings.max_iterations}，强制结束")
        return "end"
    
    # 如果评测未通过，继续迭代
    if proofread_result and not proofread_result.get("is_passed", False):
        logger.info(f"🔄 评测未通过，继续迭代 ({iteration_count}/{settings.max_iterations})")
        return "continue"
    
    # 默认结束
    return "end"
