"""
Unit tests for SafetyClassifier.

Tests cover:
- All 4 modes (CRISIS, CLOSE_CONVERSATION, SAFE_SUPPORT, NORMAL)
- Boundary conditions and edge cases
- Priority order (CRISIS > CLOSE > SAFE > NORMAL)
- Keyword matching (EN + RU)
- Client precheck flags
"""

import pytest

from app.services.safety.safety_classifier import SafetyClassifier, SafetyMode


@pytest.fixture
def classifier():
    return SafetyClassifier()


class TestCrisisMode:
    """Tests for CRISIS mode classification."""

    def test_explicit_self_harm_english(self, classifier):
        """CRISIS triggered on explicit self-harm keyword (EN)."""
        result = classifier.classify(latest_user_message="I want to kill myself")
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:explicit_self_harm" in result.risk_flags

    def test_explicit_self_harm_russian(self, classifier):
        """CRISIS triggered on explicit self-harm keyword (RU)."""
        result = classifier.classify(latest_user_message="Я хочу убить себя")
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:explicit_self_harm" in result.risk_flags

    def test_explicit_self_harm_from_diary(self, classifier):
        """CRISIS triggered from diary note with self-harm keyword."""
        result = classifier.classify(latest_diary_note="I'm planning to harm myself")
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:explicit_self_harm" in result.risk_flags

    def test_severe_hopelessness(self, classifier):
        """CRISIS triggered on severe hopelessness keyword."""
        result = classifier.classify(latest_user_message="Everything is hopeless")
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:severe_hopelessness" in result.risk_flags

    def test_severe_hopelessness_russian(self, classifier):
        """CRISIS triggered on severe hopelessness (RU)."""
        result = classifier.classify(latest_user_message="Всё безнадежно")
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:severe_hopelessness" in result.risk_flags

    def test_acute_distress(self, classifier):
        """CRISIS triggered on acute distress keyword."""
        result = classifier.classify(latest_user_message="I'm having a panic attack and can't breathe")
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:acute_distress" in result.risk_flags

    def test_acute_distress_russian(self, classifier):
        """CRISIS triggered on acute distress (RU)."""
        result = classifier.classify(latest_user_message="Панический приступ, не могу дышать")
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:acute_distress" in result.risk_flags

    def test_client_precheck_crisis_flag(self, classifier):
        """CRISIS triggered by client precheck flag."""
        result = classifier.classify(
            latest_user_message="I'm fine",
            client_safety_precheck_result={"flags": ["crisis"]},
        )
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:client_precheck_flagged" in result.risk_flags

    def test_client_precheck_self_harm_flag(self, classifier):
        """CRISIS triggered by client precheck self_harm flag."""
        result = classifier.classify(
            latest_user_message="Just checking",
            client_safety_precheck_result={"flags": ["self_harm"]},
        )
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:client_precheck_flagged" in result.risk_flags

    def test_multiple_crisis_triggers_one_flag(self, classifier):
        """Multiple crisis triggers return single flag (first matched)."""
        result = classifier.classify(
            latest_user_message="I'm dying and want to kill myself"
        )
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:explicit_self_harm" in result.risk_flags

    def test_crisis_priority_over_safe(self, classifier):
        """CRISIS takes priority over SAFE_SUPPORT triggers."""
        result = classifier.classify(
            latest_user_message="I'm stressed and want to die"
        )
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:explicit_self_harm" in result.risk_flags

    def test_cannot_stay_safe_keyword(self, classifier):
        """'cannot stay safe' triggers CRISIS."""
        result = classifier.classify(
            latest_user_message="I can't stay safe anymore"
        )
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:explicit_self_harm" in result.risk_flags


class TestCloseConversationMode:
    """Tests for CLOSE_CONVERSATION mode classification."""

    def test_stop_intent_english(self, classifier):
        """CLOSE triggered on stop intent keyword (EN)."""
        result = classifier.classify(latest_user_message="stop")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION
        assert "close:stop_intent" in result.risk_flags

    def test_stop_intent_russian(self, classifier):
        """CLOSE triggered on stop intent (RU)."""
        result = classifier.classify(latest_user_message="стоп")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION
        assert "close:stop_intent" in result.risk_flags

    def test_boundary_request(self, classifier):
        """CLOSE triggered on boundary request keyword."""
        result = classifier.classify(latest_user_message="don't ask me anything")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION
        assert "close:boundary_request" in result.risk_flags

    def test_boundary_request_russian(self, classifier):
        """CLOSE triggered on boundary request (RU)."""
        result = classifier.classify(latest_user_message="не задавай вопросов")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION
        assert "close:boundary_request" in result.risk_flags

    def test_hostile_and_boundary_combined(self, classifier):
        """CLOSE triggered when both hostile and boundary markers present."""
        result = classifier.classify(latest_user_message="Go away and don't ask me anything")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION
        assert "close:hostile_boundary" in result.risk_flags

    def test_hostile_only_does_not_trigger_close(self, classifier):
        """Hostile alone does not trigger CLOSE, only if combined with boundary."""
        result = classifier.classify(latest_user_message="You're useless")
        # Should escalate to SAFE_SUPPORT or lower, not CLOSE
        assert result.mode != SafetyMode.CLOSE_CONVERSATION

    def test_client_precheck_stop_intent_flag(self, classifier):
        """CLOSE triggered by client precheck stop_intent flag."""
        result = classifier.classify(
            latest_user_message="Hello",
            client_safety_precheck_result={"flags": ["stop_intent"]},
        )
        assert result.mode == SafetyMode.CLOSE_CONVERSATION
        assert "close:client_precheck_stop" in result.risk_flags

    def test_goodbye_keyword(self, classifier):
        """CLOSE triggered on goodbye keyword."""
        result = classifier.classify(latest_user_message="goodbye")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION
        assert "close:stop_intent" in result.risk_flags

    def test_leave_me_alone_keyword(self, classifier):
        """CLOSE triggered on 'leave me alone' keyword."""
        result = classifier.classify(latest_user_message="leave me alone")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION
        assert "close:stop_intent" in result.risk_flags

    def test_close_priority_over_safe(self, classifier):
        """CLOSE takes priority over SAFE_SUPPORT."""
        result = classifier.classify(
            latest_user_message="I'm stressed but stop asking"
        )
        assert result.mode == SafetyMode.CLOSE_CONVERSATION
        assert "close:stop_intent" in result.risk_flags


