import asyncio
import json
from datetime import date, datetime

from app.llm.qwen_client import ModelTimeoutError
from app.llm.prompt_builder import PromptBuilder
from app.llm.response_composer import ComposeMeta, ComposeResult, FallbackResponseFactory, QwenResponseService
from app.schemas.decision import StructuredDecision
from app.schemas.wellbeing import WellbeingSignals, WellbeingSignalsRequest
from app.services.context.memory_index_service import RetrievedMemory
from app.services.context.practice_retriever import PracticeRetriever
from app.services.context.recent_context_summary_service import ContextDailyEntry, ContextMemory
from app.services.ml.support_model import AssessorDecisionDraft, AssessorMeta, ContextAssessmentResult, ContextAssessorProtocol
from app.services.orchestration.decision_pipeline import (
    ChatOrchestratorService,
    SafetyResourceService,
    SafetyGateService,
)


GENERIC_RESOURCE_GUIDANCE = SafetyResourceService.GENERIC_UNAVAILABLE_GUIDANCE


class _FakeLLM:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls
        self.latest_user_message: str | None = None

    async def compose(self, *_args, **_kwargs) -> ComposeResult:
        self._calls.append("llm")
        self.latest_user_message = _kwargs.get("latest_user_message")
        return ComposeResult(
            text="Supportive response.",
            meta=ComposeMeta(
                used_fallback=False,
                fallback_reason=None,
                latency_ms=10,
                raw_model_response=None,
            ),
        )


