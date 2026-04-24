"""
Integration tests for SafetyGateService.

Run:
    python integration_test.py
"""

from clinical_rules import SafetyGateService, SafetyPolicyResult


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected={expected}, actual={actual}")


def run_integration_tests() -> None:
    service = SafetyGateService()

    # 1) Normal flow
    decision = service.evaluate(
        latest_user_chat_message="I feel stressed but manageable. Let's plan tomorrow.",
        latest_diary_note="Had a busy day.",
        recent_diary_notes=["busy", "sleep was okay"],
        pattern_analysis_output={
            "support_need_score": 0.28,
            "support_profile": "stable_pattern",
            "contributing_factors": [],
        },
        dialogue_state={"previous_policy": "normal"},
    )
    assert_equal(decision.policy_result, SafetyPolicyResult.NORMAL.value, "normal policy")
    assert_equal(decision.safe_mode, False, "normal safe_mode")

    # 2) Stop intent overrides everything
    decision = service.evaluate(
        latest_user_chat_message="Enough for now, let's stop.",
        latest_diary_note="I am overwhelmed",
        pattern_analysis_output={
            "support_need_score": 0.78,
            "support_profile": "unstable_pattern",
            "contributing_factors": ["emotional_instability"],
        },
    )
    assert_equal(decision.policy_result, SafetyPolicyResult.CLOSE_CONVERSATION.value, "stop override")
    assert_equal(decision.close_conversation, True, "close conversation")
    assert_equal(decision.restricted_followup, True, "no probing after stop")

    # 3) Crisis-like text enforces safe_mode
    decision = service.evaluate(
        latest_user_chat_message="I don't want to exist.",
        latest_diary_note="No way out",
        recent_diary_notes=["nothing helps"],
        dialogue_state={"previous_policy": "normal"},
    )
    assert_equal(decision.policy_result, SafetyPolicyResult.SAFE_MODE.value, "safe mode for crisis-like text")
    assert_equal(decision.safe_mode, True, "safe_mode true")
    assert_equal(decision.close_conversation, False, "not forced close unless stop intent")

    # 4) Structured + text isolation pattern
    decision = service.evaluate(
        latest_user_chat_message="I am completely alone.",
        latest_diary_note="Nobody to talk to.",
        pattern_analysis_output={
            "support_need_score": 0.71,
            "support_profile": "depleted_pattern",
            "contributing_factors": ["low_social_connectedness", "low_activity"],
            "note_signals": ["isolation_language"],
        },
    )
    assert_equal(decision.policy_result, SafetyPolicyResult.CAUTIOUS.value, "cautious isolation")
    assert "severe_isolation_pattern" in decision.risk_flags

    # 5) Client precheck can force cautious mode
    decision = service.evaluate(
        latest_user_chat_message="I had a hard day.",
        client_safety_precheck={
            "status": "flagged",
            "flags": ["acute_distress_hint"],
            "safe_response_required": True,
        },
    )
    assert_equal(decision.policy_result, SafetyPolicyResult.CAUTIOUS.value, "client precheck cautious")
    assert any(flag.startswith("client_precheck:") for flag in decision.risk_flags)

    # 6) Boundary + hostility after previous safe mode closes conversation
    decision = service.evaluate(
        latest_user_chat_message="Don't ask me anything else, go away.",
        dialogue_state={"previous_policy": "safe_mode"},
    )
    assert_equal(
        decision.policy_result,
        SafetyPolicyResult.CLOSE_CONVERSATION.value,
        "safe_mode + boundary close",
    )

    print("SafetyGateService integration tests passed.")


if __name__ == "__main__":
    run_integration_tests()
