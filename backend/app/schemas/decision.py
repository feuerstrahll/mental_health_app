from __future__ import annotations

from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.schemas.safety import SafetyAssessment
from app.schemas.wellbeing import WellbeingSignalsRequest


class StructuredDecision(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    # legacy contract fields
    support_mode: str = Field(min_length=1, max_length=64)
    assessor_action: str = Field(
        min_length=1,
        max_length=128,
        validation_alias=AliasChoices("assessor_action", "recommended_action"),
    )
    reasoning_tags: list[str] = Field(default_factory=list)

    # deprecated legacy scoring fields (kept only for backward compatibility)
    support_need_score: float | None = Field(default=None, ge=0.0, le=1.0)
    support_profile: str | None = Field(default=None, min_length=1, max_length=64)
    emotional_trend: str | None = Field(default=None, min_length=1, max_length=32)
    confidence: str | float | None = None

    # expanded structured fields for context-first LLM verbalization
    contributing_factors: list[str] = Field(default_factory=list)
    note_signals: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    interaction_flags: list[str] = Field(default_factory=list)
    response_mode: str | None = Field(default=None, min_length=1, max_length=64)
    risk_level: str = Field(default="safe", min_length=1, max_length=32)
    followup_mode: str | None = Field(default=None, min_length=1, max_length=64)
    safe_mode: bool = False
    should_continue_dialogue: bool | None = None
    context_summary: str | None = None
    relevant_memories: list[str] | None = None
    practice_cards: list[str] | None = None
    safety_instructions: list[str] | None = None
    memory_retrieval_used: bool | None = None
    support_need_bucket: str | None = Field(default=None, min_length=1, max_length=16)
    support_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    support_abstain: bool = False
    support_factors: list[str] = Field(default_factory=list)
    personalization_level: str = Field(default="none", min_length=1, max_length=16)
    memory_retrieval_quality: str = Field(default="none", min_length=1, max_length=16)
    allowed_memory_ids: list[str] = Field(default_factory=list)
    verified_safety_resources: list[str] = Field(default_factory=list)
    llm_constraints: list[str] = Field(default_factory=list)

    @property
    def recommended_action(self) -> str:
        return self.assessor_action

    @model_validator(mode="after")
    def apply_backward_compatible_defaults(self) -> "StructuredDecision":
        if self.support_profile is None:
            self.support_profile = self.support_mode

        if self.response_mode is None:
            support_mode = self.support_mode.lower()
            if support_mode in {"crisis_support", "high_touch_support"}:
                self.response_mode = "safe_support"
            else:
                self.response_mode = "action_support"

        if self.relevant_memories is None:
            self.relevant_memories = []
        if self.practice_cards is None:
            self.practice_cards = []
        if self.safety_instructions is None:
            self.safety_instructions = []
        if self.memory_retrieval_used is None:
            self.memory_retrieval_used = False

        if not self.contributing_factors and self.reasoning_tags:
            self.contributing_factors = list(self.reasoning_tags)

        if self.should_continue_dialogue is None:
            mode = (self.followup_mode or "").strip().lower()
            self.should_continue_dialogue = mode not in {"no_followup", "close_conversation", "none"}

        if self.followup_mode is None:
            self.followup_mode = "reflective" if self.should_continue_dialogue else "no_followup"

        return self


class LlmResponseMeta(BaseModel):
    used_fallback: bool = False
    fallback_reason: str | None = None
    latency_ms: int = Field(default=0, ge=0)
    raw_model_response: str | None = None


class AnalysisSnapshot(BaseModel):
    support_need_score: float = Field(ge=0.0, le=1.0)
    support_profile: str = Field(min_length=1, max_length=64)
    emotional_trend: str = Field(min_length=1, max_length=32)
    confidence: str = Field(min_length=1, max_length=16)
    contributing_factors: list[str] = Field(default_factory=list)
    note_signals: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)


class ResponseMetadata(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    session_id: str = Field(min_length=1, max_length=128)
    next_dialogue_state: str = Field(min_length=1, max_length=64)
    fallback_used: bool = False
    llm_latency_ms: int = Field(default=0, ge=0)
    persistence_error: str | None = None
    pipeline_latency_ms: int = Field(default=0, ge=0)
    used_memory_index_fallback: bool = False
    debug: dict[str, Any] | None = None


class DialogueState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal[1] = 1
    turn_index: int | None = Field(default=None, ge=0)
    last_bot_action: str | None = Field(default=None, max_length=128)
    stop_requested: bool = False
    ui_state: str | None = Field(default=None, max_length=64)
    legacy_format: bool = False

    @model_validator(mode="before")
    @classmethod
    def map_legacy_state(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if "state" not in value:
            return value
        mapped = dict(value)
        if "ui_state" not in mapped:
            mapped["ui_state"] = mapped.get("state")
        mapped.pop("state", None)
        mapped.setdefault("version", 1)
        mapped["legacy_format"] = True
        return mapped


class SupportDecisionResponse(BaseModel):
    decision: StructuredDecision
    safety: SafetyAssessment
    llm_response: str
    llm_meta: LlmResponseMeta | None = None
    analysis: AnalysisSnapshot | None = None
    dialogue_state: str | None = None
    safe_mode: bool | None = None
    should_continue_dialogue: bool | None = None
    practice_card_id: str | None = None
    recommended_action: str | None = None
    recommended_action_deprecated: bool = False
    response_metadata: ResponseMetadata | None = None


class SupportDecisionRequest(BaseModel):
    wellbeing: WellbeingSignalsRequest
    session_id: str | None = Field(default=None, max_length=128)
    latest_user_message: str | None = Field(default=None, max_length=1200)
    latest_diary_note: str | None = Field(default=None, max_length=1200)
    dialogue_state: DialogueState | None = None
    client_safety_precheck_result: dict[str, Any] | None = None
