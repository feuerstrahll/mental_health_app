"""ML Server API contracts for privacy-safe decision engine integration.

This module defines strict Pydantic request/response schemas for two data modes:
- aggregated_only
- aggregated_plus_text

Key guarantees:
1. Payload truthfulness: text fields are mode-gated and explicit.
2. PII minimization: schema forbids direct PII fields and rejects obvious PII in text.
3. Decision-first output: server returns structured decision object, not plain bot text.
4. Safety handling: explicit branches for no-text input and low-confidence predictions.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, List, Literal, Mapping, Optional, Sequence
import re

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


LOW_CONFIDENCE_THRESHOLD = 0.45

# Simple high-signal patterns to reject obvious PII in free text fields.
PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # email
    re.compile(r"(?:\+?\d[\d\-()\s]{8,}\d)"),  # phone-like sequence
    re.compile(r"\b(?:passport|паспорт|ssn|снилс|инн)\b", re.IGNORECASE),
]


class DataMode(str, Enum):
    AGGREGATED_ONLY = "aggregated_only"
    AGGREGATED_PLUS_TEXT = "aggregated_plus_text"


class SupportProfile(str, Enum):
    STABLE_PATTERN = "stable_pattern"
    ELEVATED_STRESS_PATTERN = "elevated_stress_pattern"
    DEPLETED_PATTERN = "depleted_pattern"
    UNSTABLE_PATTERN = "unstable_pattern"


class ResponseMode(str, Enum):
    TEMPLATE_ONLY = "template_only"
    SAFETY_TEMPLATE_ONLY = "safety_template_only"


class FollowupType(str, Enum):
    NONE = "none"
    SOFT_CHECKIN_24H = "soft_checkin_24h"
    PROACTIVE_CHECKIN_3H = "proactive_checkin_3h"
    SAFETY_RECHECK_30M = "safety_recheck_30m"


class RecommendationAction(str, Enum):
    BREATHING_478 = "breathing_478"
    BOX_BREATHING = "box_breathing"
    GROUNDING_5_SENSES = "grounding_5_senses"
    SHORT_WALK = "short_walk"
    HYDRATION_PAUSE = "hydration_pause"
    TINY_STEP_RESET = "tiny_step_reset"
    SELF_COMPASSION_PROMPT = "self_compassion_prompt"
    REST_PERMISSION_MESSAGE = "rest_permission_message"
    GENTLE_REFLECTION_ONLY = "gentle_reflection_only"
    CLOSING_SUPPORT_MESSAGE = "closing_support_message"


class RecommendationResponseMode(str, Enum):
    GENTLE_SUPPORT = "gentle_support"
    REFLECTIVE_SUPPORT = "reflective_support"
    ACTION_SUPPORT = "action_support"
    SAFE_SUPPORT = "safe_support"
    CLOSING_SUPPORT = "closing_support"


class FollowupMode(str, Enum):
    REFLECTIVE = "reflective"
    CLARIFYING = "clarifying"
    GENTLE_ACTION = "gentle_action"
    CLOSE_CONVERSATION = "close_conversation"
    NO_FOLLOWUP = "no_followup"


@dataclass(frozen=True)
class RecommendationDecision:
    recommended_action: str
    response_mode: str
    followup_mode: str
    should_continue_dialogue: bool
    recommendation_reason: str
    recommendation_metadata: dict[str, Any] = field(default_factory=dict)


class RecommendationService:
    """Deterministic recommendation selector for MVP."""

    DEFAULT_RECENT_WINDOW = 3
    LOW_CONFIDENCE_NUMERIC_THRESHOLD = 0.45

    PROFILE_ACTIONS: dict[str, list[str]] = {
        "stable_pattern": [
            RecommendationAction.GENTLE_REFLECTION_ONLY.value,
            RecommendationAction.SELF_COMPASSION_PROMPT.value,
            RecommendationAction.TINY_STEP_RESET.value,
        ],
        "overload_pattern": [
            RecommendationAction.BREATHING_478.value,
            RecommendationAction.BOX_BREATHING.value,
            RecommendationAction.GROUNDING_5_SENSES.value,
        ],
        "elevated_stress_pattern": [
            RecommendationAction.BREATHING_478.value,
            RecommendationAction.BOX_BREATHING.value,
            RecommendationAction.GROUNDING_5_SENSES.value,
        ],
        "depleted_pattern": [
            RecommendationAction.REST_PERMISSION_MESSAGE.value,
            RecommendationAction.HYDRATION_PAUSE.value,
            RecommendationAction.TINY_STEP_RESET.value,
            RecommendationAction.SHORT_WALK.value,
        ],
        "unstable_pattern": [
            RecommendationAction.GROUNDING_5_SENSES.value,
            RecommendationAction.BOX_BREATHING.value,
            RecommendationAction.GENTLE_REFLECTION_ONLY.value,
        ],
    }

    SAFE_MODE_ACTIONS: list[str] = [
        RecommendationAction.GROUNDING_5_SENSES.value,
        RecommendationAction.BREATHING_478.value,
        RecommendationAction.GENTLE_REFLECTION_ONLY.value,
        RecommendationAction.SELF_COMPASSION_PROMPT.value,
        RecommendationAction.CLOSING_SUPPORT_MESSAGE.value,
    ]

    SOFT_ACTIONS: list[str] = [
        RecommendationAction.GENTLE_REFLECTION_ONLY.value,
        RecommendationAction.SELF_COMPASSION_PROMPT.value,
        RecommendationAction.HYDRATION_PAUSE.value,
        RecommendationAction.REST_PERMISSION_MESSAGE.value,
    ]

    SEVERE_RISK_FLAGS = {
        "self_harm_hint",
        "crisis_like_text",
        "severe_hopelessness",
        "acute_distress",
    }

    STOP_FLAGS = {"stop_intent", "boundary_request"}

    def recommend(
        self,
        *,
        pattern_analysis_output: Mapping[str, Any] | None,
        safety_output: Mapping[str, Any] | None,
        conversation_state: Mapping[str, Any] | None = None,
        recommendation_history: Sequence[str] | None = None,
        user_preferences: Mapping[str, Any] | None = None,
    ) -> RecommendationDecision:
        pattern = dict(pattern_analysis_output or {})
        safety = dict(safety_output or {})
        state = dict(conversation_state or {})
        prefs = dict(user_preferences or {})

        support_profile = str(pattern.get("support_profile", SupportProfile.STABLE_PATTERN.value)).strip().lower()
        support_need_score = self._clamp(self._to_float(pattern.get("support_need_score", 0.3)))
        confidence_level = self._normalize_confidence(pattern.get("confidence"))
        contributing_factors = {
            str(item).strip().lower() for item in pattern.get("contributing_factors", []) or []
        }

        safe_mode = bool(safety.get("safe_mode", False))
        close_conversation = bool(safety.get("close_conversation", False))
        risk_flags = {str(item).strip().lower() for item in safety.get("risk_flags", []) or []}
        stop_requested = (
            close_conversation
            or bool(state.get("stop_requested", False))
            or bool(self.STOP_FLAGS.intersection(risk_flags))
        )

        recent_history = [str(item).strip().lower() for item in (recommendation_history or state.get("recent_actions", []) or [])]
        avoid_actions = {str(item).strip().lower() for item in prefs.get("avoid_actions", []) or []}
        preferred_actions = [str(item).strip().lower() for item in prefs.get("preferred_actions", []) or []]

        if stop_requested:
            return RecommendationDecision(
                recommended_action=RecommendationAction.CLOSING_SUPPORT_MESSAGE.value,
                response_mode=RecommendationResponseMode.CLOSING_SUPPORT.value,
                followup_mode=FollowupMode.CLOSE_CONVERSATION.value,
                should_continue_dialogue=False,
                recommendation_reason="stop_requested",
                recommendation_metadata={"policy_override": "stop_intent_or_close"},
            )

        if close_conversation:
            return RecommendationDecision(
                recommended_action=RecommendationAction.CLOSING_SUPPORT_MESSAGE.value,
                response_mode=RecommendationResponseMode.CLOSING_SUPPORT.value,
                followup_mode=FollowupMode.NO_FOLLOWUP.value,
                should_continue_dialogue=False,
                recommendation_reason="close_requested_by_safety",
                recommendation_metadata={"policy_override": "close_conversation"},
            )

        if safe_mode:
            candidates = list(self.SAFE_MODE_ACTIONS)
            if risk_flags.intersection(self.SEVERE_RISK_FLAGS):
                # Keep action non-activating for high-risk cases.
                candidates = [
                    RecommendationAction.GROUNDING_5_SENSES.value,
                    RecommendationAction.BREATHING_478.value,
                    RecommendationAction.GENTLE_REFLECTION_ONLY.value,
                ]
            action = self._select_action(
                candidates=candidates,
                recent_history=recent_history,
                preferred_actions=preferred_actions,
                avoid_actions=avoid_actions,
            )
            return RecommendationDecision(
                recommended_action=action,
                response_mode=RecommendationResponseMode.SAFE_SUPPORT.value,
                followup_mode=FollowupMode.NO_FOLLOWUP.value,
                should_continue_dialogue=False,
                recommendation_reason="safety_override_active",
                recommendation_metadata={"safe_mode": True, "risk_flags": sorted(risk_flags)},
            )

        candidates = list(self.PROFILE_ACTIONS.get(support_profile, self.PROFILE_ACTIONS["stable_pattern"]))
        candidates = self._enrich_candidates(candidates, contributing_factors, support_need_score)

        if confidence_level == "low":
            candidates = self._prefer_soft_actions(candidates)

        action = self._select_action(
            candidates=candidates,
            recent_history=recent_history,
            preferred_actions=preferred_actions,
            avoid_actions=avoid_actions,
        )

        response_mode = self._resolve_response_mode(
            action=action,
            confidence_level=confidence_level,
            support_profile=support_profile,
        )
        followup_mode = self._resolve_followup_mode(
            response_mode=response_mode,
            confidence_level=confidence_level,
            support_need_score=support_need_score,
        )
        should_continue = followup_mode in {
            FollowupMode.REFLECTIVE.value,
            FollowupMode.CLARIFYING.value,
            FollowupMode.GENTLE_ACTION.value,
        }
        reason = self._resolve_reason(
            support_profile=support_profile,
            contributing_factors=contributing_factors,
            confidence_level=confidence_level,
            support_need_score=support_need_score,
        )

        return RecommendationDecision(
            recommended_action=action,
            response_mode=response_mode,
            followup_mode=followup_mode,
            should_continue_dialogue=should_continue,
            recommendation_reason=reason,
            recommendation_metadata={
                "support_profile": support_profile,
                "support_need_score": round(support_need_score, 4),
                "confidence": confidence_level,
                "candidates": candidates,
                "recent_history_window": recent_history[-self.DEFAULT_RECENT_WINDOW :],
            },
        )

    def _enrich_candidates(
        self,
        candidates: list[str],
        contributing_factors: set[str],
        support_need_score: float,
    ) -> list[str]:
        enriched = list(candidates)
        if "low_sleep" in contributing_factors or "poor_sleep_quality" in contributing_factors:
            enriched.insert(0, RecommendationAction.REST_PERMISSION_MESSAGE.value)
        if "high_sedentary_time" in contributing_factors or "low_activity" in contributing_factors:
            enriched.append(RecommendationAction.SHORT_WALK.value)
        if "emotional_instability" in contributing_factors:
            enriched.insert(0, RecommendationAction.GROUNDING_5_SENSES.value)
        if "negative_note_signal" in contributing_factors:
            enriched.append(RecommendationAction.SELF_COMPASSION_PROMPT.value)
        if support_need_score < 0.25:
            enriched.insert(0, RecommendationAction.GENTLE_REFLECTION_ONLY.value)
        return self._dedupe(enriched)

    def _prefer_soft_actions(self, candidates: list[str]) -> list[str]:
        preferred = [item for item in self.SOFT_ACTIONS if item in candidates]
        others = [item for item in candidates if item not in preferred]
        return self._dedupe(preferred + others)

    def _select_action(
        self,
        *,
        candidates: Sequence[str],
        recent_history: Sequence[str],
        preferred_actions: Sequence[str],
        avoid_actions: set[str],
    ) -> str:
        ordered = [item for item in candidates if item not in avoid_actions]
        if not ordered:
            ordered = [RecommendationAction.GENTLE_REFLECTION_ONLY.value]

        preferred = [item for item in preferred_actions if item in ordered]
        if preferred:
            ordered = self._dedupe(preferred + ordered)

        recent_window = list(recent_history[-self.DEFAULT_RECENT_WINDOW :])
        for action in ordered:
            if action not in recent_window:
                return action
        return ordered[0]

    def _resolve_response_mode(
        self,
        *,
        action: str,
        confidence_level: str,
        support_profile: str,
    ) -> str:
        if confidence_level == "low":
            return RecommendationResponseMode.GENTLE_SUPPORT.value
        if action in {
            RecommendationAction.GENTLE_REFLECTION_ONLY.value,
            RecommendationAction.SELF_COMPASSION_PROMPT.value,
            RecommendationAction.REST_PERMISSION_MESSAGE.value,
        }:
            return RecommendationResponseMode.REFLECTIVE_SUPPORT.value
        if support_profile == "stable_pattern":
            return RecommendationResponseMode.GENTLE_SUPPORT.value
        return RecommendationResponseMode.ACTION_SUPPORT.value

    def _resolve_followup_mode(
        self,
        *,
        response_mode: str,
        confidence_level: str,
        support_need_score: float,
    ) -> str:
        if confidence_level == "low":
            return FollowupMode.CLARIFYING.value
        if support_need_score < 0.25:
            return FollowupMode.NO_FOLLOWUP.value
        if response_mode == RecommendationResponseMode.REFLECTIVE_SUPPORT.value:
            return FollowupMode.REFLECTIVE.value
        if response_mode == RecommendationResponseMode.ACTION_SUPPORT.value:
            return FollowupMode.GENTLE_ACTION.value
        return FollowupMode.REFLECTIVE.value

    def _resolve_reason(
        self,
        *,
        support_profile: str,
        contributing_factors: set[str],
        confidence_level: str,
        support_need_score: float,
    ) -> str:
        if confidence_level == "low":
            return "low_confidence_soft_recommendation"
        if support_profile == "depleted_pattern" and {
            "low_sleep",
            "poor_sleep_quality",
            "low_activity",
        }.intersection(contributing_factors):
            return "recent_sleep_drop_and_low_energy"
        if support_profile in {"overload_pattern", "elevated_stress_pattern"}:
            return "overload_signals_with_high_distress"
        if support_profile == "unstable_pattern":
            return "unstable_pattern_with_conflicting_signals"
        if support_need_score < 0.3:
            return "light_support_for_stable_pattern"
        return "profile_based_deterministic_action"

    def _normalize_confidence(self, raw: Any) -> str:
        if isinstance(raw, str):
            text = raw.strip().lower()
            if text in {"low", "medium", "high"}:
                return text
        numeric = self._to_float(raw)
        if numeric <= 0:
            return "medium"
        if numeric < self.LOW_CONFIDENCE_NUMERIC_THRESHOLD:
            return "low"
        if numeric < 0.75:
            return "medium"
        return "high"

    def _dedupe(self, values: Sequence[str]) -> list[str]:
        seen: set[str] = set()
        ordered: list[str] = []
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            ordered.append(value)
        return ordered

    def _to_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _clamp(self, value: float, lower: float = 0.0, upper: float = 1.0) -> float:
        if value < lower:
            return lower
        if value > upper:
            return upper
        return value

    def map_response_mode_to_contract(self, recommendation_response_mode: str) -> ResponseMode:
        if recommendation_response_mode in {
            RecommendationResponseMode.SAFE_SUPPORT.value,
            RecommendationResponseMode.CLOSING_SUPPORT.value,
        }:
            return ResponseMode.SAFETY_TEMPLATE_ONLY
        return ResponseMode.TEMPLATE_ONLY

    def map_followup_mode_to_contract(self, followup_mode: str) -> FollowupType:
        if followup_mode in {FollowupMode.CLOSE_CONVERSATION.value, FollowupMode.NO_FOLLOWUP.value}:
            return FollowupType.NONE
        if followup_mode == FollowupMode.GENTLE_ACTION.value:
            return FollowupType.PROACTIVE_CHECKIN_3H
        if followup_mode == FollowupMode.CLARIFYING.value:
            return FollowupType.SOFT_CHECKIN_24H
        return FollowupType.SOFT_CHECKIN_24H


class ConsentFlags(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_aggregated_processing: bool = Field(
        ..., description="Allows server-side processing of aggregated non-PII features."
    )
    allow_text_processing: bool = Field(
        ..., description="Allows text transfer/processing when mode is aggregated_plus_text."
    )
    allow_safety_policy_enforcement: bool = Field(
        ..., description="Allows safety gating and mandatory safe response policies."
    )


class SafetyPrecheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["pass", "flagged", "blocked"]
    flags: List[str] = Field(default_factory=list)
    safe_response_required: bool = False


class AggregatedFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entries_last_7d: int = Field(..., ge=0, le=100)
    avg_stress_7d: float = Field(..., ge=0.0, le=10.0)
    stress_trend_7d: Literal["down", "flat", "up", "unknown"] = "unknown"
    avg_sleep_hours_7d: Optional[float] = Field(default=None, ge=0.0, le=24.0)
    avg_energy_7d: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    checkins_count_14d: Optional[int] = Field(default=None, ge=0, le=200)


class DecisionRequest(BaseModel):
    """Request payload to ML decision endpoint.

    PII is intentionally excluded by schema design:
    - no name/email/phone/address/user_message_id/user_id fields
    - only anonymous event metadata and aggregated signals
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    mode: DataMode
    request_id: str = Field(..., min_length=8, max_length=64)
    client_version: str = Field(..., min_length=1, max_length=64)
    locale: str = Field(..., pattern=r"^[a-z]{2}(?:-[A-Z]{2})?$")
    consent_flags: ConsentFlags
    safety_precheck_result: SafetyPrecheckResult
    aggregated_features: AggregatedFeatures

    # Optional text channels (mode-gated)
    user_message: Optional[str] = Field(default=None, max_length=2000)
    note_text: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("user_message", "note_text")
    @classmethod
    def reject_obvious_pii(cls, value: Optional[str]) -> Optional[str]:
        if value is None or value.strip() == "":
            return None
        for pattern in PII_PATTERNS:
            if pattern.search(value):
                raise ValueError("Text contains potential PII and cannot be sent to server.")
        return value

    @model_validator(mode="after")
    def validate_mode_and_consent(self) -> "DecisionRequest":
        has_text = bool(self.user_message or self.note_text)

        if not self.consent_flags.allow_aggregated_processing:
            raise ValueError("allow_aggregated_processing must be true for server decisioning.")

        if self.mode == DataMode.AGGREGATED_ONLY and has_text:
            raise ValueError("Text fields are forbidden in aggregated_only mode.")

        if has_text and self.mode == DataMode.AGGREGATED_PLUS_TEXT:
            if not self.consent_flags.allow_text_processing:
                raise ValueError(
                    "Text is present but consent_flags.allow_text_processing is false."
                )

        if has_text and self.mode == DataMode.AGGREGATED_ONLY:
            raise ValueError("aggregated_only mode cannot include user_message or note_text.")

        return self

    @property
    def has_text_input(self) -> bool:
        return bool(self.user_message or self.note_text)


