"""Skeleton v2 pipeline nodes (move_step4 landing).

Pipeline (v2):
preprocess → analyst → normalizer → entity_mapper → creator → qc → (targeted rewrite loop) → proofread
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from src.agent.codebooks_v0 import (
    FEWSHOT_ANALYST_V0,
    INTENT_CODEBOOK_V0,
    MICRO_RHETORIC_CODEBOOK_V0,
)
from src.agent.nodes import _dbg, _extract_json, _to_text, get_llm
from src.agent.skeleton_v2 import SkeletonV2
from src.agent.state import AgentState
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger(__name__)


_PRICE_RE = re.compile(r"(?P<num>\d+(?:\.\d+)?)\s*(?:元|块|￥)")
_NUM_TOKEN_RE = re.compile(r"\d+(?:\.\d+)?%?|\d+倍|[A-Za-z]{2,}|mg|g|kg|ml|mL|L|℃")


def _infer_v2_mode(state: AgentState) -> str:
    """
    v2 dual-mode inference:
    - transfer: caller provided new_product_specs (cross-category / new product grounding)
    - imitate: no new_product_specs (same-product imitation)
    """
    specs = state.get("new_product_specs")
    return "transfer" if isinstance(specs, dict) and len(specs) > 0 else "imitate"


def _split_sentences_zh(text: str) -> list[str]:
    parts = re.split(r"[。！？!?;\n]+", text)
    return [p.strip() for p in parts if p and p.strip()]


def preprocess_v2_node(state: AgentState) -> dict[str, Any]:
    """Step0: deterministic preprocessing (entities + risk lexicon hits + sentence split)."""
    logger.info("🧰 [v2] Preprocess Node")
    source = state.get("user_input") or ""
    v2_mode = _infer_v2_mode(state)

    # Candidate entities (very lightweight v0 heuristic)
    entities: list[str] = []
    # prices
    for m in _PRICE_RE.finditer(source):
        tok = m.group(0).strip()
        if tok and tok not in entities:
            entities.append(tok)
    # bracketed terms, hashtags, obvious brand-ish tokens
    for tok in re.findall(r"[#＃][\w\u4e00-\u9fff]{2,}", source):
        if tok not in entities:
            entities.append(tok)
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", source):
        if tok not in entities:
            entities.append(tok)

    risk_terms = ["最", "第一", "唯一", "100%", "百分百", "绝对", "包治", "根治", "永久", "无副作用", "治愈", "特效"]
    risk_hits = [t for t in risk_terms if t in source]

    sentences = _split_sentences_zh(source)

    # v2 imitate-mode: auto-extract minimal specs for grounding/QC
    auto_specs: dict[str, Any] | None = None
    if v2_mode == "imitate":
        numeric_from_source = list(dict.fromkeys(_NUM_TOKEN_RE.findall(source)))
        prices_from_source = list(
            dict.fromkeys(
                [m.group(0).strip() for m in _PRICE_RE.finditer(source) if m.group(0) and m.group(0).strip()]
            )
        )
        auto_specs = {
            "__auto_extracted_from_source": True,
            "mode": "imitate",
            "source_numbers": numeric_from_source,
            "source_prices": prices_from_source,
            "source_excerpt": source[:1200],
        }

    out = {
        "v2_mode": v2_mode,
        "source_entities": entities,
        "risk_lexicon_hits": risk_hits,
        "sentences": sentences,
    }
    if settings.debug_node_io:
        _dbg("v2.preprocess.out", out)
    if v2_mode == "imitate" and not (isinstance(state.get("new_product_specs"), dict) and len(state.get("new_product_specs") or {}) > 0):
        return {"preprocess_result": out, "new_product_specs": auto_specs}
    return {"preprocess_result": out}


def _render_codebook_block() -> str:
    intents = "\n".join([f"- {k}: {v}" for k, v in INTENT_CODEBOOK_V0.items()])
    rhet = "\n".join([f"- {k}: {v}" for k, v in MICRO_RHETORIC_CODEBOOK_V0.items()])
    return f"""## Intent Codebook (PrimaryIntent)
{intents}

