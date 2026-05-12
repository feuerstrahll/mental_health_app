"""
Safety Gate Service for mental well-being support bot (MVP).

Deterministic rules-first policy gate that runs before response generation.
The goal is to classify conversation safety mode and enforce restrictions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Sequence


class SafetyPolicyResult(StrEnum):
    NORMAL = "normal"
    CAUTIOUS = "cautious"
    SAFE_MODE = "safe_mode"
    CLOSE_CONVERSATION = "close_conversation"


@dataclass(frozen=True)
class SafetyRule:
    rule_id: str
    category: str
    priority: int
    phrases: tuple[str, ...]
    sources: tuple[str, ...] = ("current_message", "latest_note", "recent_notes", "recent_messages")
    min_matches: int = 1


@dataclass(frozen=True)
class RuleMatch:
    rule_id: str
    category: str
    source: str
    matched_phrases: list[str]


@dataclass
class SafetyGateDecision:
    safe_mode: bool
    risk_flags: list[str]
    close_conversation: bool
    restricted_followup: bool
    allowed_response_mode: str
    safety_reason_codes: list[str]
    recommended_fallback_type: str
    policy_result: str
    debug_metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SafetyGateService:
    """
    Rules-first safety policy resolver.

    Categories:
    - crisis_like_text
    - self_harm_hint
    - severe_hopelessness
    - acute_distress
    - severe_isolation_pattern
    - stop_intent
    - boundary_request
    - hostile_or_rejecting_message
    """

    def __init__(self) -> None:
        self.rule_registry: list[SafetyRule] = self._build_rule_registry()

    def evaluate(
        self,
        *,
        latest_user_chat_message: str | None,
        latest_diary_note: str | None = None,
        recent_diary_notes: Sequence[str] | None = None,
        recent_chat_messages: Sequence[str] | None = None,
        pattern_analysis_output: Mapping[str, Any] | None = None,
        dialogue_state: Mapping[str, Any] | None = None,
        client_safety_precheck: Mapping[str, Any] | None = None,
    ) -> SafetyGateDecision:
        source_texts = self._prepare_sources(
            latest_user_chat_message=latest_user_chat_message,
            latest_diary_note=latest_diary_note,
            recent_diary_notes=recent_diary_notes,
            recent_chat_messages=recent_chat_messages,
        )

        matches = self._match_rules(source_texts)
        matched_categories = {match.category for match in matches}

        context_categories, context_reason_codes = self._derive_context_categories(
            source_texts=source_texts,
            pattern_analysis_output=pattern_analysis_output,
        )
        matched_categories.update(context_categories)

        precheck_categories, precheck_reason_codes, precheck_flags = self._derive_precheck_categories(
            client_safety_precheck=client_safety_precheck
        )
        matched_categories.update(precheck_categories)

        policy, override_source = self._resolve_policy(
            categories=matched_categories,
            dialogue_state=dialogue_state or {},
            client_safety_precheck=client_safety_precheck or {},
        )
        restrictions = self._policy_restrictions(policy)

        safe_mode = policy in (SafetyPolicyResult.SAFE_MODE, SafetyPolicyResult.CLOSE_CONVERSATION)
        close_conversation = policy == SafetyPolicyResult.CLOSE_CONVERSATION
        restricted_followup = policy != SafetyPolicyResult.NORMAL

        rule_reason_codes = [match.rule_id for match in matches]
        safety_reason_codes = self._unique(
            [override_source] + precheck_reason_codes + context_reason_codes + rule_reason_codes
        )
        risk_flags = self._unique(sorted(matched_categories) + precheck_flags)

        debug_metadata = {
            "matched_categories": sorted(matched_categories),
            "matched_rule_ids": self._unique([match.rule_id for match in matches]),
            "policy_chosen": policy.value,
            "override_source": override_source or "none",
            "matched_rules": [asdict(match) for match in matches],
            "response_restrictions": restrictions,
            "source_lengths": {name: len(text) for name, text in source_texts.items()},
        }

        return SafetyGateDecision(
            safe_mode=safe_mode,
            risk_flags=risk_flags,
            close_conversation=close_conversation,
            restricted_followup=restricted_followup,
            allowed_response_mode=self._allowed_response_mode(policy),
            safety_reason_codes=safety_reason_codes,
            recommended_fallback_type=self._fallback_type(policy),
            policy_result=policy.value,
            debug_metadata=debug_metadata,
        )

    def _build_rule_registry(self) -> list[SafetyRule]:
        return sorted(
            [
                SafetyRule(
                    rule_id="stop_intent.direct_stop",
                    category="stop_intent",
                    priority=100,
                    phrases=(
                        "stop",
                        "not now",
                        "enough for now",
                        "let's stop",
                        "later",
                        "leave me alone",
                        "i don't want to continue",
                        "не сейчас",
                        "хватит на сегодня",
                        "давай остановимся",
                        "не хочу продолжать",
                    ),
                    sources=("current_message",),
                ),
                SafetyRule(
                    rule_id="boundary_request.no_questions",
                    category="boundary_request",
                    priority=90,
                    phrases=(
                        "don't ask",
                        "no more questions",
                        "stop asking",
                        "don't push",
                        "respect my boundaries",
                        "не задавай вопросов",
                        "без вопросов",
                        "не дави",
                    ),
                    sources=("current_message",),
                ),
                SafetyRule(
                    rule_id="hostile_or_rejecting_message.rejection",
                    category="hostile_or_rejecting_message",
                    priority=85,
                    phrases=(
                        "go away",
                        "shut up",
                        "leave me alone",
                        "you're useless",
                        "отстань",
                        "уйди",
                        "замолчи",
                    ),
                    sources=("current_message",),
                ),
                SafetyRule(
                    rule_id="self_harm_hint.direct_hint",
                    category="self_harm_hint",
                    priority=95,
                    phrases=(
                        "harm myself",
                        "hurt myself",
                        "self harm",
                        "навредить себе",
                        "причинить себе вред",
                    ),
                    sources=("current_message", "latest_note"),
                ),
                SafetyRule(
                    rule_id="crisis_like_text.nonexistence",
                    category="crisis_like_text",
                    priority=94,
                    phrases=(
                        "want to disappear",
                        "don't want to exist",
                        "no point in continuing",
                        "исчезнуть",
                        "не хочу существовать",
                        "не вижу смысла продолжать",
                    ),
                    sources=("current_message", "latest_note"),
                ),
                SafetyRule(
                    rule_id="severe_hopelessness.explicit",
                    category="severe_hopelessness",
                    priority=88,
                    phrases=(
                        "hopeless",
                        "no way out",
                        "nothing helps",
                        "безнадежно",
                        "нет выхода",
                        "ничего не поможет",
                    ),
                    sources=("current_message", "latest_note", "recent_notes"),
                ),
                SafetyRule(
                    rule_id="acute_distress.high_intensity",
                    category="acute_distress",
                    priority=86,
                    phrases=(
                        "panic attack",
                        "can't breathe",
                        "breaking down",
                        "unbearable",
                        "паника",
                        "накрывает",
                        "невыносимо",
                        "срыв",
                    ),
                ),
                SafetyRule(
                    rule_id="severe_isolation_pattern.text_signals",
                    category="severe_isolation_pattern",
                    priority=82,
                    phrases=(
                        "nobody",
                        "no one",
                        "completely alone",
                        "isolated",
                        "никого нет",
                        "совсем один",
                        "полная изоляция",
                    ),
                    sources=("current_message", "latest_note", "recent_notes"),
                ),
            ],
            key=lambda item: item.priority,
            reverse=True,
        )

    def _prepare_sources(
        self,
        *,
        latest_user_chat_message: str | None,
        latest_diary_note: str | None,
        recent_diary_notes: Sequence[str] | None,
        recent_chat_messages: Sequence[str] | None,
    ) -> dict[str, str]:
        recent_notes_compact = " ".join((recent_diary_notes or [])[-3:])
        recent_messages_compact = " ".join((recent_chat_messages or [])[-3:])
        return {
            "current_message": self._normalize_text(latest_user_chat_message),
            "latest_note": self._normalize_text(latest_diary_note),
            "recent_notes": self._normalize_text(recent_notes_compact),
            "recent_messages": self._normalize_text(recent_messages_compact),
        }

    def _match_rules(self, source_texts: Mapping[str, str]) -> list[RuleMatch]:
        matches: list[RuleMatch] = []
        for rule in self.rule_registry:
            for source in rule.sources:
                text = source_texts.get(source, "")
                if not text:
                    continue
                matched_phrases = [phrase for phrase in rule.phrases if phrase in text]
                if len(matched_phrases) >= rule.min_matches:
                    matches.append(
                        RuleMatch(
                            rule_id=rule.rule_id,
                            category=rule.category,
                            source=source,
                            matched_phrases=matched_phrases,
                        )
                    )
        return matches

    def _derive_context_categories(
        self,
        *,
        source_texts: Mapping[str, str],
        pattern_analysis_output: Mapping[str, Any] | None,
    ) -> tuple[set[str], list[str]]:
        categories: set[str] = set()
        reason_codes: list[str] = []

        analysis = dict(pattern_analysis_output or {})
        contributing_factors = {
            str(item).strip().lower()
            for item in analysis.get("contributing_factors", []) or []
        }
        note_signals = {
            str(item).strip().lower()
            for item in analysis.get("note_signals", []) or []
        }
        support_profile = str(analysis.get("support_profile", "")).strip().lower()
        support_need_score = self._to_float(analysis.get("support_need_score"))

        isolation_text = any(
            marker in source_texts.get(name, "")
            for name in ("current_message", "latest_note", "recent_notes")
            for marker in ("nobody", "no one", "alone", "isolat", "никого", "один", "изоляц")
        )
        social_withdrawal = (
            "low_social_connectedness" in contributing_factors
            or "isolation_language" in note_signals
            or support_profile in {"depleted_pattern", "unstable_pattern"}
        )

        if isolation_text and social_withdrawal:
            categories.add("severe_isolation_pattern")
            reason_codes.append("ctx.isolation_text_plus_structured")
        elif social_withdrawal and support_need_score >= 0.65:
            categories.add("severe_isolation_pattern")
            reason_codes.append("ctx.structured_isolation_high_need")

        return categories, reason_codes

    def _derive_precheck_categories(
        self,
        *,
        client_safety_precheck: Mapping[str, Any] | None,
    ) -> tuple[set[str], list[str], list[str]]:
        categories: set[str] = set()
        reason_codes: list[str] = []
        risk_flags: list[str] = []

        precheck = dict(client_safety_precheck or {})
        status = str(precheck.get("status", "pass")).strip().lower()
        flags = [str(item).strip().lower() for item in precheck.get("flags", []) or []]
        safe_required = bool(precheck.get("safe_response_required", False))

        for flag in flags:
            risk_flags.append(f"client_precheck:{flag}")

        if status == "blocked":
            categories.add("acute_distress")
            reason_codes.append("precheck.blocked")
        elif status == "flagged":
            categories.add("acute_distress")
            reason_codes.append("precheck.flagged")

        if safe_required:
            categories.add("acute_distress")
            reason_codes.append("precheck.safe_response_required")

        return categories, reason_codes, risk_flags

    def _resolve_policy(
        self,
        *,
        categories: set[str],
        dialogue_state: Mapping[str, Any],
        client_safety_precheck: Mapping[str, Any],
    ) -> tuple[SafetyPolicyResult, str | None]:
        precheck_status = str(client_safety_precheck.get("status", "pass")).strip().lower()
        safe_required = bool(client_safety_precheck.get("safe_response_required", False))
        previous_policy = str(dialogue_state.get("previous_policy", "")).strip().lower()

        if "stop_intent" in categories:
            return SafetyPolicyResult.CLOSE_CONVERSATION, "policy.stop_intent_override"

        if previous_policy == SafetyPolicyResult.SAFE_MODE.value and "boundary_request" in categories:
            return SafetyPolicyResult.CLOSE_CONVERSATION, "policy.safe_mode_then_boundary_close"

        if "self_harm_hint" in categories:
            return SafetyPolicyResult.SAFE_MODE, "policy.self_harm_override"

        if "crisis_like_text" in categories:
            return SafetyPolicyResult.SAFE_MODE, "policy.crisis_text_override"

        if "severe_hopelessness" in categories:
            return SafetyPolicyResult.SAFE_MODE, "policy.hopelessness_override"

        if precheck_status == "blocked":
            return SafetyPolicyResult.SAFE_MODE, "policy.client_precheck_blocked"

        if "hostile_or_rejecting_message" in categories and "boundary_request" in categories:
            return SafetyPolicyResult.CLOSE_CONVERSATION, "policy.hostile_boundary_close"

        if "acute_distress" in categories:
            return SafetyPolicyResult.CAUTIOUS, "policy.acute_distress"

        if "severe_isolation_pattern" in categories:
            return SafetyPolicyResult.CAUTIOUS, "policy.severe_isolation"

        if "boundary_request" in categories:
            return SafetyPolicyResult.CAUTIOUS, "policy.boundary_request"

        if "hostile_or_rejecting_message" in categories:
            return SafetyPolicyResult.CAUTIOUS, "policy.hostile_rejection"

        if precheck_status == "flagged" or safe_required:
            return SafetyPolicyResult.CAUTIOUS, "policy.client_precheck_cautious"

        return SafetyPolicyResult.NORMAL, "policy.default_normal"

    def _policy_restrictions(self, policy: SafetyPolicyResult) -> dict[str, Any]:
        if policy == SafetyPolicyResult.NORMAL:
            return {
                "allow_followup": True,
                "max_soft_questions": 2,
                "restrict_recommendation_types": False,
                "simplify_language": False,
                "block_speculative_interpretation": False,
            }
        if policy == SafetyPolicyResult.CAUTIOUS:
            return {
                "allow_followup": True,
                "max_soft_questions": 1,
                "restrict_recommendation_types": True,
                "simplify_language": True,
                "block_speculative_interpretation": True,
            }
        if policy == SafetyPolicyResult.SAFE_MODE:
            return {
                "allow_followup": False,
                "max_soft_questions": 0,
                "restrict_recommendation_types": True,
                "simplify_language": True,
                "block_speculative_interpretation": True,
            }
        return {
            "allow_followup": False,
            "max_soft_questions": 0,
            "restrict_recommendation_types": True,
            "simplify_language": True,
            "block_speculative_interpretation": True,
        }

    def _allowed_response_mode(self, policy: SafetyPolicyResult) -> str:
        if policy == SafetyPolicyResult.NORMAL:
            return "normal"
        if policy == SafetyPolicyResult.CAUTIOUS:
            return "cautious"
        if policy == SafetyPolicyResult.SAFE_MODE:
            return "safe_mode"
        return "closing"

    def _fallback_type(self, policy: SafetyPolicyResult) -> str:
        if policy == SafetyPolicyResult.NORMAL:
            return "none"
        if policy == SafetyPolicyResult.CAUTIOUS:
            return "cautious_checkin_template"
        if policy == SafetyPolicyResult.SAFE_MODE:
            return "grounding_support_template"
        return "respectful_closure_template"

    def _normalize_text(self, value: str | None) -> str:
        if not value:
            return ""
        return (
            value.lower()
            .replace("’", "'")
            .replace("“", '"')
            .replace("”", '"')
            .strip()
        )

    def _to_float(self, value: Any) -> float:
        try:
            if value is None:
                return 0.0
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _unique(self, values: Sequence[str | None]) -> list[str]:
        seen: set[str] = set()
        unique_values: list[str] = []
        for item in values:
            if not item:
                continue
            if item in seen:
                continue
            seen.add(item)
            unique_values.append(item)
        return unique_values


def _run_self_check() -> None:
    service = SafetyGateService()

    scenarios = [
        (
            "normal",
            dict(
                latest_user_chat_message="I had a rough day but I want to keep talking calmly.",
                latest_diary_note="Tired but trying to rest.",
                recent_diary_notes=["Worked a lot", "Will sleep earlier"],
                pattern_analysis_output={"support_need_score": 0.35, "contributing_factors": []},
            ),
            SafetyPolicyResult.NORMAL.value,
        ),
        (
            "stop_intent",
            dict(
                latest_user_chat_message="Not now, let's stop.",
                latest_diary_note="too much for me",
            ),
            SafetyPolicyResult.CLOSE_CONVERSATION.value,
        ),
        (
            "safe_mode_crisis_like",
            dict(
                latest_user_chat_message="I don't want to exist anymore.",
                latest_diary_note="Everything feels pointless.",
            ),
            SafetyPolicyResult.SAFE_MODE.value,
        ),
        (
            "cautious_isolation",
            dict(
                latest_user_chat_message="I feel completely alone.",
                latest_diary_note="nobody is around",
                pattern_analysis_output={
                    "support_need_score": 0.7,
                    "support_profile": "depleted_pattern",
                    "contributing_factors": ["low_social_connectedness"],
                },
            ),
            SafetyPolicyResult.CAUTIOUS.value,
        ),
    ]

    for scenario_name, payload, expected_policy in scenarios:
        decision = service.evaluate(**payload)
        assert decision.policy_result == expected_policy, (
            f"{scenario_name}: expected {expected_policy}, got {decision.policy_result}"
        )
        assert isinstance(decision.risk_flags, list)
        assert isinstance(decision.safety_reason_codes, list)
    print("SafetyGateService self-check passed.")


if __name__ == "__main__":
    _run_self_check()