class RiskFlag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=2, max_length=64)
    severity: Literal["low", "medium", "high", "critical"]
    evidence: List[str] = Field(default_factory=list, max_length=5)


class NoteSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=2, max_length=64)
    source: Literal["note_text", "user_message", "none", "model"]
    strength: float = Field(..., ge=0.0, le=1.0)


class DecisionResponse(BaseModel):
    """Structured server decision object expected by client decision engine."""

    model_config = ConfigDict(extra="forbid")

    support_profile: SupportProfile
    support_need_score: float = Field(..., ge=0.0, le=1.0)
    confidence: float = Field(..., ge=0.0, le=1.0)
    risk_flags: List[RiskFlag] = Field(default_factory=list)
    note_signals: List[NoteSignal] = Field(default_factory=list)
    response_mode: ResponseMode
    recommended_practice: Optional[str] = Field(default=None, max_length=128)
    followup_type: FollowupType
    escalate: bool
    safe_response_required: bool

    @model_validator(mode="after")
    def validate_low_confidence_policy(self) -> "DecisionResponse":
        if self.confidence < LOW_CONFIDENCE_THRESHOLD:
            if not self.safe_response_required:
                raise ValueError(
                    "Low confidence prediction requires safe_response_required=true."
                )
            if self.response_mode not in (
                ResponseMode.TEMPLATE_ONLY,
                ResponseMode.SAFETY_TEMPLATE_ONLY,
            ):
                raise ValueError("Low confidence response must stay in safe template modes.")
        return self