## Micro-Rhetoric Codebook (tag)
{rhet}
"""


def analyst_v2_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Step1: LLM analyst produces Skeleton v2 draft."""
    logger.info("🧠 [v2] Analyst Node")
    source = state.get("user_input") or ""
    preprocess = state.get("preprocess_result") or {}
    v2_mode = str(preprocess.get("v2_mode") or _infer_v2_mode(state))
    target_duration_sec = None
    try:
        target_duration_sec = int(
            (state.get("schema_ir") or {}).get("spoken_constraints", {}).get("target_duration_sec")
            or 0
        )
    except Exception:
        target_duration_sec = None

    fewshot = FEWSHOT_ANALYST_V0[0]
    fewshot_block = json.dumps(fewshot["expected_skeleton"], ensure_ascii=False)

    task_line = (
        "你的任务：忽略原文在卖什么，提取可迁移的说服逻辑骨架（Skeleton v2），用于后续跨品类仿写。"
        if v2_mode == "transfer"
        else "你的任务：在不改变原文品类/关键信息的前提下，提取可复用的说服逻辑骨架（Skeleton v2），用于同品类/同商品仿写。"
    )
    hint_rule = (
        "在 imitate 模式下：\n"
        "- 对 verification=hard 的点：mention_hints 必须尽量“可审计”，优先使用 source_fact 里的关键短 token（数字/单位/工艺词/原料名/地域名等）。\n"
        "- 对 verification=soft 的点：mention_hints 允许更抽象（场景/情绪/价值主张），不要求字面命中。\n"
        if v2_mode != "transfer"
        else "在 transfer 模式下：hard 点的 hints 需要可落到 specs 事实；soft 点的 hints 用于表达方向即可。"
    )

    prompt = f"""你是一个“口播文案 Skeleton v2 分析师（Analyst）”。
{task_line}

你必须遵守：
1) 只输出一个“纯 JSON 对象”，不得输出 markdown、解释文字。
2) primary_intent 必须从固定枚举选择：{list(INTENT_CODEBOOK_V0.keys())}
3) micro_rhetoric.tag 必须从固定枚举选择：{list(MICRO_RHETORIC_CODEBOOK_V0.keys())}
4) abstracted_template 必须“去产品化”，不得包含任何 source_entities（下面会给候选）。
5) move_id 使用 Ten-move 的宏 move_id（1-10）。你可以只输出其中 4-9 个关键 moves，但必须包含 1/4/9。
6) entity_slots 里的 source_default 可以引用原文实体，但必须写在 source_default 字段里；abstracted_template 禁止出现原文实体。
7) 你必须先从原文中抽取一个“信息账本 must_cover_points”，并为每个点标注：
   - point_id：使用数字字符串 "1","2","3"...（不要用 p1/p2）。
   - importance：使用小写枚举 p0/p1/p2 表示优先级：
       - p0：最终口播绝对不能漏（如配料/规格/关键证据/关键优惠/价格门槛/核心机制等）。
       - p1：强烈建议覆盖（增强说服力/减少疑虑）。
       - p2：可选（可融合/省略）。
   - verification：hard/soft（二选一）：
       - hard：事实型点（数字/价格/枚举/专有名词/规格），后续会做确定性验收。
       - soft：语义型点（场景/痛点/价值主张），后续默认只提示不 gate。
8) 每个 P0 点必须在 move_sequence 里“有落点”：要么在某个 move 的 entity_slots 里提供对应 source_default，要么在该 move 的 abstracted_template 中明确要求覆盖（但不得出现 source_entities）。
9) 每个 must_cover_point 必须给出 anchor_move_ids（建议放入哪些 move_id 承载该点；可为多个）。
10) {hint_rule}

输出结构（Skeleton v2）最小要求：
{{
  "meta": {{"schema_version":"skeleton_v2","medium":"live_stream","language":"zh","target_duration_sec": {target_duration_sec or 60}}},
  "codebook_refs": {{"intent_codebook_version":"intent_codebook_v0","rhetoric_codebook_version":"micro_rhetoric_codebook_v0"}},
  "source_entities": [...],
  "risk_lexicon_hits": [...],
  "must_cover_points": [
    {{
      "point_id": "1",
      "importance": "p0",
      "category": "ingredients/specs/offer/proof/process/scene/price",
      "verification": "hard",
      "source_fact": "原文事实（可含实体/数字，用于审计）",
      "abstract_requirement": "去实体、可迁移的覆盖要求（transfer-safe）",
      "mention_hints": ["2-5个短提示词（不得含source_entities）"],
      "anchor_move_ids": [4],
      "why_important": "一句话说明为什么重要"
    }}
  ],
  "move_sequence": [
    {{
      "move_id": 1,
      "primary_intent": "Attention",
      "secondary_intents": [],
      "micro_rhetoric": {{"tag":"Concessive_Reversal","note":"..."}},
      "emotional_beat": ["surprise","reassurance"],
      "abstracted_template": "...",
      "entity_slots": {{"slot_name": {{"source_default":"...","target_value":null,"fallback":null}}}},
      "constraints": {{"must_include_evidence": false, "must_include_scene": false, "must_include_price_or_offer": false, "must_have_clear_cta": false, "must_avoid_source_entities": true, "must_ground_numbers_in_specs": true}},
      "source_span": "（可选）原文片段"
    }}
  ],
  "global_constraints": {{}}
}}

{_render_codebook_block()}

### Few-shot（参考输出形态，不要抄原文实体）
示例原文：
{fewshot["source_copy"]}
示例输出骨架（片段）：
{fewshot_block}

### 本次输入
source_entities 候选：
{json.dumps(preprocess.get("source_entities") or [], ensure_ascii=False)}

预处理信息（供你发现关键事实/证据/规格，不要原句照抄）：
{json.dumps({"sentences": preprocess.get("sentences") or [], "risk_lexicon_hits": preprocess.get("risk_lexicon_hits") or []}, ensure_ascii=False)}

原文：
{source}
"""

    if settings.debug_llm_io:
        _dbg("v2.analyst.prompt", prompt[:4000])

    llm = get_llm(temperature=0.0)
    response = llm.invoke([SystemMessage(content=prompt)], config=config)
    raw_text = _to_text(getattr(response, "content", response))
    if settings.debug_llm_io:
        _dbg("v2.analyst.raw", raw_text[:2500])
    parsed = _extract_json(raw_text) or {}

    # Validate with Pydantic (best-effort). If it fails, keep dict and let normalizer repair.
    try:
        sk = SkeletonV2.model_validate(parsed).model_dump()
    except Exception as e:
        logger.warning(f"[v2] Analyst output validation failed; will normalize. err={e}")
        sk = parsed
    return {"skeleton_v2": sk}


