"""
Deterministic, rule-based safety mode classifier.

Assigns exactly one safety mode (crisis | close_conversation | safe_support | normal)
based on keyword matching in user input. Output is immutable downstream.

No ML, no scoring, no probabilistic decisions. Priority-ordered rules only.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Sequence

from app.schemas.safety import RiskLevel, SafetyAssessment

logger = logging.getLogger(__name__)


class SafetyMode(StrEnum):
    """Safety classification mode hierarchy."""

    CRISIS = "crisis"
    CLOSE_CONVERSATION = "close_conversation"
    SAFE_SUPPORT = "safe_support"
    NORMAL = "normal"


@dataclass(frozen=True)
class SafetyClassification:
    """Immutable safety classification result."""

    mode: SafetyMode
    risk_flags: tuple[str, ...]
    safety_instructions: tuple[str, ...]
    confidence: float  # 1.0 for deterministic rules
    raw_triggers: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode.value,
            "risk_flags": list(self.risk_flags),
            "safety_instructions": list(self.safety_instructions),
            "confidence": self.confidence,
            "raw_triggers": self.raw_triggers,
        }


class SafetyClassifier:
    """
    Deterministic rule-based safety classifier.

    Evaluates user input in priority order:
    1. CRISIS: explicit self-harm, severe hopelessness, acute distress
    2. CLOSE_CONVERSATION: stop intent, boundary requests
    3. SAFE_SUPPORT: elevated stress, sleep issues, isolation, low mood
    4. NORMAL: no triggers
    """

    # Keyword sets: EN + RU for each trigger category
    CRISIS_SELF_HARM_KEYWORDS = {
        # English
        "suicide",
        "kill myself",
        "want to die",
        "self harm",
        "harm myself",
        "can't stay safe",
        "cannot stay safe",
        # Russian
        "суицид",
        "убить себя",
        "умереть",
        "причинить себе вред",
        "не могу остаться в безопасности",
    }

    CRISIS_HOPELESSNESS_KEYWORDS = {
        # English
        "no point",
        "no reason",
        "everything is hopeless",
        "nothing matters",
        # Russian
        "смысла нет",
        "нет причины",
        "всё безнадежно",
        "ничего не важно",
    }

    CRISIS_ACUTE_DISTRESS_KEYWORDS = {
        # English
        "panic attack",
        "can't breathe",
        "cannot breathe",
        "dying",
        "going crazy",
        # Russian
        "панический приступ",
        "не могу дышать",
        "умираю",
        "схожу с ума",
    }

    CLOSE_STOP_INTENT_KEYWORDS = {
        # English
        "stop",
        "enough",
        "bye",
        "goodbye",
        "don't reply",
        "do not reply",
        "leave me alone",
        # Russian
        "стоп",
        "хватит",
        "пока",
        "до свидания",
        "не отвечай",
        "оставь меня в покое",
    }

    CLOSE_BOUNDARY_KEYWORDS = {
        # English
        "don't ask",
        "no questions",
        "respect my boundary",
        "private",
        # Russian
        "не задавай",
        "без вопросов",
        "уважай мою границу",
        "приватно",
    }

    CLOSE_HOSTILE_KEYWORDS = {
        # English
        "go away",
        "shut up",
        "you're useless",
        # Russian
        "отстань",
        "замолчи",
        "ты бесполезен",
    }

    SAFE_STRESS_KEYWORDS = {
        # English
        "stress",
        "overwhelm",
        "overwhelmed",
        "anxious",
        "can't cope",
        "cannot cope",
        "struggling",
        # Russian
        "стресс",
        "перегруз",
        "перегруженность",
        "тревож",
        "не справляюсь",
        "борюсь",
    }

    SAFE_SLEEP_KEYWORDS = {
        # English
        "can't sleep",
        "cannot sleep",
        "no sleep",
        "exhausted",
        "tired",
        "insomnia",
        # Russian
        "не сплю",
        "без сна",
        "истощен",
        "устал",
        "бессонница",
    }

    SAFE_ISOLATION_KEYWORDS = {
        # English
        "alone",
        "isolated",
        "no one",
        "nobody",
        # Russian
        "один",
        "одна",
        "изолирован",
        "никого",
        "в одиночестве",
    }

    SAFE_LOW_MOOD_KEYWORDS = {
        # English
        "sad",
        "down",
        "not good",
        # Russian
        "грусть",
        "грустно",
        "подавленность",
        "не хорошо",
    }

    # Safety instructions per mode
    SAFETY_INSTRUCTIONS = {
        SafetyMode.CRISIS: (
            "do_not_ask_questions",
            "provide_only_validated_resources",
            "keep_response_under_360_chars",
            "do_not_offer_techniques",
            "reference_crisis_hotline_if_relevant",
            "encourage_immediate_help_seeking",
        ),
        SafetyMode.CLOSE_CONVERSATION: (
            "respect_stop_request",
            "provide_brief_closure_only",
            "no_follow_up_question",
            "no_continuation_offer",
            "warm_but_final_tone",
        ),
        SafetyMode.SAFE_SUPPORT: (
            "gentle_tone_only",
            "no_deep_probing",
            "at_most_one_soft_question",
            "offer_simple_grounding",
            "avoid_high_intensity_techniques",
            "simplify_language",
            "normalize_experience",
        ),
        SafetyMode.NORMAL: (
            "empathetic_response",
            "up_to_one_reflective_question",
            "use_provided_techniques_if_relevant",
            "standard_supportive_tone",
        ),
    }

    def classify(
        self,
        *,
        latest_user_message: str | None = None,
        latest_diary_note: str | None = None,
        client_safety_precheck_result: dict[str, Any] | None = None,
    ) -> SafetyClassification:
        """
        Classify input into safety mode using deterministic rules.

        Priority order (highest to lowest):
        1. CRISIS
        2. CLOSE_CONVERSATION
        3. SAFE_SUPPORT
        4. NORMAL

        Args:
            latest_user_message: User's current chat message.
            latest_diary_note: User's latest diary/note entry.
            client_safety_precheck_result: Client-side safety flags.

        Returns:
            SafetyClassification with mode, flags, and instructions.
        """
        started_at = time.perf_counter()
        triggers: dict[str, Any] = {}

        # Normalize inputs
        message_text = self._normalize(latest_user_message)
        diary_text = self._normalize(latest_diary_note)
        precheck_flags = self._extract_precheck_flags(client_safety_precheck_result)

        # Step 1: Check CRISIS triggers
        crisis_self_harm = self._match_keywords(
            message_text, diary_text, self.CRISIS_SELF_HARM_KEYWORDS
        )
        if crisis_self_harm:
            triggers["crisis_self_harm"] = crisis_self_harm
            return self._result(
                mode=SafetyMode.CRISIS,
                flag="crisis:explicit_self_harm",
                started_at=started_at,
                triggers=triggers,
            )

        crisis_hopelessness = self._match_keywords(
            message_text, None, self.CRISIS_HOPELESSNESS_KEYWORDS
        )  # current message only
        if crisis_hopelessness:
            triggers["crisis_hopelessness"] = crisis_hopelessness
            return self._result(
                mode=SafetyMode.CRISIS,
                flag="crisis:severe_hopelessness",
                started_at=started_at,
                triggers=triggers,
            )

        crisis_acute_distress = self._match_keywords(
            message_text, None, self.CRISIS_ACUTE_DISTRESS_KEYWORDS
        )  # current message only
        if crisis_acute_distress:
            triggers["crisis_acute_distress"] = crisis_acute_distress
            return self._result(
                mode=SafetyMode.CRISIS,
                flag="crisis:acute_distress",
                started_at=started_at,
                triggers=triggers,
            )

        if "crisis" in precheck_flags or "urgent" in precheck_flags or "self_harm" in precheck_flags or "suicide" in precheck_flags:
            triggers["client_precheck_crisis"] = precheck_flags
            return self._result(
                mode=SafetyMode.CRISIS,
                flag="crisis:client_precheck_flagged",
                started_at=started_at,
                triggers=triggers,
            )

        # Step 2: Check CLOSE_CONVERSATION triggers
        # Check hostile_and_boundary first (more specific), then stop/boundary separately
        boundary_keywords = self._match_keywords(
            message_text, None, self.CLOSE_BOUNDARY_KEYWORDS
        )  # current message only
        hostile_keywords = self._match_keywords(
            message_text, None, self.CLOSE_HOSTILE_KEYWORDS
        )  # current message only

        if hostile_keywords and boundary_keywords:
            triggers["hostile_boundary"] = {
                "hostile": hostile_keywords,
                "boundary": boundary_keywords,
            }
            return self._result(
                mode=SafetyMode.CLOSE_CONVERSATION,
                flag="close:hostile_boundary",
                started_at=started_at,
                triggers=triggers,
            )

        stop_intent = self._match_keywords(
            message_text, None, self.CLOSE_STOP_INTENT_KEYWORDS
        )  # current message only
        if stop_intent:
            triggers["stop_intent"] = stop_intent
            return self._result(
                mode=SafetyMode.CLOSE_CONVERSATION,
                flag="close:stop_intent",
                started_at=started_at,
                triggers=triggers,
            )

        if boundary_keywords:
            triggers["boundary_request"] = boundary_keywords
            return self._result(
                mode=SafetyMode.CLOSE_CONVERSATION,
                flag="close:boundary_request",
                started_at=started_at,
                triggers=triggers,
            )

        if "stop_intent" in precheck_flags or "boundary_request" in precheck_flags:
            triggers["client_precheck_stop"] = precheck_flags
            return self._result(
                mode=SafetyMode.CLOSE_CONVERSATION,
                flag="close:client_precheck_stop",
                started_at=started_at,
                triggers=triggers,
            )

        # Step 3: Check SAFE_SUPPORT triggers
        elevated_stress = self._match_keywords(
            message_text, diary_text, self.SAFE_STRESS_KEYWORDS
        )
        if elevated_stress:
            triggers["elevated_stress"] = elevated_stress
            return self._result(
                mode=SafetyMode.SAFE_SUPPORT,
                flag="safe:elevated_stress",
                started_at=started_at,
                triggers=triggers,
            )

        sleep_issues = self._match_keywords(
            message_text, diary_text, self.SAFE_SLEEP_KEYWORDS
        )
        if sleep_issues:
            triggers["sleep_issues"] = sleep_issues
            return self._result(
                mode=SafetyMode.SAFE_SUPPORT,
                flag="safe:sleep_issues",
                started_at=started_at,
                triggers=triggers,
            )

        isolation_signal = self._match_keywords(
            message_text, diary_text, self.SAFE_ISOLATION_KEYWORDS
        )
        if isolation_signal:
            triggers["isolation_signal"] = isolation_signal
            return self._result(
                mode=SafetyMode.SAFE_SUPPORT,
                flag="safe:isolation_signal",
                started_at=started_at,
                triggers=triggers,
            )

        low_mood = self._match_keywords(message_text, diary_text, self.SAFE_LOW_MOOD_KEYWORDS)
        if low_mood:
            triggers["low_mood"] = low_mood
            return self._result(
                mode=SafetyMode.SAFE_SUPPORT,
                flag="safe:low_mood",
                started_at=started_at,
                triggers=triggers,
            )

        if "elevated_stress" in precheck_flags or "low_mood" in precheck_flags or "isolation" in precheck_flags:
            triggers["client_precheck_safe"] = precheck_flags
            return self._result(
                mode=SafetyMode.SAFE_SUPPORT,
                flag="safe:client_precheck_caution",
                started_at=started_at,
                triggers=triggers,
            )

        # Step 4: Default to NORMAL
        return self._result(
            mode=SafetyMode.NORMAL,
            flag=None,
            started_at=started_at,
            triggers=triggers,
        )

    def _match_keywords(
        self,
        message_text: str,
        diary_text: str | None,
        keywords: set[str],
    ) -> list[str]:
        """
        Match keywords in message and/or diary text.

        Avoids naive substring matching by checking for negation markers.
        Returns list of matched keywords (can be empty).
        """
        matched: list[str] = []
        for keyword in keywords:
            found_in_message = keyword in message_text
            found_in_diary = diary_text and keyword in diary_text

            # Simple negation check: if keyword found, verify it's not preceded by "not "
            if found_in_message:
                # Find position of keyword in message
                pos = message_text.find(keyword)
                # Check if "not " precedes it (with context)
                if pos >= 4 and message_text[pos - 4 : pos] == "not ":
                    found_in_message = False

            if found_in_message or found_in_diary:
                matched.append(keyword)

        return matched

    def _normalize(self, text: str | None) -> str:
        """Normalize text: lowercase, strip, collapse multiple spaces."""
        if not text:
            return ""
        # Lowercase, strip, and collapse multiple spaces
        text = text.lower().strip()
        # Replace multiple spaces with single space
        while "  " in text:
            text = text.replace("  ", " ")
        return text

    def _extract_precheck_flags(self, precheck_result: dict[str, Any] | None) -> set[str]:
        """Extract flags from client safety precheck."""
        if not precheck_result:
            return set()
        flags = precheck_result.get("flags", [])
        return {str(flag).strip().lower() for flag in flags if flag}

    def _result(
        self,
        *,
        mode: SafetyMode,
        flag: str | None,
        started_at: float,
        triggers: dict[str, Any],
    ) -> SafetyClassification:
        """Build result with mode, flag, and instructions."""
        risk_flags = (flag,) if flag else ()
        instructions = self.SAFETY_INSTRUCTIONS.get(mode, ())
        latency_ms = int((time.perf_counter() - started_at) * 1000)

        result = SafetyClassification(
            mode=mode,
            risk_flags=risk_flags,
            safety_instructions=tuple(instructions),
            confidence=1.0,  # deterministic rules
            raw_triggers={"triggers": triggers, "latency_ms": latency_ms},
        )

        logger.info(
            "safety_classification mode=%s flag=%s latency_ms=%d",
            mode.value,
            flag or "none",
            latency_ms,
        )

        return result


@dataclass(frozen=True)
class SafetyResource:
    label: str
    country: str | None = None
    language: str = "ru"
    phone: str | None = None
    url: str | None = None
    availability: str | None = None

    def as_prompt_text(self) -> str:
        parts = [self.label]
        if self.phone:
            parts.append(f"phone: {self.phone}")
        if self.url:
            parts.append(f"url: {self.url}")
        if self.availability:
            parts.append(f"availability: {self.availability}")
        return "; ".join(parts)


class SafetyResourceService:
    GENERIC_UNAVAILABLE_GUIDANCE = (
        "localized crisis resources unavailable; advise local emergency services or a trusted nearby person"
    )

    def __init__(self, resources: Sequence[SafetyResource] | None = None) -> None:
        self._resources = list(resources or [])

    def crisis_resources(
        self,
        *,
        country: str | None,
        language: str = "ru",
    ) -> list[SafetyResource]:
        country_key = self._normalize(country)
        language_key = self._normalize_language(language)
        if country_key:
            matches = [
                resource
                for resource in self._resources
                if self._normalize(resource.country) == country_key
                and self._normalize_language(resource.language) == language_key
            ]
            if matches:
                return matches

        return [
            SafetyResource(
                country=country_key or None,
                language=language_key,
                label=self.GENERIC_UNAVAILABLE_GUIDANCE,
            )
        ]

    def _normalize(self, value: str | None) -> str | None:
        text = (value or "").strip().lower()
        return text or None

    def _normalize_language(self, value: str | None) -> str:
        text = (value or "ru").strip().lower()
        return (text.split("-", 1)[0].split("_", 1)[0] or "ru")


@dataclass(frozen=True)
class SafetyPrecheckResult:
    risk_level: str  # safe | safe_support | crisis
    current_classification: SafetyClassification
    should_persist_message: bool
    should_use_current_turn_in_prompt: bool
    should_extract_structured_signals: bool
    should_persist_structured_signals: bool
    should_embed_raw_text: bool
    should_embed_redacted_text: bool
    should_retrieve_memory: bool
    retention_policy: str  # normal | short_ttl | skip_raw_text
    redacted_text: str | None = None
    verified_resources: list[SafetyResource] = field(default_factory=list)


@dataclass(frozen=True)
class SafetyGateResult:
    mode: str  # normal | supportive_caution | crisis | closing
    safety_assessment: SafetyAssessment
    risk_flags: list[str]
    safe_mode: bool
    close_conversation: bool
    stop_requested: bool
    safety_instructions: list[str]
    verified_resources: list[SafetyResource] = field(default_factory=list)


class SafetyGateService:
    """
    MVP Refactor: Now uses deterministic SafetyClassifier.
    Hard rule: crisis detection is based only on current/latest inputs.
    Retrieved memories are never used as crisis triggers.
    """

    def __init__(self, safety_resource_service: SafetyResourceService | None = None):
        self._classifier = SafetyClassifier()
        self._safety_resource_service = safety_resource_service or SafetyResourceService()

    def precheck(
        self,
        *,
        latest_user_message: str | None,
        latest_diary_note: str | None,
        client_safety_precheck_result: dict[str, Any] | None,
    ) -> SafetyPrecheckResult:
        """
        Minimal early safety policy before persistence and embedding.

        Priority is intentionally CRISIS > SAFE_SUPPORT > CLOSE_CONVERSATION > NORMAL.
        Stop/close intent must not downgrade crisis or elevated-support handling.
        """
        classification = self._classifier.classify(
            latest_user_message=latest_user_message,
            latest_diary_note=latest_diary_note,
            client_safety_precheck_result=client_safety_precheck_result,
        )
        if classification.mode == SafetyMode.CRISIS:
            resources = self._crisis_resources(client_safety_precheck_result)
            return SafetyPrecheckResult(
                risk_level="crisis",
                current_classification=classification,
                should_persist_message=False,
                should_use_current_turn_in_prompt=True,
                should_extract_structured_signals=True,
                should_persist_structured_signals=True,
                should_embed_raw_text=False,
                should_embed_redacted_text=False,
                should_retrieve_memory=False,
                retention_policy="skip_raw_text",
                verified_resources=resources,
            )

        if classification.mode == SafetyMode.SAFE_SUPPORT or self._has_safe_support_signal(
            latest_user_message=latest_user_message,
            latest_diary_note=latest_diary_note,
            client_safety_precheck_result=client_safety_precheck_result,
        ):
            return SafetyPrecheckResult(
                risk_level="safe_support",
                current_classification=classification,
                should_persist_message=True,
                should_use_current_turn_in_prompt=True,
                should_extract_structured_signals=True,
                should_persist_structured_signals=True,
                should_embed_raw_text=False,
                should_embed_redacted_text=False,
                should_retrieve_memory=True,
                retention_policy="short_ttl",
            )

        return SafetyPrecheckResult(
            risk_level="safe",
            current_classification=classification,
            should_persist_message=True,
            should_use_current_turn_in_prompt=True,
            should_extract_structured_signals=True,
            should_persist_structured_signals=True,
            should_embed_raw_text=True,
            should_embed_redacted_text=False,
            should_retrieve_memory=True,
            retention_policy="normal",
        )

    def evaluate(
        self,
        *,
        latest_user_message: str | None,
        latest_diary_note: str | None,
        stop_requested: bool,
        client_safety_precheck_result: dict[str, Any] | None,
        precheck_result: SafetyPrecheckResult | None = None,
        recent_context_safety_concern: bool = False,
    ) -> SafetyGateResult:
        """
        Evaluate using SafetyClassifier (deterministic rules).
        Converts SafetyClassification output to legacy SafetyGateResult format.
        """
        classification = (
            precheck_result.current_classification
            if precheck_result is not None
            else self._classifier.classify(
                latest_user_message=latest_user_message,
                latest_diary_note=latest_diary_note,
                client_safety_precheck_result=client_safety_precheck_result,
            )
        )

        if classification.mode != SafetyMode.CRISIS and self._has_safe_support_signal(
            latest_user_message=latest_user_message,
            latest_diary_note=latest_diary_note,
            client_safety_precheck_result=client_safety_precheck_result,
        ):
            classification = self._classifier._result(
                mode=SafetyMode.SAFE_SUPPORT,
                flag="safe:elevated_stress",
                started_at=time.perf_counter(),
                triggers={"priority_override": "safe_support_over_close"},
            )

        # Handle explicit stop only after crisis and safe-support priority.
        if stop_requested and classification.mode not in (SafetyMode.CRISIS, SafetyMode.SAFE_SUPPORT):
            return SafetyGateResult(
                mode="closing",
                safety_assessment=SafetyAssessment(
                    risk_level=RiskLevel.low,
                    risk_score=0.0,
                    flags=["stop_intent"],
                    escalation_required=False,
                ),
                risk_flags=["stop_intent"],
                safe_mode=False,
                close_conversation=True,
                stop_requested=True,
                safety_instructions=list(classification.safety_instructions),
            )

        if recent_context_safety_concern and classification.mode == SafetyMode.NORMAL:
            return SafetyGateResult(
                mode="supportive_caution",
                safety_assessment=SafetyAssessment(
                    risk_level=RiskLevel.high,
                    risk_score=0.7,
                    flags=["recent_context:safety_concern"],
                    escalation_required=False,
                ),
                risk_flags=["recent_context:safety_concern"],
                safe_mode=True,
                close_conversation=False,
                stop_requested=False,
                safety_instructions=list(SafetyClassifier.SAFETY_INSTRUCTIONS[SafetyMode.SAFE_SUPPORT]),
            )

        # Convert SafetyMode to legacy mode strings and risk levels
        mode_mapping = {
            SafetyMode.CRISIS: ("crisis", RiskLevel.urgent, 1.0, True),
            SafetyMode.CLOSE_CONVERSATION: ("closing", RiskLevel.low, 0.0, False),
            SafetyMode.SAFE_SUPPORT: ("supportive_caution", RiskLevel.high, 0.7, True),
            SafetyMode.NORMAL: ("normal", RiskLevel.low, 0.0, False),
        }

        legacy_mode, risk_level, risk_score, safe_mode = mode_mapping.get(
            classification.mode, ("normal", RiskLevel.low, 0.0, False)
        )

        resources = (
            self._crisis_resources(client_safety_precheck_result)
            if classification.mode == SafetyMode.CRISIS
            else []
        )
        risk_flags = list(classification.risk_flags)
        if recent_context_safety_concern and classification.mode == SafetyMode.SAFE_SUPPORT:
            risk_flags.append("recent_context:safety_concern")

        return SafetyGateResult(
            mode=legacy_mode,
            safety_assessment=SafetyAssessment(
                risk_level=risk_level,
                risk_score=risk_score,
                flags=risk_flags,
                escalation_required=classification.mode in (SafetyMode.CRISIS, SafetyMode.CLOSE_CONVERSATION),
            ),
            risk_flags=risk_flags,
            safe_mode=safe_mode,
            close_conversation=classification.mode == SafetyMode.CLOSE_CONVERSATION,
            stop_requested=False,
            safety_instructions=list(classification.safety_instructions),
            verified_resources=resources,
        )

    def _has_safe_support_signal(
        self,
        *,
        latest_user_message: str | None,
        latest_diary_note: str | None,
        client_safety_precheck_result: dict[str, Any] | None,
    ) -> bool:
        flags = self._client_flags(client_safety_precheck_result)
        if {"elevated_stress", "low_mood", "isolation"}.intersection(flags):
            return True

        message_text = self._classifier._normalize(latest_user_message)
        diary_text = self._classifier._normalize(latest_diary_note)
        safe_keyword_sets = (
            SafetyClassifier.SAFE_STRESS_KEYWORDS,
            SafetyClassifier.SAFE_SLEEP_KEYWORDS,
            SafetyClassifier.SAFE_ISOLATION_KEYWORDS,
            SafetyClassifier.SAFE_LOW_MOOD_KEYWORDS,
        )
        return any(
            self._classifier._match_keywords(message_text, diary_text, keywords)
            for keywords in safe_keyword_sets
        )

    def has_recent_context_safety_concern(self, texts: Sequence[str]) -> bool:
        merged = self._classifier._normalize(" ".join(text for text in texts if text))
        if not merged:
            return False
        crisis_keyword_sets = (
            SafetyClassifier.CRISIS_SELF_HARM_KEYWORDS,
            SafetyClassifier.CRISIS_HOPELESSNESS_KEYWORDS,
            SafetyClassifier.CRISIS_ACUTE_DISTRESS_KEYWORDS,
        )
        return any(
            self._classifier._match_keywords(merged, None, keywords)
            for keywords in crisis_keyword_sets
        )

    # Legacy methods kept for backward compatibility (deprecated)
    def _client_flags(self, client_safety_precheck_result: dict[str, Any] | None) -> list[str]:
        raw = (client_safety_precheck_result or {}).get("flags", [])
        return [str(item).strip().lower() for item in raw if str(item).strip()]

    def _crisis_resources(self, client_safety_precheck_result: dict[str, Any] | None) -> list[SafetyResource]:
        precheck = dict(client_safety_precheck_result or {})
        country = precheck.get("country") or precheck.get("country_code")
        language = precheck.get("language") or precheck.get("locale") or "ru"
        return self._safety_resource_service.crisis_resources(
            country=str(country).strip() if country else None,
            language=str(language).strip() if language else "ru",
        )

    def _merge_text(self, *parts: str | None) -> str:
        return " ".join(part or "" for part in parts).strip().lower()

    def _keyword_flags(self, text: str, keywords: Sequence[str], *, prefix: str) -> list[str]:
        return [f"{prefix}:{keyword}" for keyword in keywords if keyword in text]

    def _dedupe(self, values: Sequence[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value in seen:
                continue
            seen.add(value)
            out.append(value)
        return out
