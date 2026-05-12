from app.services.orchestration.decision_pipeline import SafetyGateService
from app.services.safety.safety_classifier import SafetyClassifier


class _CountingSafetyClassifier(SafetyClassifier):
    def __init__(self) -> None:
        self.classify_calls = 0

    def classify(self, **kwargs):  # type: ignore[override]
        self.classify_calls += 1
        return super().classify(**kwargs)


def test_old_memory_content_does_not_trigger_crisis() -> None:
    service = SafetyGateService()

    result = service.evaluate(
        latest_user_message="I had a difficult day but I am safe now",
        latest_diary_note="Trying to rest and recover",
        stop_requested=False,
        client_safety_precheck_result={"flags": []},
    )

    assert result.mode == "normal"
    assert result.safety_assessment.risk_level.value == "low"


def test_current_explicit_crisis_still_triggers_crisis() -> None:
    service = SafetyGateService()
    precheck = service.precheck(
        latest_user_message="I want to kill myself",
        latest_diary_note=None,
        client_safety_precheck_result={"flags": []},
    )

    result = service.evaluate(
        latest_user_message="I want to kill myself",
        latest_diary_note=None,
        stop_requested=False,
        client_safety_precheck_result={"flags": []},
        precheck_result=precheck,
        recent_context_safety_concern=True,
    )

    assert result.mode == "crisis"
    assert result.safety_assessment.risk_level.value == "urgent"
    assert result.safety_assessment.escalation_required is True


def test_recent_context_concern_is_supportive_caution_not_crisis() -> None:
    service = SafetyGateService()
    precheck = service.precheck(
        latest_user_message="okay thanks",
        latest_diary_note=None,
        client_safety_precheck_result={"flags": []},
    )

    result = service.evaluate(
        latest_user_message="okay thanks",
        latest_diary_note=None,
        stop_requested=False,
        client_safety_precheck_result={"flags": []},
        precheck_result=precheck,
        recent_context_safety_concern=True,
    )

    assert result.mode == "supportive_caution"
    assert result.safety_assessment.risk_level.value == "high"
    assert result.safety_assessment.escalation_required is False
    assert result.risk_flags == ["recent_context:safety_concern"]


def test_evaluate_reuses_precheck_classification() -> None:
    service = SafetyGateService()
    classifier = _CountingSafetyClassifier()
    service._classifier = classifier

    precheck = service.precheck(
        latest_user_message="I feel okay",
        latest_diary_note=None,
        client_safety_precheck_result={"flags": []},
    )
    result = service.evaluate(
        latest_user_message="I feel okay",
        latest_diary_note=None,
        stop_requested=False,
        client_safety_precheck_result={"flags": []},
        precheck_result=precheck,
    )

    assert result.mode == "normal"
    assert classifier.classify_calls == 1