def normalizer_v2_node(state: AgentState) -> dict[str, Any]:
    """Step1.5: deterministic/semideterministic normalization to stabilize IR."""
    logger.info("🧹 [v2] Normalizer Node")
    preprocess = state.get("preprocess_result") or {}
    source_entities: list[str] = preprocess.get("source_entities") or []
    sk = state.get("skeleton_v2") or {}

    # Basic structural repairs
    if not isinstance(sk, dict):
        sk = {}
    sk.setdefault("meta", {"schema_version": "skeleton_v2", "medium": "live_stream", "language": "zh"})
    sk.setdefault("codebook_refs", {"intent_codebook_version": "intent_codebook_v0", "rhetoric_codebook_version": "micro_rhetoric_codebook_v0"})
    sk["source_entities"] = list(dict.fromkeys([*source_entities, *(sk.get("source_entities") or [])]))
    sk["risk_lexicon_hits"] = list(dict.fromkeys([*(preprocess.get("risk_lexicon_hits") or []), *(sk.get("risk_lexicon_hits") or [])]))

    # Normalize must_cover_points (best-effort; keep it permissive)
    mcp = sk.get("must_cover_points") or []
    if not isinstance(mcp, list):
        mcp = []
    normalized_points: list[dict[str, Any]] = []
    seen_pid: set[str] = set()
    for i, p in enumerate(mcp):
        if not isinstance(p, dict):
            continue
        pid = str(p.get("point_id") or "").strip()
        if not pid:
            pid = str(i + 1)
        if pid in seen_pid:
            continue
        seen_pid.add(pid)
        importance = str(p.get("importance") or "p1").strip().lower()
        if importance not in ("p0", "p1", "p2"):
            # Backward-compat: accept legacy P0/P1/P2
            legacy = str(p.get("importance") or "").strip().upper()
            if legacy in ("P0", "P1", "P2"):
                importance = legacy.lower()
            else:
                importance = "p1"
        verification = str(p.get("verification") or "").strip().lower()
        if verification not in ("hard", "soft"):
            # Heuristic inference:
            # - any numeric/units/price/explicit enum token -> hard
            # - otherwise -> soft
            sf0 = str(p.get("source_fact") or "").strip()
            hints0 = p.get("mention_hints") or []
            hints_text = " ".join([str(x) for x in hints0]) if isinstance(hints0, list) else ""
            probe = (sf0 + "\n" + hints_text).strip()
            has_num = bool(_NUM_TOKEN_RE.findall(probe))
            has_price = ("元" in probe) or ("￥" in probe)
            has_enum = any(k in probe for k in ["口味", "原味", "芥末", "斯哈辣", "型号", "套餐"])
            verification = "hard" if (has_num or has_price or has_enum) else "soft"
        abstract_req = str(p.get("abstract_requirement") or "").strip()
        if not abstract_req:
            abstract_req = str(p.get("source_fact") or "").strip()
        for ent in source_entities:
            if ent:
                abstract_req = abstract_req.replace(ent, "【占位】")
        hints = p.get("mention_hints") or []
        if not isinstance(hints, list):
            hints = []
        clean_hints: list[str] = []
        for h in hints:
            hs = str(h or "").strip()
            if not hs:
                continue
            for ent in source_entities:
                if ent and ent in hs:
                    hs = hs.replace(ent, "【占位】")
            if hs and hs not in clean_hints:
                clean_hints.append(hs)
        normalized_points.append(
            {
                "point_id": pid,
                "importance": importance,
                "category": (str(p.get("category") or "").strip() or None),
                "verification": verification,
                "source_fact": (str(p.get("source_fact") or "").strip() or None),
                "abstract_requirement": abstract_req,
                "mention_hints": clean_hints,
                "anchor_move_ids": [
                    j
                    for j in [
                        int(x)
                        for x in (p.get("anchor_move_ids") or [])
                        if str(x).strip().isdigit()
                    ]
                    if 1 <= j <= 10
                ]
                if isinstance(p.get("anchor_move_ids"), list)
                else [],
                "why_important": (str(p.get("why_important") or "").strip() or None),
            }
        )
    sk["must_cover_points"] = normalized_points

    seq = sk.get("move_sequence") or []
    if not isinstance(seq, list):
        seq = []

    # Keep only valid move_id [1..10], de-dup by move_id preserving order
    dedup: list[dict[str, Any]] = []
    seen: set[int] = set()
    for m in seq:
        if not isinstance(m, dict):
            continue
        try:
            mid = int(m.get("move_id"))
        except Exception:
            continue
        if not (1 <= mid <= 10):
            continue
        if mid in seen:
            continue
        seen.add(mid)
        m["move_id"] = mid
        dedup.append(m)
    seq = dedup

    # Ensure required moves exist (1/4/9). Insert minimal stubs if missing.
    required = [1, 4, 9]
    have = {int(m.get("move_id")) for m in seq if isinstance(m, dict) and isinstance(m.get("move_id"), int)}
    for mid in required:
        if mid not in have:
            seq.insert(
                0 if mid == 1 else len(seq),
                {
                    "move_id": mid,
                    "primary_intent": "Attention" if mid == 1 else ("Value" if mid == 4 else "Conversion"),
                    "secondary_intents": [],
                    "micro_rhetoric": {"tag": "Low_Friction_CTA" if mid == 9 else "Scenario_Anchoring", "note": ""},
                    "emotional_beat": [],
                    "abstracted_template": "（待补全）",
                    "entity_slots": {},
                    "constraints": {},
                    "source_span": None,
                },
            )
    # De-entity templates: hard strip any source entity hits (v0 blunt)
    for m in seq:
        tpl = str(m.get("abstracted_template") or "")
        for ent in source_entities:
            if ent and ent in tpl:
                tpl = tpl.replace(ent, "【占位】")
        m["abstracted_template"] = tpl.strip()
        # Ensure constraints defaults exist
        cons = m.get("constraints") or {}
        if not isinstance(cons, dict):
            cons = {}
        cons.setdefault("must_avoid_source_entities", True)
        cons.setdefault("must_ground_numbers_in_specs", True)
        m["constraints"] = cons

    sk["move_sequence"] = seq
    sk.setdefault("global_constraints", {})

    # Validate again (best-effort)
    try:
        sk2 = SkeletonV2.model_validate(sk).model_dump()
        sk = sk2
    except Exception as e:
        logger.warning(f"[v2] Normalized skeleton still not fully valid (will continue). err={e}")

    return {"skeleton_v2": sk}