class _TimeoutModelClient:
    async def generate_chat(self, *, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        raise ModelTimeoutError("model_timeout")


class _TrackedSummaryService:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    def build_summary(self, **_kwargs) -> str:
        self._calls.append("summary")
        return "Compact context summary."


class _TrackedSafetyService(SafetyGateService):
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls
        super().__init__()

    def evaluate(self, **kwargs):  # type: ignore[override]
        self._calls.append("safety")
        return super().evaluate(**kwargs)

    def precheck(self, **kwargs):  # type: ignore[override]
        self._calls.append("precheck")
        return super().precheck(**kwargs)


class _TrackedPracticeRetriever(PracticeRetriever):
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls
        super().__init__()

    def retrieve(self, **kwargs):  # type: ignore[override]
        self._calls.append("practice")
        return super().retrieve(**kwargs)


class _TrackedContextAssessorService(ContextAssessorProtocol):
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls

    async def assess(self, **_kwargs):  # type: ignore[override]
        self._calls.append("assessor")
        return _assessment_result(profile="reflective_support", confidence=0.86)


class _StaticContextAssessorService(ContextAssessorProtocol):
    def __init__(self, calls: list[str], result: ContextAssessmentResult) -> None:
        self._calls = calls
        self._result = result

    async def assess(self, **_kwargs):  # type: ignore[override]
        self._calls.append("assessor")
        return self._result


class _TrackedMemoryIndex:
    def __init__(self, calls: list[str]) -> None:
        self._calls = calls
        self.upserted_chunks = []
        self.retrieve_calls = 0

    async def upsert_chunks(self, **_kwargs):
        self._calls.append("chunk_upsert")
        self.upserted_chunks = list(_kwargs.get("chunks") or [])

        class _Res:
            indexed_count = 2
            upserted_count = 2
            reembedded_count = 1
            skipped_count = 1
            used_embedding_provider = "fallback"

        return _Res()

    async def retrieve_relevant(self, **_kwargs):
        self._calls.append("retrieval")
        self.retrieve_calls += 1
        return [
            RetrievedMemory(
                memory_chunk_id="c1",
                source_type="checkin",
                source_id="src1",
                date="2026-05-01",
                text="Date: 2026-05-01. Emotion: stressed.",
                metadata={},
                score=0.7,
            )
        ]


class _EmptyMemoryIndex(_TrackedMemoryIndex):
    async def retrieve_relevant(self, **_kwargs):
        self._calls.append("retrieval")
        self.retrieve_calls += 1
        return []


class _LowScoreMemoryIndex(_TrackedMemoryIndex):
    async def retrieve_relevant(self, **_kwargs):
        self._calls.append("retrieval")
        self.retrieve_calls += 1
        return [
            RetrievedMemory(
                memory_chunk_id="c_low",
                source_type="checkin",
                source_id="src_low",
                date="2026-05-01",
                text="Date: 2026-05-01. Emotion: neutral.",
                metadata={},
                score=0.4,
            )
        ]


class _CrisisVectorMemoryIndex(_TrackedMemoryIndex):
    async def retrieve_relevant(self, **_kwargs):
        self._calls.append("retrieval")
        self.retrieve_calls += 1
        return [
            RetrievedMemory(
                memory_chunk_id="c_crisis_old",
                source_type="chat_message",
                source_id="old_vector",
                date="2026-04-20",
                text="Old retrieved memory: I want to die.",
                metadata={},
                score=0.9,
            )
        ]


class _FailingMemoryIndex(_TrackedMemoryIndex):
    async def retrieve_relevant(self, **_kwargs):
        self._calls.append("retrieval")
        self.retrieve_calls += 1
        raise RuntimeError("vector search failed")


class _TrackedConversationRepository:
    def __init__(self) -> None:
        self.user_messages: list[str] = []
        self.bot_messages: list[str] = []
        self._records: list[dict] = []

    async def upsert_session(self, **_kwargs) -> None:
        return None

    async def save_user_message(self, **kwargs) -> str:
        message_id = f"user_{len(self.user_messages) + 1}"
        self.user_messages.append(kwargs["text_value"])
        self._records.append(
            {
                "id": message_id,
                "role": "user",
                "text": kwargs["text_value"],
                "created_at": datetime(2026, 5, 1, 12, 0, 0),
                "metadata": {
                    "request_id": kwargs["request_id"],
                    "session_id": kwargs["session_id"],
                    "role": "user",
                },
            }
        )
        return message_id

    async def save_bot_message(self, **kwargs) -> str:
        self.bot_messages.append(kwargs["text_value"])
        return f"bot_{len(self.bot_messages)}"

    async def mark_messages_not_current_turn(self, **_kwargs) -> None:
        return None

    async def get_recent_messages(self, **_kwargs):
        return list(self._records)


class _TrackedDailyCommentRepository:
    def __init__(self) -> None:
        self.comments: list[str] = []
        self._records: list[dict] = []

    async def save_comment(self, **kwargs) -> str:
        comment_id = f"daily_{len(self.comments) + 1}"
        self.comments.append(kwargs["comment_text"])
        self._records.append(
            {
                "id": comment_id,
                "entry_date": kwargs["entry_date"],
                "emotion_marker": kwargs["emotion_marker"],
                "comment_text": kwargs["comment_text"],
                "created_at": datetime(2026, 5, 1, 12, 0, 0),
                "metadata": {"request_id": kwargs["request_id"]},
            }
        )
        return comment_id

    async def get_recent_comments(self, **_kwargs):
        return list(self._records)


class _TrackedWellbeingRepository:
    def __init__(self) -> None:
        self.saved_payloads: list[WellbeingSignalsRequest] = []

    async def save(self, *, payload: WellbeingSignalsRequest) -> None:
        self.saved_payloads.append(payload)

    async def get_recent_by_user(self, **_kwargs):
        return []


def _payload(*, diary_note: str | None = "Felt tired after study.") -> WellbeingSignalsRequest:
    return WellbeingSignalsRequest(
        user_id="u1",
        client_timestamp=datetime(2026, 5, 1, 12, 0, 0),
        signals=WellbeingSignals(
            emotion_marker="sad",
            diary_note=diary_note,
            sleep_duration_hours=5.5,
            sleep_regularity=2,
            sleep_quality=2,
            physical_activity_minutes=10,
            sedentary_minutes=600,
            outdoor_minutes=10,
            social_connectedness=2,
            routine_regularity=2,
        ),
    )


def _entry(
    day: int,
    *,
    emotion_marker: str = "sad",
    diary_note: str | None = None,
    sleep_duration_hours: float = 7.0,
    sleep_quality: str = "3",
    sleep_regularity: str = "3",
    social_connectedness_score: float = 3.0,
    routine_regularity: str = "3",
    physical_activity_minutes: float = 30.0,
    outdoor_time_minutes: float = 30.0,
    sedentary_time_minutes: float = 300.0,
) -> ContextDailyEntry:
    return ContextDailyEntry(
        entry_date=date(2026, 5, day),
        emotion_marker=emotion_marker,
        diary_note=diary_note,
        sleep_duration_hours=sleep_duration_hours,
        sleep_quality=sleep_quality,
        sleep_regularity=sleep_regularity,
        social_connectedness_score=social_connectedness_score,
        routine_regularity=routine_regularity,
        physical_activity_minutes=physical_activity_minutes,
        outdoor_time_minutes=outdoor_time_minutes,
        sedentary_time_minutes=sedentary_time_minutes,
    )


def _assessment_result(
    *,
    confidence: float = 0.86,
    abstain: bool = False,
    profile: str = "gentle_checkin",
    raw_risk_hint: str = "safe",
    allowed_memory_ids: list[str] | None = None,
) -> ContextAssessmentResult:
    return ContextAssessmentResult(
        draft=AssessorDecisionDraft(
            support_mode=profile,
            recommended_action="validate_and_ask_one_question",
            raw_risk_hint=raw_risk_hint,
            contributing_factors=["steady_recent_checkins"],
            note_signals=[],
            followup_mode="reflective",
            context_summary="Assessor summary.",
            support_confidence=confidence,
            support_abstain=abstain,
            support_factors=["steady_recent_checkins"],
            allowed_memory_ids=list(allowed_memory_ids if allowed_memory_ids is not None else ["c1"]),
            llm_constraints=[],
        ),
        meta=AssessorMeta(
            used_fallback=abstain,
            fallback_reason="cold_start" if abstain else None,
            latency_ms=1,
        ),
    )


def test_pipeline_stage_order() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_TrackedContextAssessorService(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
        recent_entries_limit=14,
        retrieved_memories_limit=6,
    )

    recent_entries = [
        _entry(
            day,
            emotion_marker="sad",
            diary_note="I feel stressed and cannot cope.",
            sleep_duration_hours=5.5,
        )
        for day in range(25, 31)
    ]

    response = asyncio.run(
        service.run(
            _payload(),
            latest_user_message="Can you suggest one practice?",
            recent_daily_entries=recent_entries,
        )
        )
    assert response.llm_response
    assert response.analysis is not None
    assert response.analysis.support_need_score > 0.0
    assert response.analysis.support_profile == "reflective_support"
    assert response.decision.assessor_action == "validate_and_ask_one_question"
    assert response.decision.recommended_action == "validate_and_ask_one_question"
    assert response.practice_card_id == response.recommended_action
    assert response.recommended_action != response.decision.assessor_action
    assert response.recommended_action_deprecated is True
    dumped = response.model_dump()
    assert dumped["decision"]["assessor_action"] == "validate_and_ask_one_question"
    assert "recommended_action" not in dumped["decision"]
    assert response.decision.support_need_score == response.analysis.support_need_score
    assert calls == ["precheck", "chunk_upsert", "retrieval", "summary", "safety", "assessor", "practice", "llm"]


def test_memory_retrieval_disabled_skips_vector_calls_and_uses_fallback() -> None:
    calls: list[str] = []
    memory_index = _TrackedMemoryIndex(calls)
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_TrackedContextAssessorService(calls),
        memory_index_service=memory_index,
        app_debug=True,
        memory_retrieval_enabled=False,
    )

    response = asyncio.run(
        service.run(
            _payload(),
            latest_user_message="Can you help with stress?",
            recent_daily_entries=[
                _entry(day, emotion_marker="sad", diary_note="Stress at work.", sleep_duration_hours=5.5)
                for day in range(28, 31)
            ],
        )
    )

    assert "chunk_upsert" not in calls
    assert "retrieval" not in calls
    assert memory_index.retrieve_calls == 0
    assert response.response_metadata is not None
    assert response.response_metadata.used_memory_index_fallback is True
    debug = response.response_metadata.debug
    assert debug is not None
    assert debug["memory_retrieval_skipped"] is True
    assert debug["used_memory_index_fallback"] is True
    assert debug["embedding_provider"] == "retrieval_disabled"
    assert debug["retrieved_count"] > 0