class TestSafeSupportMode:
    """Tests for SAFE_SUPPORT mode classification."""

    def test_elevated_stress_english(self, classifier):
        """SAFE_SUPPORT triggered on elevated stress keyword (EN)."""
        result = classifier.classify(latest_user_message="I'm so stressed")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:elevated_stress" in result.risk_flags

    def test_elevated_stress_russian(self, classifier):
        """SAFE_SUPPORT triggered on elevated stress (RU)."""
        result = classifier.classify(latest_user_message="Я в стрессе")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:elevated_stress" in result.risk_flags

    def test_sleep_issues(self, classifier):
        """SAFE_SUPPORT triggered on sleep issues keyword."""
        result = classifier.classify(latest_user_message="I can't sleep")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:sleep_issues" in result.risk_flags

    def test_sleep_issues_russian(self, classifier):
        """SAFE_SUPPORT triggered on sleep issues (RU)."""
        result = classifier.classify(latest_user_message="Я не сплю")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:sleep_issues" in result.risk_flags

    def test_isolation_signal(self, classifier):
        """SAFE_SUPPORT triggered on isolation keyword."""
        result = classifier.classify(latest_user_message="I feel so alone")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:isolation_signal" in result.risk_flags

    def test_isolation_signal_russian(self, classifier):
        """SAFE_SUPPORT triggered on isolation (RU)."""
        result = classifier.classify(latest_user_message="Я совсем один")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:isolation_signal" in result.risk_flags

    def test_low_mood(self, classifier):
        """SAFE_SUPPORT triggered on low mood keyword."""
        result = classifier.classify(latest_user_message="I feel so sad")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:low_mood" in result.risk_flags

    def test_low_mood_russian(self, classifier):
        """SAFE_SUPPORT triggered on low mood (RU)."""
        result = classifier.classify(latest_user_message="Мне грустно")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:low_mood" in result.risk_flags

    def test_client_precheck_elevated_stress_flag(self, classifier):
        """SAFE_SUPPORT triggered by client precheck elevated_stress flag."""
        result = classifier.classify(
            latest_user_message="Hi",
            client_safety_precheck_result={"flags": ["elevated_stress"]},
        )
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:client_precheck_caution" in result.risk_flags

    def test_overwhelm_keyword(self, classifier):
        """SAFE_SUPPORT triggered on 'overwhelmed' keyword."""
        result = classifier.classify(latest_user_message="I feel overwhelmed")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:elevated_stress" in result.risk_flags

    def test_exhausted_keyword(self, classifier):
        """SAFE_SUPPORT triggered on 'exhausted' keyword."""
        result = classifier.classify(latest_user_message="I'm exhausted")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:sleep_issues" in result.risk_flags