def entity_mapper_v2_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Step2: map entity slots to new product specs (hybrid v0: deterministic + LLM assist)."""
    logger.info("🧩 [v2] Entity Mapper Node")
    sk = state.get("skeleton_v2") or {}
    specs = state.get("new_product_specs") or {}
    preprocess = state.get("preprocess_result") or {}
    v2_mode = str(preprocess.get("v2_mode") or _infer_v2_mode(state))

    # Imitate-mode: keep same-product entities by default.
    # We map each slot key to its source_default (identity mapping) and skip LLM mapping.
    if v2_mode == "imitate" and isinstance(sk, dict):
        mapping: dict[str, str] = {}
        seq = sk.get("move_sequence") or []
        if isinstance(seq, list):
            for m in seq:
                if not isinstance(m, dict):
                    continue
                slots = m.get("entity_slots") or {}
                if not isinstance(slots, dict):
                    continue
                for slot_key, slot_val in slots.items():
                    if not isinstance(slot_key, str):
                        continue
                    if isinstance(slot_val, dict):
                        sd = slot_val.get("source_default")
                        if isinstance(sd, str) and sd.strip():
                            mapping.setdefault(slot_key, sd.strip())
        return {
            "entity_mapping": {
                "mapping_dictionary": mapping,
                "fallback_policy": "仿写模式：默认沿用原文实体（source_default），仅改写表达。",
            }
        }

    # Deterministic mapping for common slots if present
    mapping: dict[str, str] = {}
    if isinstance(specs, dict):
        for k in ["product_name", "category", "core_benefit", "offer", "cta_url", "target_audience"]:
            v = specs.get(k)
            if isinstance(v, str) and v.strip():
                mapping[k] = v.strip()

    # LLM assist: map skeleton entity_slots keys to best target expression
    prompt = f"""你是“实体槽位映射器（Entity Mapper）”。