def test_qwen_timeout_fallback_does_not_break_pipeline() -> None:
    calls: list[str] = []
    qwen_response_service = QwenResponseService(
        model_client=_TimeoutModelClient(),
        prompt_builder=PromptBuilder(),
        fallback_factory=FallbackResponseFactory(),
        timeout_seconds=0.01,
        max_response_chars=700,
    )
    service = ChatOrchestratorService(
        qwen_response_service=qwen_response_service,
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_TrackedContextAssessorService(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
        recent_entries_limit=14,
        retrieved_memories_limit=6,
    )

    response = asyncio.run(
        service.run(
            _payload(),
            latest_user_message="Can you suggest one practice?",
            recent_daily_entries=[
                _entry(day, emotion_marker="sad", diary_note="I feel stressed.", sleep_duration_hours=5.5)
                for day in range(25, 31)
            ],
        )
    )

    assert response.llm_response
    assert response.llm_meta.used_fallback is True
    assert response.llm_meta.fallback_reason == "model_timeout"

def test_crisis_safety_overrides_assessor_profile() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
    )

    response = asyncio.run(service.run(_payload(), latest_user_message="I want to kill myself"))

    assert response.decision.response_mode == "crisis"
    assert response.decision.risk_level == "crisis"
    assert response.decision.personalization_level == "none"
    assert response.decision.support_profile == "safe_support"
    assert response.decision.practice_cards == []
    assert response.analysis is not None
    assert response.analysis.support_profile == "safe_support"
    assert response.safe_mode is True


