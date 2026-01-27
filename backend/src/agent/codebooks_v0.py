"""Codebooks (v0) for Skeleton v2 pipeline.

These codebooks are meant to be small, stable enums used as anchors to reduce
Analyst instability (label drift) while still allowing free-form notes.
"""

from __future__ import annotations

from typing import Final


INTENT_CODEBOOK_V0: Final[dict[str, str]] = {
    # Hard logic (macro persuasion function)
    "Attention": "打断自动滑动/制造认知中断，让用户愿意继续听",
    "Need": "唤醒需求/痛点/场景，让用户觉得‘这跟我有关’",
    "Value": "讲清产品价值/差异化/机制，让用户觉得‘值得’",
    "Proof": "提供证据/背书/案例，解决‘凭什么信你’",
    "Conversion": "推动行动/降低摩擦，给出明确下一步（轻量 CTA）",
}


# Micro-rhetoric is about “how to say”, not syntax.
MICRO_RHETORIC_CODEBOOK_V0: Final[dict[str, str]] = {
    "Concessive_Reversal": "让步反转：先承认/自嘲/以为…，再反转给出更优真相",
    "Conversational_Confession": "对话式坦白：‘跟你说实话…’‘我先交代一句…’拉近距离",
    "Specific_Exaggeration": "具象化夸张：不用‘很’‘非常’，用具体生理/画面来放大感受",
    "Curiosity_Gap": "信息缺口：留悬念/只说一半，让人想听下去",
    "Scenario_Anchoring": "场景锚定：用具体时刻/人群/动作把需求钉在现实里",
    "Pain_Contrast": "痛点对比：旧方案不行/踩雷经历 → 引出新解法",
    "Sensory_Stacking": "感官堆叠：多维感官/节奏堆叠，制造‘爽感’与画面感",
    "Authority_Signal": "可信信号：工艺/资质/标准/来源等（避免虚构权威）",
    "Objection_Preempt": "预判异议：先替用户说出顾虑，再给出化解",
    "Low_Friction_CTA": "低摩擦 CTA：‘点进来看看/先了解一下’而不是强互动指令",
}


# Few-shot examples: kept minimal and general to avoid leakage.
# v0: only one compact example; can be expanded later.
FEWSHOT_ANALYST_V0: Final[list[dict]] = [
    {
        "source_copy": "喝了一整箱，才发现这根本不是那种兑了糖浆的碳酸饮料啊～这是真正的0糖0卡果味气泡水，气泡感特别足！",
        "expected_skeleton": {
            "move_sequence": [
                {
                    "move_id": 1,
                    "primary_intent": "Attention",
                    "micro_rhetoric": {
                        "tag": "Concessive_Reversal",
                        "note": "用‘才发现/以为…其实…’制造认知反差吸引注意",
                    },
                    "abstracted_template": "先承认自己/大众对[品类]的常见误解，再反转揭示更好的真实属性",
                    "entity_slots": {
                        "misconception_item": {"source_default": "兑了糖浆的普通饮料"},
                        "reality_item": {"source_default": "0糖0卡的真实果味气泡"},
                    },
                }
            ]
        },
    }
]