输入：
1) Skeleton v2（含 entity_slots.source_default）
2) 新产品 specs（结构化事实）

你的任务：
- 输出 mapping_dictionary：将每个 slot 映射到新产品的对应表达（优先使用 specs 中的事实）。
- 若 specs 无对应信息，给出 fallback_policy（软着陆泛化表达），不要保留 source_default 原词，也不要编造数字/权威/疗效。

严格输出一个纯 JSON：
{{
  "mapping_dictionary": {{"slot_key": "mapped_value_or_generic"}},
  "fallback_policy": "一句话策略"
}}

source_entities（用于避免泄漏）：
{json.dumps(preprocess.get("source_entities") or [], ensure_ascii=False)}

specs：
{json.dumps(specs, ensure_ascii=False)}

skeleton_v2：
{json.dumps(sk, ensure_ascii=False)}
"""
    if settings.debug_llm_io:
        _dbg("v2.entity_mapper.prompt", prompt[:3500])
    # In imitate-mode, allow a bit more flexibility while still staying stable.
    llm = get_llm(temperature=0.0 if v2_mode == "transfer" else 0.1)
    resp = llm.invoke([SystemMessage(content=prompt)], config=config)
    raw = _to_text(getattr(resp, "content", resp))
    parsed = _extract_json(raw) or {}

    md = parsed.get("mapping_dictionary") if isinstance(parsed, dict) else {}
    if isinstance(md, dict):
        for k, v in md.items():
            if isinstance(k, str) and isinstance(v, str) and v.strip():
                mapping.setdefault(k.strip(), v.strip())

    out = {
        "mapping_dictionary": mapping,
        "fallback_policy": str(parsed.get("fallback_policy") or "").strip(),
    }
    return {"entity_mapping": out}


def creator_v2_node(state: AgentState, config: RunnableConfig) -> dict[str, Any]:
    """Step3: generate draft by moves; supports targeted rewrite using qc_report.failed_move_ids."""
    logger.info("✍️ [v2] Creator Node")
    sk = state.get("skeleton_v2") or {}
    specs = state.get("new_product_specs") or {}
    mapping = state.get("entity_mapping") or {}
    preprocess = state.get("preprocess_result") or {}
    v2_mode = str(preprocess.get("v2_mode") or _infer_v2_mode(state))
    qc = state.get("qc_report") or {}
    iteration_count = int(state.get("iteration_count", 0) or 0)
    clean_room = bool(state.get("clean_room") or False)

    failed_moves = []
    if isinstance(qc, dict):
        failed_moves = qc.get("failed_move_ids") or []
    if not isinstance(failed_moves, list):
        failed_moves = []

    hard_constraints = (
        """硬约束：
- 只能使用新产品 specs 与 mapping_dictionary 中的事实/表达；不得编造数字/权威/疗效。
- 严禁出现 source_entities（下方提供候选），不得泄漏原文品牌/品名/价格等。
- 每个 move 必须完成其 primary_intent 任务，并遵循 micro_rhetoric.tag（迁移策略，不是句式抄写）。"""
        if v2_mode == "transfer"
        else """硬约束：
- 保持原文品类/关键信息一致（例如产品/价格/优惠/规格等），但表达必须改写，避免大段原句复刻。
- 不得编造新的数字/权威/疗效；若出现数字，应来自 specs（仿写模式下 specs 由系统从原文自动抽取或用户提供）。
- 每个 move 必须完成其 primary_intent 任务，并遵循 micro_rhetoric.tag（策略迁移，不是句式抄写）。"""
    )

    must_cover_points = []
    if isinstance(sk, dict):
        must_cover_points = sk.get("must_cover_points") or []

    prompt = f"""你是“结构化口播创作者（Skeleton v2 Creator）”。
