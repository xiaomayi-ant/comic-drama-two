"""Ten-move schema (IR) utilities for promotional spoken copy (live selling)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

Medium = Literal["sms", "push", "banner", "landing_page", "live_stream"]


def default_ten_move_schema() -> dict[str, Any]:
    """Return a default Ten-move schema template (IR)."""
    return {
        "schema_version": "promo_move_schema_v1",
        "medium": "live_stream",
        "language": "zh",
        "product_context": {
            "product_name": "",
            "category": "",
            "target_audience": "",
            "core_problem": "",
            "core_benefit": "",
            "proof_points": [],
            "offer": "",
            "cta_url": "",
        },
        "global_constraints": {
            # For live scripts, we default to time not chars; model should still keep concise.
            "max_chars": 800,
            "tone": "friendly",
            "brand_voice_notes": "",
            "must_include_terms": [],
            "must_avoid_terms": [],
        },
        "spoken_constraints": {
            "target_duration_sec": 60,
            "delivery_style": "直播带货",
            "line_break_rule": "尽量按口播停顿断句，每行不宜过长",
            "compliance_notes": "避免绝对化/夸大/医疗功效承诺；不虚构权威背书；价格表述谨慎",
        },
        "move_sequence": [
            {
                "move_id": 1,
                "move_name": "Headline",
                "necessity": "obligatory",
                "intent": "capture_attention",
                "rhetorical_relation": "motivation",
                "content": "",
            },
            {
                "move_id": 2,
                "move_name": "Targeting_the_Market",
                "necessity": "optional",
                "intent": "audience_alignment",
                "rhetorical_relation": "background",
                "content": "",
            },
            {
                "move_id": 3,
                "move_name": "Justifying_by_Establishing_a_Niche",
                "necessity": "optional",
                "intent": "problem_gap_framing",
                "rhetorical_relation": "contrast",
                "content": "",
            },
            {
                "move_id": 4,
                "move_name": "Detailing_the_Product_or_Service",
                "necessity": "obligatory",
                "intent": "value_explanation",
                "rhetorical_relation": "enablement",
                "content": "",
            },
            {
                "move_id": 5,
                "move_name": "Establishing_Credentials",
                "necessity": "optional",
                "intent": "trust_building",
                "rhetorical_relation": "evidence",
                "content": "",
            },
            {
                "move_id": 6,
                "move_name": "Endorsements_or_Testimonials",
                "necessity": "optional",
                "intent": "social_proof",
                "rhetorical_relation": "evidence",
                "content": "",
            },
            {
                "move_id": 7,
                "move_name": "Offering_Incentives",
                "necessity": "optional",
                "intent": "value_amplification",
                "rhetorical_relation": "enablement",
                "content": "",
            },
            {
                "move_id": 8,
                "move_name": "Using_Pressure_Tactics",
                "necessity": "optional",
                "intent": "urgency_creation",
                "rhetorical_relation": "motivation",
                "content": "",
            },
            {
                "move_id": 9,
                "move_name": "Soliciting_Response",
                "necessity": "obligatory",
                "intent": "action_trigger",
                "rhetorical_relation": "enablement",
                "content": "",
            },
            {
                "move_id": 10,
                "move_name": "Brand_Logo_or_Signature",
                "necessity": "optional",
                "intent": "brand_identity",
                "rhetorical_relation": "background",
                "content": "",
            },
        ],
        "optional_extension": {
            "link_button": {"enabled": False, "text": "", "url": ""}
        },
    }


def prune_moves_for_live_stream(schema: dict[str, Any], target_duration_sec: int) -> dict[str, Any]:
    """
    Deterministically prune move_sequence for live stream spoken scripts.

    - 30s: 1,3,4,7,9 (+10 optional)
    - 60s: 1,2,3,4,5,7,8,9 (+10 optional)
    """
    pruned = deepcopy(schema)
    target = 60 if target_duration_sec >= 60 else 30
    keep_ids = {1, 4, 9}
    if target == 30:
        keep_ids |= {3, 7, 10}
    else:
        keep_ids |= {2, 3, 5, 7, 8, 10}
    pruned["spoken_constraints"]["target_duration_sec"] = target_duration_sec
    pruned["move_sequence"] = [
        m for m in pruned.get("move_sequence", []) if m.get("move_id") in keep_ids
    ]
    return pruned