def test_recent_context_safety_concern_uses_supportive_caution_not_crisis() -> None:
    calls: list[str] = []
    conversation_repo = _TrackedConversationRepository()
    conversation_repo._records.append(
        {
            "id": "old_concern",
            "role": "user",
            "text": "I want to die",
            "created_at": datetime(2026, 5, 1, 11, 50, 0),
            "metadata": {"request_id": "old_req", "role": "user"},
        }
    )
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
        conversation_repository=conversation_repo,
    )

    response = asyncio.run(
        service.run(
            _payload(diary_note="Had a steady day."),
            latest_user_message="okay, thanks",
        )
    )

    assert response.decision.response_mode == "supportive_caution"
    assert response.decision.risk_level == "safe_support"
    assert response.safe_mode is True
    assert "recent_context:safety_concern" in response.decision.risk_flags
    assert response.safety.escalation_required is False


def test_old_vector_memory_content_does_not_trigger_crisis() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_StaticContextAssessorService(calls, _assessment_result()),
        memory_index_service=_CrisisVectorMemoryIndex(calls),
    )

    response = asyncio.run(
        service.run(
            _payload(diary_note="Had a steady day."),
            latest_user_message="okay, thanks",
        )
    )

    assert response.decision.response_mode == "normal"
    assert response.decision.risk_level == "safe"
    assert response.safe_mode is False


def test_assessor_elevated_hint_maps_to_safe_support() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_StaticContextAssessorService(
            calls,
            _assessment_result(raw_risk_hint="elevated"),
        ),
        memory_index_service=_TrackedMemoryIndex(calls),
        app_debug=True,
    )

    response = asyncio.run(service.run(_payload(diary_note="Had a steady day."), latest_user_message="okay, thanks"))

    assert response.decision.risk_level == "safe_support"
    assert response.decision.response_mode == "supportive_caution"
    assert response.safe_mode is True
    debug = response.response_metadata.debug if response.response_metadata else None
    assert debug is not None
    assert debug["assessor_prompt_version"] == "context_assessor_v1"
    assert debug["assessor_raw_risk_hint"] == "elevated"
    assert debug["deterministic_safety_level"] == "safe"
    assert debug["final_risk_level"] == "safe_support"