你必须按 skeleton_v2.move_sequence 的顺序，逐 move 输出口播内容，并最终拼接为 final_copy_text。

{hard_constraints}

覆盖硬约束（信息账本 must_cover_points）：
- 你必须覆盖所有 importance=p0 的点（不得遗漏）。
- 覆盖时允许换序/融合，但必须“说到”，且不得编造新的数字/权威/疗效。
- transfer 模式：只使用 abstract_requirement + specs/mapping_dictionary 的事实来满足覆盖；不得泄漏 source_entities。
- imitate 模式：允许保留原文事实（价格/规格/配料/数据等），但必须改写表达，避免原句复刻。
- 对 verification=hard 的点：coverage_map 里的 phrase 必须是你写进 final_copy_text 的一段“原样片段”（可直接复制 final_copy_text 里的原句/短语），用于后续确定性验收。
- 对 verification=soft 的点：coverage_map.phrase 允许是概括短语/意图说明（不要求字面命中），用于解释你如何表达了该点。

输出格式（严格，一个 JSON）：
{{
  "rendered_by_move": {{"1":"...","4":"...","9":"..."}},
  "coverage_map": {{
    "1": {{"covered": true, "move_id": 4, "phrase": "证据短句/概括短语（见上方规则）"}}
  }},
  "final_copy_text": "..."
}}

如果提供 failed_move_ids，则你只重写这些 move；其他 move 需保持不变（直接复用 previous_rendered_by_move）。

source_entities：
{json.dumps(preprocess.get("source_entities") or [], ensure_ascii=False)}

specs：
{json.dumps(specs, ensure_ascii=False)}

mapping_dictionary：
{json.dumps((mapping.get("mapping_dictionary") if isinstance(mapping, dict) else {}) or {}, ensure_ascii=False)}

fallback_policy：
{json.dumps((mapping.get("fallback_policy") if isinstance(mapping, dict) else "") or "", ensure_ascii=False)}

skeleton_v2：
{json.dumps(sk, ensure_ascii=False)}

must_cover_points：
{json.dumps(must_cover_points, ensure_ascii=False)}

failed_move_ids：
{json.dumps(failed_moves, ensure_ascii=False)}

previous_rendered_by_move（可能为空）：
{json.dumps((state.get("writing_meta") or {}).get("rendered_by_move") or {}, ensure_ascii=False)}

