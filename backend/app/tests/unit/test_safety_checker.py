from app.services.safety.safety_checker import SafetyChecker


def test_safety_checker_high_risk() -> None:
    checker = SafetyChecker()
    result = checker.assess(risk_score=0.8, flags=["critical_emotion_marker"])

    assert result.risk_level.value == "high"
    assert result.escalation_required is True