def test_assessor_crisis_hint_does_not_create_final_crisis() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_StaticContextAssessorService(
            calls,
            _assessment_result(raw_risk_hint="crisis"),
        ),
        memory_index_service=_TrackedMemoryIndex(calls),
    )

    response = asyncio.run(service.run(_payload(diary_note="Had a steady day."), latest_user_message="okay, thanks"))

    assert response.decision.risk_level == "safe_support"
    assert response.decision.response_mode == "supportive_caution"
    assert response.decision.risk_level != "crisis"


def test_crisis_decision_includes_generic_resource_state_when_unavailable() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
    )

    response = asyncio.run(
        service.run(
            _payload(),
            latest_user_message="I want to kill myself",
            client_safety_precheck_result={"country": "unknown", "language": "ru"},
        )
    )

    assert response.decision.risk_level == "crisis"
    assert response.decision.verified_safety_resources == [GENERIC_RESOURCE_GUIDANCE]
    assert response.decision.practice_cards == []


def test_unknown_country_does_not_create_fake_hotline_numbers() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
    )

    response = asyncio.run(
        service.run(
            _payload(),
            latest_user_message="I want to kill myself",
            client_safety_precheck_result={"country": "ZZ", "language": "ru"},
        )
    )

    resource_blob = " ".join(response.decision.verified_safety_resources)
    assert GENERIC_RESOURCE_GUIDANCE in resource_blob
    assert "http://" not in resource_blob
    assert "https://" not in resource_blob
    assert not any(char.isdigit() for char in resource_blob)


def test_close_conversation_safety_overrides_ml_recommendation() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
    )

    response = asyncio.run(service.run(_payload(diary_note="Had a steady day."), latest_user_message="stop"))

    assert response.decision.response_mode == "closing"
    assert response.decision.risk_level == "closing"
    assert response.decision.personalization_level != "normal"
    assert response.decision.followup_mode == "no_followup"
    assert response.dialogue_state == "closing"
    assert response.should_continue_dialogue is False


def test_safe_support_constrains_followup_behavior() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
    )

    response = asyncio.run(service.run(_payload(), latest_user_message="I'm so stressed"))

    assert response.decision.response_mode == "supportive_caution"
    assert response.decision.risk_level == "safe_support"
    assert response.decision.personalization_level == "none"
    assert response.decision.followup_mode == "no_followup"
    assert response.safe_mode is True
    assert response.dialogue_state == "safe_mode"


def test_safe_support_priority_beats_close_intent() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
    )

    response = asyncio.run(service.run(_payload(), latest_user_message="I'm so stressed, stop asking"))

    assert response.decision.risk_level == "safe_support"
    assert response.decision.response_mode == "supportive_caution"
    assert response.dialogue_state == "safe_mode"


def test_abstain_disables_personalization_and_adds_constraints() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_StaticContextAssessorService(calls, _assessment_result(abstain=True, confidence=0.4)),
        memory_index_service=_TrackedMemoryIndex(calls),
    )

    response = asyncio.run(service.run(_payload(diary_note="Had a steady day."), latest_user_message="Can you suggest one practice?"))

    assert response.decision.support_abstain is True
    assert response.decision.personalization_level == "none"
    assert "Do not infer stable user patterns from limited data." in response.decision.llm_constraints


def test_empty_vector_memory_returns_none_and_no_prompt_memories() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_StaticContextAssessorService(calls, _assessment_result()),
        memory_index_service=_EmptyMemoryIndex(calls),
    )

    response = asyncio.run(service.run(_payload(diary_note="Had a steady day."), latest_user_message="Can you suggest one practice?"))

    assert response.decision.memory_retrieval_quality == "none"
    assert response.decision.relevant_memories == []
    assert response.decision.personalization_level == "light"
    assert 'Do not say "based on your history".' in response.decision.llm_constraints
    assert "Do not claim recurring patterns." in response.decision.llm_constraints
    assert 'Do not say "you usually" or "this keeps happening".' in response.decision.llm_constraints
    assert "Use only current-turn wording for personalization." in response.decision.llm_constraints


