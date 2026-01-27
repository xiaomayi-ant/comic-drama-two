"""Skeleton v2 (IR) data structures for move-based copy imitation.

Concrete landing of docs/move_step4.md:
- stable primary intents (codebook)
- micro-rhetoric strategies ("how to say")
- entity slots with source defaults and mapped target values
- constraints per move for QC and targeted rewrites
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


SchemaVersion = Literal["skeleton_v2"]
Medium = Literal["live_stream", "short_video", "landing_page", "sms", "push", "banner"]
PrimaryIntent = Literal["Attention", "Need", "Value", "Proof", "Conversion"]
PointImportance = Literal["p0", "p1", "p2"]
VerificationMode = Literal["hard", "soft"]


class CodebookRefs(BaseModel):
    intent_codebook_version: str = Field(default="intent_codebook_v0")
    rhetoric_codebook_version: str = Field(default="micro_rhetoric_codebook_v0")


class SkeletonMeta(BaseModel):
    schema_version: SchemaVersion = Field(default="skeleton_v2")
    medium: Medium = Field(default="live_stream")
    language: str = Field(default="zh")
    target_duration_sec: Optional[int] = Field(default=None, ge=10, le=180)


class MicroRhetoric(BaseModel):
    tag: str = Field(description="Micro-rhetoric tag (must be from codebook enum list).")
    note: str = Field(default="", description="Short operational note.")


class EntitySlotValue(BaseModel):
    source_default: Optional[str] = Field(default=None)
    target_value: Optional[str] = Field(default=None)
    fallback: Optional[str] = Field(
        default=None, description="Soft-landing generic expression if no mapping."
    )


class MoveConstraints(BaseModel):
    must_include_evidence: bool = Field(default=False)
    must_include_scene: bool = Field(default=False)
    must_include_price_or_offer: bool = Field(default=False)
    must_have_clear_cta: bool = Field(default=False)
    must_avoid_source_entities: bool = Field(default=True)
    must_ground_numbers_in_specs: bool = Field(default=True)


class SkeletonMoveV2(BaseModel):
    move_id: int = Field(ge=1, le=10, description="Macro move_id aligned to Ten-move (1-10).")
    primary_intent: PrimaryIntent
    secondary_intents: list[str] = Field(default_factory=list)
    micro_rhetoric: MicroRhetoric
    emotional_beat: list[str] = Field(default_factory=list)
    abstracted_template: str = Field(
        description="De-entity template instruction; MUST NOT include source entities."
    )
    entity_slots: dict[str, EntitySlotValue] = Field(default_factory=dict)
    constraints: MoveConstraints = Field(default_factory=MoveConstraints)
    source_span: Optional[str] = Field(default=None, description="Debug only.")


class MustCoverPoint(BaseModel):
    """
    Information ledger extracted from the source copy.

    - Imitate-mode: can preserve these facts (rewritten) to avoid omission.
    - Transfer-mode: must satisfy abstract_requirement using provided specs/mapping,
      without leaking source entities.
    """

    point_id: str = Field(description='Point id, e.g. "1", "2", "3".')
    importance: PointImportance = Field(default="p1", description="p0 must be covered; p1/p2 optional.")
    category: Optional[str] = Field(default=None, description="e.g. ingredients/specs/offer/proof/process/scene")
    verification: VerificationMode = Field(
        default="hard",
        description="Verification mode: hard=fact-like deterministic checks; soft=semantic guidance (non-blocking by default).",
    )
    source_fact: Optional[str] = Field(
        default=None,
        description="Optional raw fact from source (may contain entities/numbers). For audit only.",
    )
    abstract_requirement: str = Field(
        description="Entity-free requirement describing what must be conveyed (transfer-safe)."
    )
    mention_hints: list[str] = Field(
        default_factory=list,
        description="2-5 short, entity-free hint phrases to help coverage checks.",
    )
    anchor_move_ids: list[int] = Field(
        default_factory=list,
        description="Suggested move_id(s) [1..10] where this point should be covered.",
    )
    why_important: Optional[str] = Field(default=None, description="Short reason for importance.")


class SkeletonV2(BaseModel):
    meta: SkeletonMeta = Field(default_factory=SkeletonMeta)
    codebook_refs: CodebookRefs = Field(default_factory=CodebookRefs)
    source_entities: list[str] = Field(default_factory=list)
    risk_lexicon_hits: list[str] = Field(default_factory=list)
    must_cover_points: list[MustCoverPoint] = Field(default_factory=list)
    move_sequence: list[SkeletonMoveV2]
    global_constraints: dict[str, Any] = Field(default_factory=dict)