class TestNormalMode:
    """Tests for NORMAL mode classification."""

    def test_cheerful_message(self, classifier):
        """NORMAL mode for cheerful, no-distress message."""
        result = classifier.classify(latest_user_message="Hi, how are you?")
        assert result.mode == SafetyMode.NORMAL
        assert result.risk_flags == ()

    def test_neutral_question(self, classifier):
        """NORMAL mode for neutral question."""
        result = classifier.classify(latest_user_message="What should I do today?")
        assert result.mode == SafetyMode.NORMAL
        assert result.risk_flags == ()

    def test_empty_message(self, classifier):
        """NORMAL mode for empty message."""
        result = classifier.classify(latest_user_message="")
        assert result.mode == SafetyMode.NORMAL
        assert result.risk_flags == ()

    def test_none_inputs(self, classifier):
        """NORMAL mode when all inputs are None."""
        result = classifier.classify()
        assert result.mode == SafetyMode.NORMAL
        assert result.risk_flags == ()

    def test_whitespace_only(self, classifier):
        """NORMAL mode for whitespace-only input."""
        result = classifier.classify(latest_user_message="   ")
        assert result.mode == SafetyMode.NORMAL
        assert result.risk_flags == ()

    def test_positive_message(self, classifier):
        """NORMAL mode for positive message."""
        result = classifier.classify(latest_user_message="I had a great day today!")
        assert result.mode == SafetyMode.NORMAL
        assert result.risk_flags == ()


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_case_insensitive_matching(self, classifier):
        """Keyword matching is case-insensitive."""
        result = classifier.classify(latest_user_message="STOP")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION

        result = classifier.classify(latest_user_message="Stop")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION

        result = classifier.classify(latest_user_message="sToP")
        assert result.mode == SafetyMode.CLOSE_CONVERSATION

    def test_whitespace_normalization(self, classifier):
        """Whitespace is normalized before matching."""
        result = classifier.classify(latest_user_message="  I want to  die  ")
        assert result.mode == SafetyMode.CRISIS

    def test_mixed_languages(self, classifier):
        """Matching works with mixed EN + RU."""
        result = classifier.classify(latest_user_message="I'm stressed и тревожусь")
        assert result.mode == SafetyMode.SAFE_SUPPORT
        assert "safe:elevated_stress" in result.risk_flags

    def test_negation_handled(self, classifier):
        """'I'm not sad' does NOT trigger SAFE_SUPPORT (negation is detected)."""
        result = classifier.classify(latest_user_message="I'm not sad")
        assert result.mode == SafetyMode.NORMAL

    def test_diary_takes_precedence_for_self_harm(self, classifier):
        """Self-harm from diary triggers CRISIS even if message is neutral."""
        result = classifier.classify(
            latest_user_message="Everything is okay",
            latest_diary_note="I'm thinking about self harm",
        )
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:explicit_self_harm" in result.risk_flags

    def test_current_message_takes_precedence_for_hopelessness(self, classifier):
        """Current message is checked first for CRISIS triggers."""
        result = classifier.classify(
            latest_user_message="Everything is hopeless",
            latest_diary_note="I had a good day",
        )
        assert result.mode == SafetyMode.CRISIS
        assert "crisis:severe_hopelessness" in result.risk_flags

    def test_client_flag_with_conflicting_text(self, classifier):
        """Client flag takes priority even if text contradicts."""
        result = classifier.classify(
            latest_user_message="I'm fine",
            client_safety_precheck_result={"flags": ["crisis"]},
        )
        assert result.mode == SafetyMode.CRISIS

    def test_multiple_safe_triggers_one_flag(self, classifier):
        """Multiple SAFE_SUPPORT triggers return only the first matched flag."""
        result = classifier.classify(
            latest_user_message="I'm stressed, can't sleep, and feel alone"
        )
        assert result.mode == SafetyMode.SAFE_SUPPORT
        # First matched in priority order
        assert len(result.risk_flags) == 1


class TestSafetyInstructions:
    """Tests that correct safety instructions are attached to each mode."""

    def test_crisis_instructions(self, classifier):
        """CRISIS mode includes correct safety instructions."""
        result = classifier.classify(latest_user_message="I want to die")
        assert "do_not_ask_questions" in result.safety_instructions
        assert "provide_only_validated_resources" in result.safety_instructions
        assert "keep_response_under_360_chars" in result.safety_instructions

    def test_close_conversation_instructions(self, classifier):
        """CLOSE_CONVERSATION mode includes correct safety instructions."""
        result = classifier.classify(latest_user_message="stop")
        assert "respect_stop_request" in result.safety_instructions
        assert "no_follow_up_question" in result.safety_instructions
        assert "warm_but_final_tone" in result.safety_instructions

    def test_safe_support_instructions(self, classifier):
        """SAFE_SUPPORT mode includes correct safety instructions."""
        result = classifier.classify(latest_user_message="I'm stressed")
        assert "gentle_tone_only" in result.safety_instructions
        assert "no_deep_probing" in result.safety_instructions
        assert "at_most_one_soft_question" in result.safety_instructions

    def test_normal_instructions(self, classifier):
        """NORMAL mode includes correct safety instructions."""
        result = classifier.classify(latest_user_message="Hi")
        assert "empathetic_response" in result.safety_instructions
        assert "standard_supportive_tone" in result.safety_instructions


class TestConfidenceAndMetadata:
    """Tests for confidence score and metadata."""

    def test_confidence_always_1_0(self, classifier):
        """Confidence is always 1.0 for deterministic rules."""
        modes = [
            classifier.classify(latest_user_message="stop"),
            classifier.classify(latest_user_message="I want to die"),
            classifier.classify(latest_user_message="Hi"),
        ]
        for result in modes:
            assert result.confidence == 1.0

    def test_risk_flags_immutable(self, classifier):
        """Risk flags list is immutable."""
        result = classifier.classify(latest_user_message="I want to die")
        with pytest.raises((TypeError, AttributeError)):
            result.risk_flags.append("something")

    def test_result_frozen(self, classifier):
        """SafetyClassification result is frozen/immutable."""
        result = classifier.classify(latest_user_message="Hi")
        with pytest.raises((AttributeError, TypeError)):
            result.mode = SafetyMode.CRISIS