def test_low_score_vector_memory_is_weak_and_adds_memory_caution_constraints() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_StaticContextAssessorService(calls, _assessment_result()),
        memory_index_service=_LowScoreMemoryIndex(calls),
    )

    response = asyncio.run(service.run(_payload(diary_note="Had a steady day."), latest_user_message="Can you suggest one practice?"))

    assert response.decision.memory_retrieval_quality == "weak"
    assert response.decision.personalization_level == "light"
    assert 'Do not say "based on your history".' in response.decision.llm_constraints
    assert "Do not claim recurring patterns." in response.decision.llm_constraints
    assert 'Do not say "you usually" or "this keeps happening".' in response.decision.llm_constraints
    assert "Use only current-turn wording for personalization." in response.decision.llm_constraints


def test_memory_retrieval_failure_uses_compact_chronological_fallback() -> None:
    calls: list[str] = []
    conversation_repo = _TrackedConversationRepository()
    for index in range(4):
        conversation_repo._records.append(
            {
                "id": f"old_{index}",
                "role": "user",
                "text": f"Older user-visible context {index}",
                "created_at": datetime(2026, 5, 1, 8 + index, 0, 0),
                "metadata": {"request_id": f"old_req_{index}", "role": "user"},
            }
        )
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_StaticContextAssessorService(
            calls,
            _assessment_result(allowed_memory_ids=["old_2", "old_1", "old_0"]),
        ),
        memory_index_service=_FailingMemoryIndex(calls),
        conversation_repository=conversation_repo,
    )

    response = asyncio.run(service.run(_payload(diary_note="Had a steady day."), latest_user_message="Can you suggest one practice?"))

    assert response.decision.memory_retrieval_quality == "weak"
    assert len(response.decision.relevant_memories) == 3
    assert len(response.decision.allowed_memory_ids) == 3
    assert all("Older user-visible context" in memory for memory in response.decision.relevant_memories)
    assert response.response_metadata is not None
    assert response.response_metadata.used_memory_index_fallback is True


def test_high_confidence_safe_case_with_good_vector_memory_uses_normal_personalization() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        context_assessor_service=_StaticContextAssessorService(calls, _assessment_result(confidence=0.86)),
        memory_index_service=_TrackedMemoryIndex(calls),
    )

    response = asyncio.run(service.run(_payload(diary_note="Had a steady day."), latest_user_message="Can you suggest one practice?"))

    assert response.decision.risk_level == "safe"
    assert response.decision.memory_retrieval_quality == "good"
    assert response.decision.allowed_memory_ids == ["c1"]
    assert response.decision.personalization_level == "normal"


def test_current_turn_or_unconfirmed_score_memories_never_count_as_good() -> None:
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM([]),
        recent_context_summary_service=_TrackedSummaryService([]),
        safety_gate_service=_TrackedSafetyService([]),
        practice_retriever=_TrackedPracticeRetriever([]),
    )
    current_turn_memory = ContextMemory(
        source="chat_message",
        text="Current turn text",
        entry_date=date(2026, 5, 1),
        metadata={
            "retrieval_source": "vector",
            "retrieval_score": 0.99,
            "retrieval_score_direction": "higher_is_better",
            "is_current_turn": True,
        },
    )
    unconfirmed_score_memory = ContextMemory(
        source="chat_message",
        text="Old text",
        entry_date=date(2026, 5, 1),
        metadata={
            "retrieval_source": "vector",
            "retrieval_score": 0.99,
        },
    )

    assert service._memory_retrieval_quality([current_turn_memory]) == "weak"
    assert service._memory_retrieval_quality([unconfirmed_score_memory]) == "weak"


