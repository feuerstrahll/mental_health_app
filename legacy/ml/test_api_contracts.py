"""Validation smoke tests for ML server API contracts."""

from __future__ import annotations

import copy
import json
from pydantic import ValidationError

from api_contracts import (
    AGGREGATED_ONLY_EXAMPLE,
    AGGREGATED_PLUS_TEXT_EXAMPLE,
    DataMode,
    DecisionRequest,
    FollowupType,
    FollowupMode,
    RecommendationResponseMode,
    RecommendationService,
    ResponseMode,
    SupportProfile,
    build_decision_response,
)


def assert_raises_validation(payload: dict, case_name: str) -> None:
    try:
        DecisionRequest.model_validate(payload)
    except ValidationError:
        print(f"PASS {case_name}: correctly rejected")
        return
    raise AssertionError(f"{case_name}: expected validation error")


def main() -> None:
    print("=" * 70)
    print("API CONTRACT TESTS")
    print("=" * 70)

    # Example JSON for both modes
    print("\n[Example JSON] aggregated_only")
    print(json.dumps(AGGREGATED_ONLY_EXAMPLE, ensure_ascii=False, indent=2))

    print("\n[Example JSON] aggregated_plus_text")
    print(json.dumps(AGGREGATED_PLUS_TEXT_EXAMPLE, ensure_ascii=False, indent=2))

    # 1) Required + optional fields validation (aggregated_only)
    req1 = DecisionRequest.model_validate(AGGREGATED_ONLY_EXAMPLE)
    assert req1.mode == DataMode.AGGREGATED_ONLY
    assert req1.user_message is None
    assert req1.note_text is None
    print("PASS required/optional fields: aggregated_only parsed")

    # 2) Required + optional fields validation (aggregated_plus_text)
    req2 = DecisionRequest.model_validate(AGGREGATED_PLUS_TEXT_EXAMPLE)
    assert req2.mode == DataMode.AGGREGATED_PLUS_TEXT
    assert req2.has_text_input
    print("PASS required/optional fields: aggregated_plus_text parsed")

    # 3) aggregated_only cannot contain text
    bad_mode_payload = copy.deepcopy(AGGREGATED_ONLY_EXAMPLE)
    bad_mode_payload["user_message"] = "Просто тест"
    assert_raises_validation(bad_mode_payload, "aggregated_only_with_text")

    # 4) Explicit no-text handling in aggregated_plus_text mode
    no_text_payload = copy.deepcopy(AGGREGATED_PLUS_TEXT_EXAMPLE)
    no_text_payload.pop("user_message", None)
    no_text_payload.pop("note_text", None)
    no_text_request = DecisionRequest.model_validate(no_text_payload)
    response_no_text = build_decision_response(
        no_text_request,
        support_profile=SupportProfile.ELEVATED_STRESS_PATTERN,
        support_need_score=0.71,
        confidence=0.74,
        response_mode=ResponseMode.TEMPLATE_ONLY,
        recommended_practice="breathing_2min",
        followup_type=FollowupType.SOFT_CHECKIN_24H,
        escalate=False,
        safe_response_required=False,
    )
    assert any(signal.code == "no_text_input" for signal in response_no_text.note_signals)
    print("PASS explicit no-text handling: note_signals include no_text_input")

    # 5) Explicit low-confidence handling
    low_conf_response = build_decision_response(
        req2,
        support_profile=SupportProfile.UNSTABLE_PATTERN,
        support_need_score=0.66,
        confidence=0.32,
        response_mode=ResponseMode.TEMPLATE_ONLY,
        recommended_practice="grounding_5_4_3_2_1",
        followup_type=FollowupType.NONE,
        escalate=False,
        safe_response_required=False,
    )
    assert low_conf_response.safe_response_required is True
    assert low_conf_response.response_mode == ResponseMode.SAFETY_TEMPLATE_ONLY
    assert low_conf_response.followup_type == FollowupType.SOFT_CHECKIN_24H
    assert any(
        signal.code == "low_confidence_prediction"
        for signal in low_conf_response.note_signals
    )
    print("PASS low-confidence handling: safe response policy enforced")

    # 6) PII filtering in text
    pii_payload = copy.deepcopy(AGGREGATED_PLUS_TEXT_EXAMPLE)
    pii_payload["note_text"] = "Моя почта user@example.com"
    assert_raises_validation(pii_payload, "pii_in_text")

    # 7) Missing required field
    missing_required = copy.deepcopy(AGGREGATED_ONLY_EXAMPLE)
    missing_required.pop("client_version", None)
    assert_raises_validation(missing_required, "missing_required_client_version")

    # 8) Optional fields can be omitted
    optional_omitted = copy.deepcopy(AGGREGATED_ONLY_EXAMPLE)
    optional_omitted["aggregated_features"].pop("avg_energy_7d", None)
    optional_omitted["aggregated_features"].pop("checkins_count_14d", None)
    parsed_optional = DecisionRequest.model_validate(optional_omitted)
    assert parsed_optional.aggregated_features.avg_energy_7d is None
    assert parsed_optional.aggregated_features.checkins_count_14d is None
    print("PASS optional fields can be omitted")

    # 9) RecommendationService: close conversation on stop intent
    recommendation_service = RecommendationService()
    rec_close = recommendation_service.recommend(
        pattern_analysis_output={
            "support_profile": "unstable_pattern",
            "support_need_score": 0.82,
            "confidence": "high",
        },
        safety_output={
            "safe_mode": False,
            "close_conversation": True,
            "risk_flags": ["stop_intent"],
        },
        conversation_state={"stop_requested": True},
    )
    assert rec_close.recommended_action == "closing_support_message"
    assert rec_close.response_mode == RecommendationResponseMode.CLOSING_SUPPORT.value
    assert rec_close.followup_mode == FollowupMode.CLOSE_CONVERSATION.value
    assert rec_close.should_continue_dialogue is False
    print("PASS recommendation close mode: stop intent / close override respected")

    # 10) RecommendationService: safe mode restrictions
    rec_safe = recommendation_service.recommend(
        pattern_analysis_output={
            "support_profile": "overload_pattern",
            "support_need_score": 0.74,
            "confidence": "medium",
            "contributing_factors": ["emotional_instability"],
        },
        safety_output={
            "safe_mode": True,
            "close_conversation": False,
            "risk_flags": ["acute_distress"],
        },
        recommendation_history=["grounding_5_senses"],
    )
    assert rec_safe.response_mode == RecommendationResponseMode.SAFE_SUPPORT.value
    assert rec_safe.followup_mode == FollowupMode.NO_FOLLOWUP.value
    assert rec_safe.should_continue_dialogue is False
    assert rec_safe.recommended_action in {
        "grounding_5_senses",
        "breathing_478",
        "gentle_reflection_only",
    }
    print("PASS recommendation safe mode: restricted non-probing behavior")

    # 11) RecommendationService: depleted profile mapping
    rec_depleted = recommendation_service.recommend(
        pattern_analysis_output={
            "support_profile": "depleted_pattern",
            "support_need_score": 0.66,
            "confidence": "medium",
            "contributing_factors": ["low_sleep", "poor_sleep_quality", "low_activity"],
        },
        safety_output={"safe_mode": False, "close_conversation": False, "risk_flags": []},
        recommendation_history=["rest_permission_message"],
    )
    assert rec_depleted.recommended_action in {
        "hydration_pause",
        "tiny_step_reset",
        "short_walk",
        "rest_permission_message",
    }
    assert rec_depleted.response_mode in {
        RecommendationResponseMode.REFLECTIVE_SUPPORT.value,
        RecommendationResponseMode.ACTION_SUPPORT.value,
    }
    print("PASS recommendation mapping: depleted profile gives small restorative action")

    # 12) RecommendationService: repetition avoidance
    rec_repeat = recommendation_service.recommend(
        pattern_analysis_output={
            "support_profile": "overload_pattern",
            "support_need_score": 0.61,
            "confidence": "medium",
            "contributing_factors": ["emotional_instability"],
        },
        safety_output={"safe_mode": False, "close_conversation": False, "risk_flags": []},
        recommendation_history=["breathing_478", "box_breathing", "breathing_478"],
    )
    assert rec_repeat.recommended_action != "breathing_478"
    print("PASS repetition control: avoids same action in recent window")

    # 13) build_decision_response auto recommendation mapping
    auto_rec_response = build_decision_response(
        req2,
        support_profile=SupportProfile.DEPLETED_PATTERN,
        support_need_score=0.64,
        confidence=0.71,
        risk_flags=[],
        note_signals=[],
        safe_response_required=False,
        pattern_analysis_output={
            "support_profile": "depleted_pattern",
            "support_need_score": 0.64,
            "confidence": "medium",
            "contributing_factors": ["low_sleep", "low_activity"],
        },
        safety_output={
            "safe_mode": False,
            "close_conversation": False,
            "risk_flags": [],
        },
    )
    assert auto_rec_response.recommended_practice is not None
    assert auto_rec_response.followup_type in {
        FollowupType.SOFT_CHECKIN_24H,
        FollowupType.PROACTIVE_CHECKIN_3H,
        FollowupType.NONE,
    }
    assert auto_rec_response.response_mode in {
        ResponseMode.TEMPLATE_ONLY,
        ResponseMode.SAFETY_TEMPLATE_ONLY,
    }
    print("PASS build_decision_response: recommendation service integrated")

    print("\n" + "=" * 70)
    print("ALL API CONTRACT TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
