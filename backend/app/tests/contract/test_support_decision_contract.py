from app.schemas.decision import StructuredDecision, SupportDecisionResponse
from app.schemas.safety import RiskLevel, SafetyAssessment


def test_support_decision_contract_shape() -> None:
    payload = SupportDecisionResponse.model_validate(
        {
            "decision": {
                "support_mode": "guided_checkin",
                "recommended_action": "prompt_short_reflection",
                "reasoning_tags": ["stable_baseline"],
            },
            "safety": {
                "risk_level": RiskLevel.low,
                "risk_score": 0.1,
                "flags": [],
                "escalation_required": False,
            },
            "llm_response": "Support mode: guided_checkin. Recommended action: prompt_short_reflection.",
        }
    )

    assert isinstance(payload.safety, SafetyAssessment)
    assert payload.decision.support_mode == "guided_checkin"
    assert payload.decision.risk_level == "safe"
    assert payload.decision.personalization_level == "none"
    assert payload.decision.memory_retrieval_quality == "none"
    assert payload.decision.support_factors == []
    assert payload.decision.allowed_memory_ids == []


def test_structured_decision_support_confidence_does_not_repurpose_legacy_confidence() -> None:
    decision = StructuredDecision(
        support_mode="context_first_support",
        recommended_action="supportive_response",
        confidence="legacy-medium",
        support_confidence=0.82,
    )

    assert decision.confidence == "legacy-medium"
    assert decision.support_confidence == 0.82