def build_decision_response(
    request: DecisionRequest,
    *,
    support_profile: SupportProfile,
    support_need_score: float,
    confidence: float,
    risk_flags: Optional[List[RiskFlag]] = None,
    note_signals: Optional[List[NoteSignal]] = None,
    response_mode: Optional[ResponseMode] = None,
    recommended_practice: Optional[str] = None,
    followup_type: Optional[FollowupType] = None,
    escalate: bool = False,
    safe_response_required: bool = False,
    pattern_analysis_output: Optional[Mapping[str, Any]] = None,
    safety_output: Optional[Mapping[str, Any]] = None,
    conversation_state: Optional[Mapping[str, Any]] = None,
    recommendation_history: Optional[Sequence[str]] = None,
    user_preferences: Optional[Mapping[str, Any]] = None,
    recommendation_decision: Optional[RecommendationDecision] = None,
) -> DecisionResponse:
    """Builds response with explicit handling for no-text and low-confidence cases."""

    risk_flags = list(risk_flags or [])
    note_signals = list(note_signals or [])

    recommendation_service = RecommendationService()
    if recommendation_decision is None:
        derived_pattern = dict(pattern_analysis_output or {})
        derived_pattern.setdefault("support_profile", support_profile.value)
        derived_pattern.setdefault("support_need_score", support_need_score)
        derived_pattern.setdefault("confidence", confidence)

        derived_safety = dict(safety_output or {})
        derived_safety.setdefault("safe_mode", safe_response_required or request.safety_precheck_result.safe_response_required)
        derived_safety.setdefault("close_conversation", False)
        if "risk_flags" not in derived_safety:
            derived_safety["risk_flags"] = [flag.code for flag in risk_flags]

        recommendation_decision = recommendation_service.recommend(
            pattern_analysis_output=derived_pattern,
            safety_output=derived_safety,
            conversation_state=conversation_state,
            recommendation_history=recommendation_history,
            user_preferences=user_preferences,
        )

    if recommended_practice is None:
        recommended_practice = recommendation_decision.recommended_action
    if response_mode is None:
        response_mode = recommendation_service.map_response_mode_to_contract(
            recommendation_decision.response_mode
        )
    if followup_type is None:
        followup_type = recommendation_service.map_followup_mode_to_contract(
            recommendation_decision.followup_mode
        )

    # Explicit handling when text is absent (aggregated_only or empty text in plus-text mode).
    if not request.has_text_input:
        note_signals.append(
            NoteSignal(code="no_text_input", source="none", strength=0.0)
        )

    # Explicit handling for low-confidence output.
    if confidence < LOW_CONFIDENCE_THRESHOLD:
        safe_response_required = True
        response_mode = ResponseMode.SAFETY_TEMPLATE_ONLY
        if followup_type == FollowupType.NONE:
            followup_type = FollowupType.SOFT_CHECKIN_24H
        note_signals.append(
            NoteSignal(
                code="low_confidence_prediction",
                source="model",
                strength=round(1.0 - confidence, 3),
            )
        )

    return DecisionResponse(
        support_profile=support_profile,
        support_need_score=support_need_score,
        confidence=confidence,
        risk_flags=risk_flags,
        note_signals=note_signals,
        response_mode=response_mode,
        recommended_practice=recommended_practice,
        followup_type=followup_type,
        escalate=escalate,
        safe_response_required=safe_response_required,
    )