clean_room_mode：
{str(clean_room)}
"""
    if settings.debug_llm_io:
        _dbg("v2.creator.prompt", prompt[:4000])
    llm = get_llm()
    resp = llm.invoke([SystemMessage(content=prompt)], config=config)
    raw = _to_text(getattr(resp, "content", resp))
    if settings.debug_llm_io:
        _dbg("v2.creator.raw", raw[:2500])
    parsed = _extract_json(raw) or {}

    rendered_by_move = {}
    if isinstance(parsed, dict) and isinstance(parsed.get("rendered_by_move"), dict):
        rendered_by_move = {str(k): str(v).strip() for k, v in parsed["rendered_by_move"].items() if str(v).strip()}
    coverage_map = {}
    if isinstance(parsed, dict) and isinstance(parsed.get("coverage_map"), dict):
        # keep as-is but normalize a little
        for pid, v in parsed["coverage_map"].items():
            if not isinstance(pid, str):
                continue
            if not isinstance(v, dict):
                continue
            try:
                mid = int(v.get("move_id"))
            except Exception:
                mid = None
            coverage_map[pid.strip()] = {
                "covered": bool(v.get("covered") is True),
                "move_id": mid,
                "phrase": str(v.get("phrase") or "").strip(),
            }
    final_text = str(parsed.get("final_copy_text") or "").strip()
    if not final_text and rendered_by_move:
        # concatenate
        parts: list[str] = []
        for m in (sk.get("move_sequence") or []):
            try:
                mid = str(int(m.get("move_id")))
            except Exception:
                continue
            seg = rendered_by_move.get(mid, "").strip()
            if seg:
                parts.append(seg)
        final_text = "\n".join(parts).strip()

    new_iteration = iteration_count + 1
    return {
        "draft_copy": final_text,
        "iteration_count": new_iteration,
        "writing_meta": {
            "rendered_by_move": rendered_by_move,
            "coverage_map": coverage_map,
            "draft_len": len(final_text),
            "mode": "v2",
        },
    }


def qc_v2_node(state: AgentState) -> dict[str, Any]:
    """Step4: deterministic QC gate + feedback for targeted rewrite."""
    logger.info("🛡️ [v2] QC Node")
    draft = str(state.get("draft_copy") or "").strip()
    preprocess = state.get("preprocess_result") or {}
    specs = state.get("new_product_specs") or {}
    sk = state.get("skeleton_v2") or {}
    v2_mode = str(preprocess.get("v2_mode") or _infer_v2_mode(state))

    source_entities: list[str] = preprocess.get("source_entities") or []
    issues: list[str] = []
    failed_move_ids: list[int] = []

    # Leakage check (transfer-mode only). In imitate-mode we intentionally allow keeping source entities (prices/brands/etc.)
    leakage_hits: list[str] = []
    if v2_mode == "transfer":
        leakage_hits = [e for e in source_entities if e and e in draft]
        if leakage_hits:
            issues.append(f"泄漏源实体：{leakage_hits}")

    # Spec grounding check (v0 heuristic): any numeric-like tokens must appear in specs text
    specs_text = ""
    try:
        specs_text = json.dumps(specs, ensure_ascii=False)
    except Exception:
        specs_text = str(specs)
    numeric_tokens = list(dict.fromkeys(_NUM_TOKEN_RE.findall(draft)))
    suspicious = [t for t in numeric_tokens if t and t not in specs_text]
    if suspicious:
        issues.append(f"可能未锚定到 specs 的数值/符号：{suspicious}")

    # Compliance v0: absolute claims
    absolute_terms = ["第一", "唯一", "100%", "百分百", "绝对", "包治", "根治", "永久", "无副作用", "治愈", "特效"]
    abs_hits = [t for t in absolute_terms if t in draft]
    if abs_hits:
        issues.append(f"可能存在绝对化/违规表达：{abs_hits}")

    # Per-move checks (very lightweight): ensure required moves have content in rendered_by_move
    rendered = (state.get("writing_meta") or {}).get("rendered_by_move") or {}
    if isinstance(rendered, dict):
        for mid in (1, 4, 9):
            if not str(rendered.get(str(mid), "")).strip():
                issues.append(f"必选 move {mid} 内容缺失")
                failed_move_ids.append(mid)

    # Coverage QC for must_cover_points (p0 only; hard points gate, soft points warn)
    coverage = {
        "p0_total": 0,
        "p0_covered": 0,
        "missing_p0_point_ids": [],
        "covered_p0_point_ids": [],
        "p0_hard_total": 0,
        "p0_hard_covered": 0,
        "missing_p0_hard_point_ids": [],
        "covered_p0_hard_point_ids": [],
        "p0_soft_total": 0,
        "p0_soft_covered": 0,
        "missing_p0_soft_point_ids": [],
        "covered_p0_soft_point_ids": [],
    }
    must_cover_points = []
    if isinstance(sk, dict):
        must_cover_points = sk.get("must_cover_points") or []
    coverage_map = (state.get("writing_meta") or {}).get("coverage_map") or {}
    if not isinstance(coverage_map, dict):
        coverage_map = {}
    if isinstance(must_cover_points, list) and must_cover_points:
        p0_points: list[dict[str, Any]] = []
        for p in must_cover_points:
            if not isinstance(p, dict):
                continue
            imp = str(p.get("importance") or "").strip().lower()
            if imp == "p0":
                p0_points.append(p)
        coverage["p0_total"] = len(p0_points)
        covered_ids: list[str] = []
        missing_ids: list[str] = []
        covered_hard: list[str] = []
        missing_hard: list[str] = []
        covered_soft: list[str] = []
        missing_soft: list[str] = []
        missing_anchor_moves: list[int] = []
        for p in p0_points:
            pid = str(p.get("point_id") or "").strip()
            if not pid:
                continue
            mode = str(p.get("verification") or "hard").strip().lower()
            if mode not in ("hard", "soft"):
                mode = "hard"

            # 1) require creator-provided phrase to appear literally in final text
            cm = coverage_map.get(pid) if isinstance(coverage_map, dict) else None
            phrase = ""
            move_id = None
            if isinstance(cm, dict):
                phrase = str(cm.get("phrase") or "").strip()
                try:
                    move_id = int(cm.get("move_id"))
                except Exception:
                    move_id = None
            # phrase_ok is only meaningful for hard points (quote evidence). For soft points, do not enforce.
            phrase_ok = bool(phrase and phrase in draft) if mode == "hard" else bool(phrase)

            # 2) audit tokens: require at least one "hard token" from source_fact (imitate) or from hints (transfer)
            audit_tokens: list[str] = []
            sf = str(p.get("source_fact") or "").strip()
            if sf:
                # numeric-like tokens (hours/weights/%/units)
                audit_tokens.extend([t for t in dict.fromkeys(_NUM_TOKEN_RE.findall(sf)) if t])
                # common "hard" chinese keywords that often represent facts
                for kw in ["非油炸", "云南", "里脊", "烘烤", "变温", "辣椒", "追剧", "半夜", "嘴馋"]:
                    if kw in sf and kw not in audit_tokens:
                        audit_tokens.append(kw)
            if not audit_tokens:
                hints = p.get("mention_hints") or []
                if isinstance(hints, list):
                    audit_tokens.extend([str(h or "").strip() for h in hints if str(h or "").strip()])
            audit_ok = True
            if audit_tokens:
                audit_ok = any(tok in draft for tok in audit_tokens if tok)

            # Hard: require audit_ok (facts) AND phrase_ok (quote evidence) to reduce false positives.
            # Soft: do not gate; best-effort mark covered by presence of any hint/phrase.
            if mode == "hard":
                hit = phrase_ok and audit_ok
            else:
                hit = phrase_ok or audit_ok

            if hit:
                covered_ids.append(pid)
                if mode == "hard":
                    covered_hard.append(pid)
                else:
                    covered_soft.append(pid)
            else:
                missing_ids.append(pid)
                if mode == "hard":
                    missing_hard.append(pid)
                    anchors = p.get("anchor_move_ids") or []
                    if isinstance(anchors, list):
                        for a in anchors:
                            try:
                                ai = int(a)
                            except Exception:
                                continue
                            if 1 <= ai <= 10 and ai not in missing_anchor_moves:
                                missing_anchor_moves.append(ai)
                else:
                    missing_soft.append(pid)

        coverage["p0_covered"] = len(covered_ids)
        coverage["covered_p0_point_ids"] = covered_ids
        coverage["missing_p0_point_ids"] = missing_ids
        coverage["p0_hard_total"] = len(covered_hard) + len(missing_hard)
        coverage["p0_hard_covered"] = len(covered_hard)
        coverage["covered_p0_hard_point_ids"] = covered_hard
        coverage["missing_p0_hard_point_ids"] = missing_hard
        coverage["p0_soft_total"] = len(covered_soft) + len(missing_soft)
        coverage["p0_soft_covered"] = len(covered_soft)
        coverage["covered_p0_soft_point_ids"] = covered_soft
        coverage["missing_p0_soft_point_ids"] = missing_soft

        # Gate only on missing hard p0 points
        if missing_hard:
            issues.append(f"p0-hard 信息点遗漏（must_cover_points）: {missing_hard}")
            # rewrite suggested anchor moves, fallback to 4.
            if missing_anchor_moves:
                failed_move_ids.extend(missing_anchor_moves)
            else:
                failed_move_ids.append(4)
        # Soft p0 points: warn only (do not gate)
        if missing_soft:
            issues.append(f"p0-soft 信息点可能未覆盖（提示，不阻断）: {missing_soft}")

    # If leakage, attempt to map to move ids by finding entity in move segments
    if leakage_hits and isinstance(rendered, dict):
        for mid_str, seg in rendered.items():
            seg_text = str(seg or "")
            if any(h in seg_text for h in leakage_hits):
                try:
                    failed_move_ids.append(int(mid_str))
                except Exception:
                    pass

    # De-dup failed ids
    failed_move_ids = list(dict.fromkeys([i for i in failed_move_ids if isinstance(i, int)]))

    is_passed = len(issues) == 0 and len(draft) >= 30
    feedback = ""
    if not is_passed:
        feedback = "请只重写 failed_move_ids 对应的 move，并修复以下问题：\n- " + "\n- ".join(issues)

    report = {
        "is_passed": is_passed,
        "issues": issues,
        "failed_move_ids": failed_move_ids,
        "feedback": feedback,
        "coverage": coverage,
    }
    return {"qc_report": report, "verification_result": report}


def should_proceed_after_qc(state: AgentState) -> str:
    """QC gating: fail → creator_v2 (targeted rewrite); pass → proofread."""
    qc = state.get("qc_report") or {}
    iteration_count = int(state.get("iteration_count", 0) or 0)
    max_iterations = int(getattr(settings, "max_iterations", 3) or 3)
    if isinstance(qc, dict) and qc.get("is_passed") is False:
        if iteration_count >= max_iterations:
            logger.warning(f"[v2] QC 未通过但已达最大迭代 {iteration_count}/{max_iterations}，强制 proceed")
            return "proceed"
        return "revise"
    return "proceed"