def test_practice_retrieval_uses_existing_support_profiles_for_same_keyword() -> None:
    retriever = PracticeRetriever()

    depleted = retriever.retrieve(
        user_text="Can you suggest one practice?",
        context_summary="Compact context summary.",
        risk_level="low",
        support_profile="depleted_pattern",
        support_need_bucket="high",
        personalization_level="light",
        max_cards=1,
    )
    elevated = retriever.retrieve(
        user_text="Can you suggest one practice?",
        context_summary="Compact context summary.",
        risk_level="low",
        support_profile="elevated_stress_pattern",
        support_need_bucket="high",
        personalization_level="light",
        max_cards=1,
    )

    assert [card.card_id for card in depleted] == ["sleep_winddown"]
    assert [card.card_id for card in elevated] == ["breathing_slow_exhale"]


def test_practice_retrieval_crisis_returns_no_wellness_cards() -> None:
    cards = PracticeRetriever().retrieve(
        user_text="Can you suggest one practice?",
        context_summary="Compact context summary.",
        risk_level="urgent",
        support_profile="crisis_pattern",
        support_need_bucket="high",
        personalization_level="none",
    )

    assert cards == []


def test_practice_retrieval_unknown_profile_uses_keyword_fallback() -> None:
    cards = PracticeRetriever().retrieve(
        user_text="\u041c\u043e\u0436\u043d\u043e \u0434\u044b\u0445\u0430\u043d\u0438\u0435?",
        context_summary="Compact context summary.",
        risk_level="low",
        support_profile="unknown_pattern",
        support_need_bucket="medium",
        personalization_level="light",
        max_cards=1,
    )

    assert [card.card_id for card in cards] == ["breathing_slow_exhale"]


def test_safe_message_persists_raw_text_and_indexes_current_turn() -> None:
    calls: list[str] = []
    conversation_repo = _TrackedConversationRepository()
    daily_repo = _TrackedDailyCommentRepository()
    wellbeing_repo = _TrackedWellbeingRepository()
    memory_index = _TrackedMemoryIndex(calls)
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=memory_index,
        wellbeing_repository=wellbeing_repo,
        conversation_repository=conversation_repo,
        daily_comment_repository=daily_repo,
    )

    asyncio.run(
        service.run(
            _payload(diary_note="Had a steady day."),
            latest_user_message="Can you suggest one practice?",
        )
    )

    assert conversation_repo.user_messages == ["Can you suggest one practice?"]
    assert daily_repo.comments == ["Had a steady day."]
    assert any(chunk.is_current_turn for chunk in memory_index.upserted_chunks)
    assert memory_index.retrieve_calls == 1


def test_safe_support_persists_but_does_not_index_current_turn_raw_text() -> None:
    calls: list[str] = []
    conversation_repo = _TrackedConversationRepository()
    daily_repo = _TrackedDailyCommentRepository()
    memory_index = _TrackedMemoryIndex(calls)
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=memory_index,
        conversation_repository=conversation_repo,
        daily_comment_repository=daily_repo,
    )

    asyncio.run(service.run(_payload(), latest_user_message="I'm so stressed"))

    assert conversation_repo.user_messages == ["I'm so stressed"]
    assert daily_repo.comments == ["Felt tired after study."]
    assert all(not chunk.is_current_turn for chunk in memory_index.upserted_chunks)
    assert all("I'm so stressed" not in chunk.text for chunk in memory_index.upserted_chunks)
    assert memory_index.retrieve_calls == 1


def test_crisis_skips_raw_persistence_indexing_and_keeps_current_text_for_response() -> None:
    calls: list[str] = []
    llm = _FakeLLM(calls)
    conversation_repo = _TrackedConversationRepository()
    daily_repo = _TrackedDailyCommentRepository()
    wellbeing_repo = _TrackedWellbeingRepository()
    memory_index = _TrackedMemoryIndex(calls)
    service = ChatOrchestratorService(
        qwen_response_service=llm,
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=memory_index,
        wellbeing_repository=wellbeing_repo,
        conversation_repository=conversation_repo,
        daily_comment_repository=daily_repo,
        app_debug=True,
    )

    response = asyncio.run(
        service.run(
            _payload(diary_note="I want to kill myself tonight."),
            latest_user_message="I want to stop and I want to kill myself",
        )
    )

    assert response.decision.response_mode == "crisis"
    assert llm.latest_user_message == "I want to stop and I want to kill myself"
    assert conversation_repo.user_messages == []
    assert daily_repo.comments == []
    assert wellbeing_repo.saved_payloads
    assert wellbeing_repo.saved_payloads[0].signals.diary_note is None
    assert "chunk_upsert" not in calls
    assert "retrieval" not in calls
    debug = response.response_metadata.debug if response.response_metadata else None
    assert debug is not None
    assert debug["raw_text_stored"] is False
    assert debug["vector_indexed"] is False
    assert debug["memory_retrieval_skipped"] is True