AGGREGATED_ONLY_EXAMPLE = {
    "mode": "aggregated_only",
    "request_id": "req_20260421_0001",
    "client_version": "1.4.0",
    "locale": "ru-RU",
    "consent_flags": {
        "allow_aggregated_processing": True,
        "allow_text_processing": False,
        "allow_safety_policy_enforcement": True,
    },
    "safety_precheck_result": {
        "status": "pass",
        "flags": [],
        "safe_response_required": False,
    },
    "aggregated_features": {
        "entries_last_7d": 6,
        "avg_stress_7d": 6.8,
        "stress_trend_7d": "up",
        "avg_sleep_hours_7d": 5.9,
        "avg_energy_7d": 4.1,
        "checkins_count_14d": 11,
    },
}


AGGREGATED_PLUS_TEXT_EXAMPLE = {
    "mode": "aggregated_plus_text",
    "request_id": "req_20260421_0002",
    "client_version": "1.4.0",
    "locale": "ru-RU",
    "consent_flags": {
        "allow_aggregated_processing": True,
        "allow_text_processing": True,
        "allow_safety_policy_enforcement": True,
    },
    "safety_precheck_result": {
        "status": "flagged",
        "flags": ["acute_distress_hint"],
        "safe_response_required": True,
    },
    "aggregated_features": {
        "entries_last_7d": 7,
        "avg_stress_7d": 8.2,
        "stress_trend_7d": "up",
        "avg_sleep_hours_7d": 4.8,
        "avg_energy_7d": 3.2,
        "checkins_count_14d": 13,
    },
    "user_message": "Я очень устал и сложно собраться.",
    "note_text": "Чувствую перегруз и хочу немного стабилизироваться.",
}