def test_debug_payload_has_only_ids_and_metrics() -> None:
    calls: list[str] = []
    service = ChatOrchestratorService(
        qwen_response_service=_FakeLLM(calls),
        recent_context_summary_service=_TrackedSummaryService(calls),
        safety_gate_service=_TrackedSafetyService(calls),
        practice_retriever=_TrackedPracticeRetriever(calls),
        memory_index_service=_TrackedMemoryIndex(calls),
        app_debug=True,
        strict_sensitive_logging=True,
    )
    response = asyncio.run(service.run(_payload(), latest_user_message="Need help with sleep"))
    debug = response.response_metadata.debug if response.response_metadata else None
    assert debug is not None
    assert "context_summary" not in debug
    assert "retrieved_memories" not in debug
    assert "prompt" not in debug


def test_prompt_includes_compact_model_decision_without_raw_history() -> None:
    decision = StructuredDecision(
        support_mode="context_first_support",
        recommended_action="supportive_response",
        response_mode="normal",
        risk_level="safe",
        support_profile="stable_pattern",
        support_need_bucket="high",
        support_confidence=0.86,
        support_abstain=False,
        personalization_level="normal",
        memory_retrieval_quality="good",
        allowed_memory_ids=["mem_1"],
        llm_constraints=["Do not diagnose."],
        relevant_memories=["[2026-05-01][chat] private raw history"],
        verified_safety_resources=["112"],
    )

    prompt = PromptBuilder().build_messages(
        decision=decision,
        latest_user_message="Hello",
        latest_diary_note=None,
        dialogue_state={},
        max_response_chars=700,
        allow_followup_question=True,
    )
    payload = json.loads(prompt.serialized_input)
    model_decision = payload["slot_2b_model_decision"]

    assert model_decision["personalization_level"] == "normal"
    assert model_decision["support_abstain"] is False
    assert model_decision["memory_retrieval_quality"] == "good"
    assert model_decision["allowed_memory_ids"] == ["mem_1"]
    assert model_decision["llm_constraints"] == ["Do not diagnose."]
    assert "private raw history" not in json.dumps(model_decision, ensure_ascii=False)
    assert payload["slot_6_verified_resources"]["verified_safety_resources"] == ["112"]
    assert payload["output_schema"]["response_text"] == "string"
    assert payload["output_schema"]["followup_question"] == "string or null"
    assert "confidence" not in payload["output_schema"]


def test_prompt_includes_crisis_resource_state_and_no_invention_rules() -> None:
    decision = StructuredDecision(
        support_mode="context_first_support",
        recommended_action="supportive_response",
        response_mode="crisis",
        risk_level="crisis",
        safe_mode=True,
        verified_safety_resources=[GENERIC_RESOURCE_GUIDANCE],
        practice_cards=[],
    )

    prompt = PromptBuilder().build_messages(
        decision=decision,
        latest_user_message="I want to kill myself",
        latest_diary_note=None,
        dialogue_state={},
        max_response_chars=700,
        allow_followup_question=False,
    )
    payload = json.loads(prompt.serialized_input)
    resource_slot = payload["slot_6_verified_resources"]
    system_prompt = prompt.messages[0]["content"]

    assert resource_slot["resource_state"] == "localized_unavailable_generic_guidance"
    assert resource_slot["verified_safety_resources"] == [GENERIC_RESOURCE_GUIDANCE]
    assert "Do not invent phone numbers" in system_prompt
    assert "Do not invent organizations" in system_prompt
    assert "Do not invent URLs" in system_prompt
