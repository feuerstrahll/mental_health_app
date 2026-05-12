from __future__ import annotations

import inspect
import json
import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol, Sequence
from uuid import uuid4

from app.llm.response_composer import ComposeMeta, ComposeResult
from app.schemas.decision import (
    AnalysisSnapshot,
    LlmResponseMeta,
    ResponseMetadata,
    StructuredDecision,
    SupportDecisionResponse,
)
from app.schemas.wellbeing import WellbeingSignalsRequest
from app.services.context.memory_index_service import MemoryIndexService, UpsertResult
from app.services.context.practice_retriever import PracticeCard, PracticeRetriever
from app.services.context.recent_context_summary_service import (
    ContextDailyEntry,
    ContextMemory,
    RecentContextSummaryService,
)
from app.services.context.user_memory_chunk_service import UserMemoryChunkService
from app.services.ml.support_model import (
    AssessorDecisionDraft,
    AssessorMeta,
    ContextAssessmentResult,
    ContextAssessorProtocol,
    FallbackContextAssessorService,
    support_need_score_for_mode,
)
from app.services.safety.safety_classifier import (
    SafetyGateResult,
    SafetyGateService,
    SafetyPrecheckResult,
    SafetyResource,
    SafetyResourceService,
)

logger = logging.getLogger(__name__)


class LlmResponseServiceProtocol(Protocol):
    async def compose(
        self,
        decision: StructuredDecision,
        *,
        latest_user_message: str | None = None,
        latest_diary_note: str | None = None,
        dialogue_state: dict[str, Any] | None = None,
    ) -> ComposeResult | str:
        ...


class ChatOrchestratorService:
    STOP_PATTERNS = ("stop", "enough", "don't reply", "do not reply", "leave me", "прекрати", "стоп")

    def __init__(
        self,
        *,
        qwen_response_service: LlmResponseServiceProtocol,
        recent_context_summary_service: RecentContextSummaryService,
        safety_gate_service: SafetyGateService,
        practice_retriever: PracticeRetriever,
        context_assessor_service: ContextAssessorProtocol | None = None,
        user_memory_chunk_service: UserMemoryChunkService | None = None,
        memory_index_service: MemoryIndexService | None = None,
        wellbeing_repository: Any | None = None,
        conversation_repository: Any | None = None,
        daily_comment_repository: Any | None = None,
        app_debug: bool = False,
        strict_sensitive_logging: bool = True,
        recent_entries_limit: int = 14,
        retrieved_memories_limit: int = 6,
        memory_retrieval_enabled: bool = True,
    ) -> None:
        self._qwen_response_service = qwen_response_service
        self._recent_context_summary_service = recent_context_summary_service
        self._safety_gate_service = safety_gate_service
        self._practice_retriever = practice_retriever
        self._context_assessor_service = context_assessor_service or FallbackContextAssessorService()
        self._user_memory_chunk_service = user_memory_chunk_service or UserMemoryChunkService()
        self._memory_index_service = memory_index_service

        self._wellbeing_repository = wellbeing_repository
        self._conversation_repository = conversation_repository
        self._daily_comment_repository = daily_comment_repository

        self._app_debug = app_debug
        self._strict_sensitive_logging = strict_sensitive_logging
        self._recent_entries_limit = recent_entries_limit
        self._retrieved_memories_limit = retrieved_memories_limit
        self._memory_retrieval_enabled = memory_retrieval_enabled

    async def run(
        self,
        payload: WellbeingSignalsRequest,
        *,
        session_id: str | None = None,
        latest_user_message: str | None = None,
        latest_diary_note: str | None = None,
        dialogue_state: dict[str, Any] | None = None,
        client_safety_precheck_result: dict[str, Any] | None = None,
        recent_daily_entries: Sequence[ContextDailyEntry] | Sequence[WellbeingSignalsRequest] | None = None,
    ) -> SupportDecisionResponse:
        started_at = time.perf_counter()
        request_id = self._new_request_id()
        resolved_session_id = session_id or self._new_session_id()
        state = dict(dialogue_state or {})
        current_diary_note = latest_diary_note or payload.signals.diary_note
        current_turn_source_ids: list[str] = []

        stop_requested = self._is_stop_requested(
            latest_user_message=latest_user_message,
            dialogue_state=state,
            client_safety_precheck_result=client_safety_precheck_result,
        )
        safety_precheck = self._safety_gate_service.precheck(
            latest_user_message=latest_user_message,
            latest_diary_note=current_diary_note,
            client_safety_precheck_result=client_safety_precheck_result,
        )

        persisted_user_message_id: str | None = None
        persisted_daily_comment_id: str | None = None
        if (
            latest_user_message
            and safety_precheck.should_persist_message
            and self._conversation_repository is not None
        ):
            try:
                persisted_user_message_id = await self._invoke_repo_method(
                    self._conversation_repository,
                    "save_user_message",
                    session_id=resolved_session_id,
                    user_id=payload.user_id,
                    text_value=latest_user_message,
                    request_id=request_id,
                )
                if persisted_user_message_id:
                    current_turn_source_ids.append(persisted_user_message_id)
            except Exception as exc:
                logger.warning(
                    "memory_current_turn_message_persist_failed request_id=%s user_id=%s error=%s",
                    request_id,
                    payload.user_id,
                    exc.__class__.__name__,
                )

        if (
            latest_user_message
            and safety_precheck.should_persist_message
            and current_diary_note
            and current_diary_note.strip()
            and self._daily_comment_repository is not None
        ):
            try:
                persisted_daily_comment_id = await self._invoke_repo_method(
                    self._daily_comment_repository,
                    "save_comment",
                    user_id=payload.user_id,
                    entry_date=payload.client_timestamp.date() if payload.client_timestamp else date.today(),
                    emotion_marker=payload.signals.emotion_marker,
                    comment_text=current_diary_note.strip(),
                    request_id=request_id,
                )
                if persisted_daily_comment_id:
                    current_turn_source_ids.append(persisted_daily_comment_id)
            except Exception as exc:
                logger.warning(
                    "memory_current_turn_daily_comment_persist_failed request_id=%s user_id=%s error=%s",
                    request_id,
                    payload.user_id,
                    exc.__class__.__name__,
                )

        recent_entries = await self._load_recent_entries(
            user_id=payload.user_id,
            payload=payload,
            recent_daily_entries=recent_daily_entries,
        )
        conversation_memories = await self._load_conversation_memories(
            user_id=payload.user_id,
            session_id=resolved_session_id,
            current_request_id=request_id,
        )
        daily_comment_memories = await self._load_daily_comments(
            user_id=payload.user_id,
            current_request_id=request_id,
        )

        conversation_prompt_context = list(conversation_memories)
        daily_comment_prompt_context = list(daily_comment_memories)
        conversation_indexable_memories = list(conversation_memories)
        daily_comment_indexable_memories = list(daily_comment_memories)

        if latest_user_message and not persisted_user_message_id:
            synthetic_chat_source_id = f"{request_id}:user"
            synthetic_chat_memory = ContextMemory(
                source="chat_message",
                text=latest_user_message,
                entry_date=payload.client_timestamp.date() if payload.client_timestamp else date.today(),
                metadata={
                    "source_type": "current_turn_chat_message",
                    "source_id": synthetic_chat_source_id,
                    "request_id": request_id,
                    "is_current_turn": True,
                    "role": "user",
                },
            )
            if safety_precheck.should_use_current_turn_in_prompt:
                conversation_prompt_context.append(synthetic_chat_memory)
            if safety_precheck.should_embed_raw_text:
                conversation_indexable_memories.append(synthetic_chat_memory)
                current_turn_source_ids.append(synthetic_chat_source_id)

        if current_diary_note and current_diary_note.strip() and not persisted_daily_comment_id:
            synthetic_daily_source_id = f"{request_id}:daily_comment"
            synthetic_daily_memory = ContextMemory(
                source="daily_comment",
                text=current_diary_note.strip(),
                entry_date=payload.client_timestamp.date() if payload.client_timestamp else date.today(),
                metadata={
                    "source_type": "current_turn_daily_comment",
                    "source_id": synthetic_daily_source_id,
                    "request_id": request_id,
                    "is_current_turn": True,
                    "role": "daily_comment",
                    "emotion_marker": payload.signals.emotion_marker,
                },
            )
            if safety_precheck.should_use_current_turn_in_prompt:
                daily_comment_prompt_context.append(synthetic_daily_memory)
            if safety_precheck.should_embed_raw_text:
                daily_comment_indexable_memories.append(synthetic_daily_memory)
                current_turn_source_ids.append(synthetic_daily_source_id)

        if not safety_precheck.should_embed_raw_text:
            conversation_indexable_memories = self._without_current_turn_memories(conversation_indexable_memories)
            daily_comment_indexable_memories = self._without_current_turn_memories(daily_comment_indexable_memories)

        memory_query = self._build_memory_query(
            payload=payload,
            latest_user_message=latest_user_message,
            latest_diary_note=latest_diary_note,
        )
        memory_index = await self._index_and_retrieve_memories(
            user_id=payload.user_id,
            query=memory_query,
            recent_entries=self._indexable_recent_entries(
                recent_entries=recent_entries,
                safety_precheck=safety_precheck,
            ),
            conversation_memories=conversation_indexable_memories,
            daily_comment_memories=daily_comment_indexable_memories,
            request_id=request_id,
            current_turn_source_ids=current_turn_source_ids,
            safety_precheck=safety_precheck,
        )

        context_summary = self._recent_context_summary_service.build_summary(
            entries=recent_entries,
            retrieved_memories=memory_index.retrieved_memories,
            latest_user_message=latest_user_message,
            latest_diary_note=current_diary_note,
        )

        safety = self._safety_gate_service.evaluate(
            latest_user_message=latest_user_message,
            latest_diary_note=current_diary_note,
            stop_requested=stop_requested,
            client_safety_precheck_result=client_safety_precheck_result,
            precheck_result=safety_precheck,
            recent_context_safety_concern=self._recent_context_safety_concern(
                conversation_memories=conversation_prompt_context,
                daily_comment_memories=daily_comment_prompt_context,
            ),
        )

        assessment = await self._context_assessor_service.assess(
            payload=payload,
            latest_user_message=latest_user_message,
            latest_diary_note=current_diary_note,
            dialogue_state=state,
            context_summary=context_summary,
            retrieved_memories=memory_index.retrieved_memories,
            safety=safety,
        )
        support_need_score = support_need_score_for_mode(
            assessment.draft.support_mode,
            support_abstain=assessment.draft.support_abstain,
        )

        practice_cards = self._practice_retriever.retrieve(
            user_text=latest_user_message,
            context_summary=context_summary,
            risk_level=safety.safety_assessment.risk_level.value,
            support_profile=assessment.draft.support_mode,
            support_need_bucket=self._support_need_bucket(support_need_score),
            personalization_level=self._personalization_level(
                risk_level=self._decision_risk_level(safety),
                support_abstain=assessment.draft.support_abstain,
                support_confidence=assessment.draft.support_confidence,
                memory_retrieval_quality=self._memory_retrieval_quality(memory_index.retrieved_memories),
            ),
            max_cards=1 if safety.safe_mode else 2,
        )

        next_state = self._determine_next_dialogue_state(safety=safety, has_new_chat_message=bool(latest_user_message))
        decision, overlay = self._build_contextual_decision(
            safety=safety,
            context_summary=context_summary,
            retrieved_memories=memory_index.retrieved_memories,
            practice_cards=practice_cards,
            assessment=assessment,
            should_continue_dialogue=next_state == "followup_wait",
        )
        if decision.safe_mode:
            next_state = "safe_mode"
        elif decision.risk_level == "closing":
            next_state = "closing"

        generated = await self._compose_response(
            decision=decision,
            latest_user_message=latest_user_message,
            latest_diary_note=current_diary_note,
            dialogue_state=state,
        )
        validated = generated

        persistence_error = await self._persist_interaction(
            request_id=request_id,
            session_id=resolved_session_id,
            payload=payload,
            latest_user_message=latest_user_message,
            persisted_user_message_id=persisted_user_message_id,
            bot_response=validated,
            safety_precheck=safety_precheck,
            next_dialogue_state=next_state,
        )

        pipeline_latency_ms = int((time.perf_counter() - started_at) * 1000)
        response = SupportDecisionResponse(
            decision=decision,
            safety=safety.safety_assessment,
            llm_response=validated.text,
            llm_meta=LlmResponseMeta(
                used_fallback=validated.meta.used_fallback,
                fallback_reason=validated.meta.fallback_reason,
                latency_ms=validated.meta.latency_ms,
                raw_model_response=validated.meta.raw_model_response if self._app_debug else None,
            ),
            analysis=AnalysisSnapshot(
                support_need_score=decision.support_need_score or 0.0,
                support_profile=decision.support_profile or decision.support_mode,
                emotional_trend=decision.emotional_trend or "unknown",
                confidence=self._confidence_label(decision.support_confidence or 0.0),
                contributing_factors=list(decision.contributing_factors),
                note_signals=list(decision.note_signals),
                risk_flags=list(safety.risk_flags),
            ),
            dialogue_state=next_state,
            safe_mode=bool(decision.safe_mode),
            should_continue_dialogue=bool(decision.should_continue_dialogue),
            practice_card_id=practice_cards[0].card_id if practice_cards else None,
            recommended_action=practice_cards[0].card_id if practice_cards else "supportive_response",
            recommended_action_deprecated=True,
            response_metadata=ResponseMetadata(
                request_id=request_id,
                session_id=resolved_session_id,
                next_dialogue_state=next_state,
                fallback_used=validated.meta.used_fallback,
                llm_latency_ms=validated.meta.latency_ms,
                persistence_error=persistence_error,
                pipeline_latency_ms=pipeline_latency_ms,
                used_memory_index_fallback=memory_index.used_memory_index_fallback,
                debug=self._build_debug_payload(
                    memory_index=memory_index,
                    practice_cards=practice_cards,
                    safety=safety,
                    safety_precheck=safety_precheck,
                    assessor_meta=assessment.meta,
                    assessor_draft=assessment.draft,
                    overlay=overlay,
                    raw_text_stored=bool(persisted_user_message_id or persisted_daily_comment_id),
                )
                if self._app_debug
                else None,
            ),
        )

        self._log_orchestration(
            request_id=request_id,
            session_id=resolved_session_id,
            safety=safety,
            memory_index=memory_index,
            practice_cards=practice_cards,
            validated_result=validated,
            assessor_meta=assessment.meta,
            overlay=overlay,
            next_dialogue_state=next_state,
            pipeline_latency_ms=pipeline_latency_ms,
        )
        return response

    async def _index_and_retrieve_memories(
        self,
        *,
        user_id: str,
        query: str,
        recent_entries: Sequence[ContextDailyEntry],
        conversation_memories: Sequence[ContextMemory],
        daily_comment_memories: Sequence[ContextMemory],
        request_id: str,
        current_turn_source_ids: Sequence[str],
        safety_precheck: SafetyPrecheckResult,
    ) -> "_MemoryIndexSummary":
        if not safety_precheck.should_retrieve_memory:
            return _MemoryIndexSummary(
                retrieved_memories=[],
                chunk_count=0,
                indexed_count=0,
                upserted_count=0,
                reembedded_count=0,
                skipped_count=0,
                provider="skipped",
                retrieved_count=0,
                retrieval_latency_ms=0,
                used_memory_index_fallback=False,
                chunk_ids=[],
                current_turn_vector_indexed=False,
                memory_retrieval_skipped=True,
            )

        chunks = self._user_memory_chunk_service.build_chunks(
            user_id=user_id,
            daily_entries=recent_entries,
            chat_memories=conversation_memories,
            daily_comments=daily_comment_memories,
        )
        deduped_chunks = self._dedupe_request_chunks(user_id=user_id, chunks=chunks)
        if not self._memory_retrieval_enabled:
            fallback_memories = self._chronological_memory_fallback(
                recent_entries=recent_entries,
                conversation_memories=conversation_memories,
                daily_comment_memories=daily_comment_memories,
            )
            return _MemoryIndexSummary(
                retrieved_memories=fallback_memories,
                chunk_count=len(deduped_chunks),
                indexed_count=0,
                upserted_count=0,
                reembedded_count=0,
                skipped_count=len(deduped_chunks),
                provider="retrieval_disabled",
                retrieved_count=len(fallback_memories),
                retrieval_latency_ms=0,
                used_memory_index_fallback=True,
                chunk_ids=[chunk.id for chunk in deduped_chunks],
                current_turn_vector_indexed=False,
                memory_retrieval_skipped=True,
            )
        current_turn_vector_indexed = bool(
            safety_precheck.should_embed_raw_text
            and any(chunk.is_current_turn for chunk in deduped_chunks)
        )
        if self._memory_index_service is None:
            return _MemoryIndexSummary(
                retrieved_memories=[],
                chunk_count=len(deduped_chunks),
                indexed_count=0,
                upserted_count=0,
                reembedded_count=0,
                skipped_count=0,
                provider="disabled",
                retrieved_count=0,
                retrieval_latency_ms=0,
                used_memory_index_fallback=True,
                chunk_ids=[chunk.id for chunk in deduped_chunks],
                current_turn_vector_indexed=False,
                memory_retrieval_skipped=False,
            )
        used_memory_index_fallback = False
        upsert_result = UpsertResult(
            indexed_count=0,
            upserted_count=0,
            reembedded_count=0,
            skipped_count=0,
            used_embedding_provider="unknown",
        )
        try:
            upsert_result = await self._memory_index_service.upsert_chunks(
                user_id=user_id,
                chunks=deduped_chunks,
            )
        except Exception as exc:
            used_memory_index_fallback = True
            logger.warning(
                "memory_upsert_failed request_id=%s user_id=%s error=%s",
                request_id,
                user_id,
                exc.__class__.__name__,
            )

        retrieval_started = time.perf_counter()
        try:
            retrieved_rows = await self._memory_index_service.retrieve_relevant(
                user_id=user_id,
                query_text=query,
                days_back=self._recent_entries_limit,
                top_k=self._retrieved_memories_limit,
                include_current_turn=False,
                exclude_source_ids=current_turn_source_ids,
            )
            retrieval_latency_ms = int((time.perf_counter() - retrieval_started) * 1000)
            retrieved = [
                ContextMemory(
                    source=row.source_type,
                    text=row.text,
                    entry_date=self._parse_date(row.date),
                    score=row.score,
                    metadata={
                        **dict(row.metadata),
                        "memory_chunk_id": row.memory_chunk_id,
                        "source_id": row.source_id,
                        "retrieval_score": row.score,
                        "retrieval_score_direction": "higher_is_better",
                        "retrieval_source": "vector",
                    },
                )
                for row in retrieved_rows
            ]
            retrieved = retrieved[: self._retrieved_memories_limit]
            return _MemoryIndexSummary(
                retrieved_memories=retrieved,
                chunk_count=len(deduped_chunks),
                indexed_count=upsert_result.indexed_count,
                upserted_count=upsert_result.upserted_count,
                reembedded_count=upsert_result.reembedded_count,
                skipped_count=upsert_result.skipped_count,
                provider=upsert_result.used_embedding_provider,
                retrieved_count=len(retrieved),
                retrieval_latency_ms=retrieval_latency_ms,
                used_memory_index_fallback=used_memory_index_fallback,
                chunk_ids=[chunk.id for chunk in deduped_chunks],
                current_turn_vector_indexed=current_turn_vector_indexed,
                memory_retrieval_skipped=False,
            )
        except Exception as exc:
            used_memory_index_fallback = True
            logger.warning(
                "memory_retrieval_failed request_id=%s user_id=%s error=%s",
                request_id,
                user_id,
                exc.__class__.__name__,
            )
            retrieval_latency_ms = int((time.perf_counter() - retrieval_started) * 1000)
            fallback_memories = self._chronological_memory_fallback(
                recent_entries=recent_entries,
                conversation_memories=conversation_memories,
                daily_comment_memories=daily_comment_memories,
            )
            return _MemoryIndexSummary(
                retrieved_memories=fallback_memories,
                chunk_count=len(deduped_chunks),
                indexed_count=upsert_result.indexed_count,
                upserted_count=upsert_result.upserted_count,
                reembedded_count=upsert_result.reembedded_count,
                skipped_count=upsert_result.skipped_count,
                provider=upsert_result.used_embedding_provider,
                retrieved_count=len(fallback_memories),
                retrieval_latency_ms=retrieval_latency_ms,
                used_memory_index_fallback=used_memory_index_fallback,
                chunk_ids=[chunk.id for chunk in deduped_chunks],
                current_turn_vector_indexed=current_turn_vector_indexed,
                memory_retrieval_skipped=False,
            )

    async def _compose_response(
        self,
        *,
        decision: StructuredDecision,
        latest_user_message: str | None,
        latest_diary_note: str | None,
        dialogue_state: dict[str, Any],
    ) -> ComposeResult:
        started = time.perf_counter()
        try:
            result = await self._qwen_response_service.compose(
                decision,
                latest_user_message=latest_user_message,
                latest_diary_note=latest_diary_note,
                dialogue_state=dialogue_state,
            )
            latency_ms = int((time.perf_counter() - started) * 1000)
            if isinstance(result, ComposeResult):
                return ComposeResult(
                    text=result.text,
                    meta=ComposeMeta(
                        used_fallback=result.meta.used_fallback,
                        fallback_reason=result.meta.fallback_reason,
                        latency_ms=result.meta.latency_ms or latency_ms,
                        raw_model_response=result.meta.raw_model_response,
                    ),
                )
            return ComposeResult(
                text=str(result),
                meta=ComposeMeta(
                    used_fallback=False,
                    fallback_reason=None,
                    latency_ms=latency_ms,
                    raw_model_response=str(result),
                ),
            )
        except Exception as exc:
            logger.exception("llm_compose_failed")
            return ComposeResult(
                text=self._fallback_generation_text(decision),
                meta=ComposeMeta(
                    used_fallback=True,
                    fallback_reason=f"llm_error:{exc.__class__.__name__}",
                    latency_ms=0,
                    raw_model_response=None,
                ),
            )

    def _fallback_generation_text(self, decision: StructuredDecision) -> str:
        if (decision.response_mode or "").lower() == "crisis":
            resource_text = " ".join(decision.verified_safety_resources or []).strip()
            guidance = resource_text or SafetyResourceService.GENERIC_UNAVAILABLE_GUIDANCE
            return f"I am really sorry this is so heavy right now. {guidance}."
        if (decision.response_mode or "").lower() == "closing":
            return "Understood. I will stop here."
        return "I am with you. Let's keep this simple and take one small step."

    def _build_contextual_decision(
        self,
        *,
        safety: SafetyGateResult,
        context_summary: str,
        retrieved_memories: Sequence[ContextMemory],
        practice_cards: Sequence[PracticeCard],
        assessment: ContextAssessmentResult,
        should_continue_dialogue: bool,
    ) -> tuple[StructuredDecision, "_AssessorOverlaySummary"]:
        draft = assessment.draft
        deterministic_risk_level = self._decision_risk_level(safety)
        risk_level, response_mode, safety_override, closing_override = self._overlay_risk(
            safety=safety,
            raw_risk_hint=draft.raw_risk_hint,
        )
        support_mode = "safe_support" if risk_level == "crisis" else draft.support_mode
        if risk_level == "closing":
            support_mode = "close_conversation"
        recommended_action = draft.recommended_action
        memory_retrieval_quality = self._memory_retrieval_quality(retrieved_memories)
        support_need_score = support_need_score_for_mode(
            support_mode,
            support_abstain=draft.support_abstain,
        )
        support_need_bucket = self._support_need_bucket(support_need_score)
        safe_mode = risk_level in {"safe_support", "crisis"}
        followup_mode = "no_followup" if safe_mode or risk_level == "closing" else draft.followup_mode
        personalization_level = self._personalization_level(
            risk_level=risk_level,
            support_abstain=draft.support_abstain,
            support_confidence=draft.support_confidence,
            memory_retrieval_quality=memory_retrieval_quality,
        )
        llm_constraints = self._llm_constraints(
            support_abstain=draft.support_abstain,
            memory_retrieval_quality=memory_retrieval_quality,
        )
        llm_constraints = self._dedupe_strings([*draft.llm_constraints, *llm_constraints])
        allowed_memory_ids = list(draft.allowed_memory_ids)
        relevant_memories = self._selected_memories_for_decision(
            memories=retrieved_memories,
            allowed_memory_ids=allowed_memory_ids,
        )
        risk_flags = self._dedupe_strings([*safety.risk_flags, *draft.risk_flags])
        context_text = draft.context_summary or context_summary
        continue_dialogue = bool(should_continue_dialogue and followup_mode != "no_followup" and not safe_mode)
        decision = StructuredDecision(
            support_mode=support_mode,
            assessor_action=recommended_action,
            reasoning_tags=list(draft.contributing_factors),
            support_need_score=support_need_score,
            support_need_bucket=support_need_bucket,
            support_profile=support_mode,
            support_confidence=draft.support_confidence,
            support_abstain=draft.support_abstain,
            support_factors=list(draft.support_factors),
            emotional_trend="unknown",
            contributing_factors=list(draft.contributing_factors),
            note_signals=list(draft.note_signals),
            risk_flags=risk_flags,
            interaction_flags=list(draft.interaction_flags),
            response_mode=response_mode,
            risk_level=risk_level,
            followup_mode=followup_mode,
            safe_mode=safe_mode,
            should_continue_dialogue=continue_dialogue,
            context_summary=context_text,
            relevant_memories=[self._memory_for_decision(row) for row in relevant_memories],
            memory_retrieval_quality=memory_retrieval_quality,
            allowed_memory_ids=allowed_memory_ids,
            practice_cards=[card.as_compact_text() for card in practice_cards],
            safety_instructions=list(safety.safety_instructions),
            verified_safety_resources=self._serialized_safety_resources(safety.verified_resources),
            llm_constraints=llm_constraints,
            personalization_level=personalization_level,
            memory_retrieval_used=bool(retrieved_memories),
        )
        overlay = _AssessorOverlaySummary(
            assessor_raw_risk_hint=draft.raw_risk_hint,
            deterministic_safety_level=deterministic_risk_level,
            final_risk_level=risk_level,
            safety_override_applied=safety_override,
            closing_override_applied=closing_override,
        )
        return decision, overlay

    def _overlay_risk(
        self,
        *,
        safety: SafetyGateResult,
        raw_risk_hint: str,
    ) -> tuple[str, str, bool, bool]:
        if safety.mode == "crisis":
            return "crisis", "crisis", True, False
        if safety.safe_mode or raw_risk_hint in {"supportive", "elevated", "crisis"}:
            return "safe_support", "supportive_caution", raw_risk_hint == "crisis", False
        if safety.close_conversation:
            return "closing", "closing", False, True
        return "safe", "normal", False, False

    def _decision_risk_level(self, safety: SafetyGateResult) -> str:
        if safety.mode == "crisis":
            return "crisis"
        if safety.safe_mode:
            return "safe_support"
        if safety.close_conversation:
            return "closing"
        return "safe"

    def _support_need_bucket(self, score: float | None) -> str | None:
        if score is None:
            return None
        if score < 0.34:
            return "low"
        if score < 0.67:
            return "medium"
        return "high"

    def _personalization_level(
        self,
        *,
        risk_level: str,
        support_abstain: bool,
        support_confidence: float | None,
        memory_retrieval_quality: str,
    ) -> str:
        if risk_level in {"crisis", "closing", "safe_support"} or support_abstain:
            return "none"
        if support_confidence is None or support_confidence < 0.75:
            return "light"
        if memory_retrieval_quality != "good":
            return "light"
        return "normal"

    def _memory_retrieval_quality(self, memories: Sequence[ContextMemory]) -> str:
        if not memories:
            return "none"
        vector_scores: list[float] = []
        has_vector_result = False
        for memory in memories:
            if memory.metadata.get("retrieval_source") != "vector":
                continue
            has_vector_result = True
            if bool(memory.metadata.get("is_current_turn", False)):
                continue
            if memory.metadata.get("retrieval_score_direction") != "higher_is_better":
                continue
            score = memory.metadata.get("retrieval_score")
            if score is None:
                continue
            try:
                vector_scores.append(float(score))
            except (TypeError, ValueError):
                continue
        if not has_vector_result:
            return "weak"
        if not vector_scores:
            return "weak"
        return "good" if max(vector_scores) >= 0.55 else "weak"

    def _allowed_memory_ids(self, memories: Sequence[ContextMemory]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for memory in memories:
            raw_id = memory.metadata.get("memory_chunk_id") or memory.metadata.get("source_id")
            memory_id = str(raw_id or "").strip()
            if not memory_id or memory_id in seen:
                continue
            seen.add(memory_id)
            out.append(memory_id)
        return out

    def _serialized_safety_resources(self, resources: Sequence[SafetyResource]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for resource in resources:
            text = resource.as_prompt_text().strip()
            if not text or text in seen:
                continue
            seen.add(text)
            out.append(text)
        return out

    def _llm_constraints(
        self,
        *,
        support_abstain: bool,
        memory_retrieval_quality: str,
    ) -> list[str]:
        constraints: list[str] = []
        if support_abstain:
            constraints.extend(
                [
                    "Do not infer stable user patterns from limited data.",
                    "Use generic supportive language.",
                    "Ask at most one gentle clarifying question.",
                    'Do not say "based on your history" or similar.',
                ]
            )
        if memory_retrieval_quality in {"weak", "none"}:
            constraints.extend(
                [
                    'Do not say "based on your history".',
                    "Do not claim recurring patterns.",
                    'Do not say "you usually" or "this keeps happening".',
                    "Use only current-turn wording for personalization.",
                ]
            )
        out: list[str] = []
        seen: set[str] = set()
        for item in constraints:
            if item in seen:
                continue
            seen.add(item)
            out.append(item)
        return out

    def _dedupe_strings(self, values: Sequence[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            out.append(text)
        return out

    def _selected_memories_for_decision(
        self,
        *,
        memories: Sequence[ContextMemory],
        allowed_memory_ids: Sequence[str],
    ) -> list[ContextMemory]:
        if not allowed_memory_ids:
            return []
        allowed = {str(value) for value in allowed_memory_ids}
        selected: list[ContextMemory] = []
        for memory in memories:
            raw_id = memory.metadata.get("memory_chunk_id") or memory.metadata.get("source_id")
            if str(raw_id or "") in allowed:
                selected.append(memory)
        return selected

    def _confidence_label(self, confidence: float) -> str:
        if confidence < 0.45:
            return "low"
        if confidence < 0.75:
            return "medium"
        return "high"

    def _memory_for_decision(self, memory: ContextMemory) -> str:
        date_part = memory.entry_date.isoformat() if memory.entry_date else "unknown-date"
        source = (memory.source or "memory").strip()
        text = (memory.text or "").strip()
        return f"[{date_part}][{source}] {text[:260]}"

    def _determine_next_dialogue_state(self, *, safety: SafetyGateResult, has_new_chat_message: bool) -> str:
        if safety.mode in {"crisis", "supportive_caution"}:
            return "safe_mode"
        if safety.close_conversation:
            return "closing"
        if has_new_chat_message:
            return "followup_wait"
        return "analysis_reply"

    async def _persist_interaction(
        self,
        *,
        request_id: str,
        session_id: str,
        payload: WellbeingSignalsRequest,
        latest_user_message: str | None,
        persisted_user_message_id: str | None,
        bot_response: ComposeResult,
        safety_precheck: SafetyPrecheckResult,
        next_dialogue_state: str,
    ) -> str | None:
        errors: list[str] = []
        try:
            if self._wellbeing_repository is not None and safety_precheck.should_persist_structured_signals:
                await self._invoke_repo_method(
                    self._wellbeing_repository,
                    "save",
                    payload=self._payload_for_structured_persistence(
                        payload=payload,
                        safety_precheck=safety_precheck,
                    ),
                )
        except Exception as exc:
            logger.exception("persist_wellbeing_failed")
            errors.append(f"wellbeing:{exc.__class__.__name__}")

        try:
            await self._invoke_repo_method(
                self._conversation_repository,
                "upsert_session",
                session_id=session_id,
                user_id=payload.user_id,
                state=next_dialogue_state,
            )
            if latest_user_message and not persisted_user_message_id and safety_precheck.should_persist_message:
                await self._invoke_repo_method(
                    self._conversation_repository,
                    "save_user_message",
                    session_id=session_id,
                    user_id=payload.user_id,
                    text_value=latest_user_message,
                    request_id=request_id,
                )
            await self._invoke_repo_method(
                self._conversation_repository,
                "save_bot_message",
                session_id=session_id,
                user_id=payload.user_id,
                text_value=bot_response.text,
                request_id=request_id,
                fallback_used=bot_response.meta.used_fallback,
            )
            await self._invoke_repo_method(
                self._conversation_repository,
                "mark_messages_not_current_turn",
                user_id=payload.user_id,
                request_id=request_id,
            )
        except Exception as exc:
            logger.exception("persist_conversation_failed")
            errors.append(f"conversation:{exc.__class__.__name__}")

        return ";".join(errors) if errors else None

    def _is_stop_requested(
        self,
        *,
        latest_user_message: str | None,
        dialogue_state: dict[str, Any] | None,
        client_safety_precheck_result: dict[str, Any] | None,
    ) -> bool:
        if bool((dialogue_state or {}).get("stop_requested", False)):
            return True
        flags = {str(flag).strip().lower() for flag in (client_safety_precheck_result or {}).get("flags", [])}
        if {"stop_intent", "boundary_request"}.intersection(flags):
            return True
        if not latest_user_message:
            return False
        text = latest_user_message.strip().lower()
        return any(pattern in text for pattern in self.STOP_PATTERNS)

    def _without_current_turn_memories(self, memories: Sequence[ContextMemory]) -> list[ContextMemory]:
        return [
            memory
            for memory in memories
            if not bool((memory.metadata or {}).get("is_current_turn", False))
        ]

    def _indexable_recent_entries(
        self,
        *,
        recent_entries: Sequence[ContextDailyEntry],
        safety_precheck: SafetyPrecheckResult,
    ) -> list[ContextDailyEntry]:
        entries = list(recent_entries)
        if safety_precheck.should_embed_raw_text or not entries:
            return entries
        # _load_recent_entries appends the current payload entry; elevated turns
        # may still use it for the current prompt, but not for vector chunks.
        return entries[:-1]

    def _payload_for_structured_persistence(
        self,
        *,
        payload: WellbeingSignalsRequest,
        safety_precheck: SafetyPrecheckResult,
    ) -> WellbeingSignalsRequest:
        if safety_precheck.should_persist_message:
            return payload
        signals = payload.signals.model_copy(update={"diary_note": None})
        return payload.model_copy(update={"signals": signals})

    async def _load_recent_entries(
        self,
        *,
        user_id: str,
        payload: WellbeingSignalsRequest,
        recent_daily_entries: Sequence[ContextDailyEntry] | Sequence[WellbeingSignalsRequest] | None,
    ) -> list[ContextDailyEntry]:
        entries: list[ContextDailyEntry] = []
        if recent_daily_entries:
            entries.extend(self._normalize_daily_entries(recent_daily_entries))
        elif self._wellbeing_repository is not None:
            try:
                history = await self._invoke_repo_method(
                    self._wellbeing_repository,
                    "get_recent_by_user",
                    user_id=user_id,
                    limit=self._recent_entries_limit,
                )
                entries.extend(self._normalize_daily_entries(history or []))
            except Exception:
                logger.exception("load_recent_entries_failed")
        entries.append(self._entry_from_payload(payload))
        entries = sorted(entries, key=lambda item: item.entry_date)
        return entries[-self._recent_entries_limit :]

    async def _load_conversation_memories(
        self,
        *,
        user_id: str,
        session_id: str,
        current_request_id: str,
    ) -> list[ContextMemory]:
        if self._conversation_repository is None:
            return []
        try:
            messages = await self._invoke_repo_method(
                self._conversation_repository,
                "get_recent_messages",
                user_id=user_id,
                session_id=session_id,
                limit=12,
            )
        except Exception:
            logger.exception("load_conversation_history_failed")
            return []
        out: list[ContextMemory] = []
        for item in messages or []:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            role = str(item.get("role") or "user").strip() or "user"
            metadata = dict(item.get("metadata") or {})
            message_request_id = str(metadata.get("request_id") or "")
            fallback_source_id = message_request_id or f"legacy:{role}:{str(item.get('created_at') or item.get('date') or '')}"
            out.append(
                ContextMemory(
                    source="chat_message",
                    text=text,
                    entry_date=self._parse_date(item.get("created_at") or item.get("timestamp") or item.get("date")),
                    metadata={
                        "session_id": session_id,
                        "role": role,
                        "source_type": "chat_message",
                        "source_id": str(item.get("id") or fallback_source_id),
                        "request_id": message_request_id,
                        "is_current_turn": message_request_id == current_request_id,
                    },
                )
            )
        return out

    async def _load_daily_comments(self, *, user_id: str, current_request_id: str) -> list[ContextMemory]:
        if self._daily_comment_repository is None:
            return []
        try:
            rows = await self._invoke_repo_method(
                self._daily_comment_repository,
                "get_recent_comments",
                user_id=user_id,
                limit=self._recent_entries_limit,
            )
        except Exception:
            logger.exception("load_daily_comments_failed")
            return []
        out: list[ContextMemory] = []
        for row in rows or []:
            text = str(row.get("comment_text") or "").strip()
            if not text:
                continue
            metadata = dict(row.get("metadata") or {})
            request_id = str(metadata.get("request_id") or "")
            fallback_source_id = request_id or f"legacy:daily_comment:{str(row.get('created_at') or row.get('entry_date') or '')}"
            out.append(
                ContextMemory(
                    source="daily_comment",
                    text=text,
                    entry_date=self._parse_date(row.get("entry_date") or row.get("created_at")),
                    metadata={
                        "source_type": "daily_comment",
                        "source_id": str(row.get("id") or fallback_source_id),
                        "request_id": request_id,
                        "is_current_turn": request_id == current_request_id,
                        "emotion_marker": row.get("emotion_marker"),
                        "role": "daily_comment",
                    },
                )
            )
        return out

    def _normalize_daily_entries(self, values: Sequence[Any]) -> list[ContextDailyEntry]:
        out: list[ContextDailyEntry] = []
        for item in values:
            if isinstance(item, ContextDailyEntry):
                out.append(item)
                continue
            if isinstance(item, WellbeingSignalsRequest):
                out.append(self._entry_from_payload(item))
                continue
            if isinstance(item, dict):
                entry_date = self._parse_date(item.get("entry_date") or item.get("date"))
                if entry_date is None:
                    continue
                out.append(
                    # Preserve source row identity for deterministic chunk source_id.
                    ContextDailyEntry(
                        entry_date=entry_date,
                        emotion_marker=item.get("emotion_marker"),
                        diary_note=item.get("diary_note"),
                        sleep_duration_hours=item.get("sleep_duration_hours"),
                        sleep_quality=str(item.get("sleep_quality")) if item.get("sleep_quality") is not None else None,
                        sleep_regularity=str(item.get("sleep_regularity"))
                        if item.get("sleep_regularity") is not None
                        else None,
                        physical_activity_minutes=item.get("physical_activity_minutes"),
                        sedentary_time_minutes=item.get("sedentary_minutes") or item.get("sedentary_time_minutes"),
                        outdoor_time_minutes=item.get("outdoor_minutes") or item.get("outdoor_time_minutes"),
                        social_connectedness_score=item.get("social_connectedness_score"),
                        routine_regularity=str(item.get("routine_regularity"))
                        if item.get("routine_regularity") is not None
                        else None,
                        metadata={
                            **dict(item.get("metadata") or {}),
                            "source_id": str(item.get("id") or item.get("source_id") or ""),
                        },
                    )
                )
        return out

    def _entry_from_payload(self, payload: WellbeingSignalsRequest) -> ContextDailyEntry:
        signals = payload.signals
        entry_date = payload.client_timestamp.date() if payload.client_timestamp else date.today()
        return ContextDailyEntry(
            entry_date=entry_date,
            emotion_marker=signals.emotion_marker,
            diary_note=signals.diary_note,
            sleep_duration_hours=signals.sleep_duration_hours,
            sleep_quality=str(signals.sleep_quality) if signals.sleep_quality is not None else None,
            sleep_regularity=str(signals.sleep_regularity) if signals.sleep_regularity is not None else None,
            physical_activity_minutes=float(signals.physical_activity_minutes)
            if signals.physical_activity_minutes is not None
            else None,
            sedentary_time_minutes=float(signals.sedentary_minutes) if signals.sedentary_minutes is not None else None,
            outdoor_time_minutes=float(signals.outdoor_minutes) if signals.outdoor_minutes is not None else None,
            social_connectedness_score=float(signals.social_connectedness)
            if signals.social_connectedness is not None
            else None,
            routine_regularity=str(signals.routine_regularity) if signals.routine_regularity is not None else None,
            metadata={"source_id": f"wellbeing:{entry_date.isoformat()}"},
        )

    def _chronological_memory_fallback(
        self,
        *,
        recent_entries: Sequence[ContextDailyEntry],
        conversation_memories: Sequence[ContextMemory],
        daily_comment_memories: Sequence[ContextMemory],
    ) -> list[ContextMemory]:
        merged: list[ContextMemory] = [*conversation_memories, *daily_comment_memories]
        merged = [
            row
            for row in merged
            if (row.text or "").strip()
            and not bool((row.metadata or {}).get("is_current_turn", False))
        ]
        merged.sort(key=lambda row: row.entry_date or date.min, reverse=True)
        if merged:
            return [self._fallback_memory(row) for row in merged[:3]]
        return self._fallback_recent_memories_from_entries(recent_entries)

    def _fallback_recent_memories_from_entries(self, entries: Sequence[ContextDailyEntry]) -> list[ContextMemory]:
        memories: list[ContextMemory] = []
        for entry in entries[-3:]:
            parts = [
                f"Date: {entry.entry_date.isoformat()}",
                f"Emotion: {entry.emotion_marker}" if entry.emotion_marker else "",
                f"Sleep: {entry.sleep_duration_hours:g}h" if entry.sleep_duration_hours is not None else "",
                f"Social: {entry.social_connectedness_score:g}/5" if entry.social_connectedness_score is not None else "",
                f"Diary: {entry.diary_note}" if entry.diary_note else "",
            ]
            text = "; ".join(part for part in parts if part)
            if text:
                memories.append(
                    ContextMemory(
                        source="wellbeing_record",
                        text=self._compact_fallback_text(text),
                        entry_date=entry.entry_date,
                        metadata={
                            "source_id": entry.metadata.get("source_id", ""),
                            "retrieval_source": "chronological_fallback",
                        },
                    )
                )
        return memories

    def _fallback_memory(self, memory: ContextMemory) -> ContextMemory:
        return ContextMemory(
            source=memory.source,
            text=self._compact_fallback_text(memory.text),
            entry_date=memory.entry_date,
            metadata={
                **dict(memory.metadata or {}),
                "retrieval_source": "chronological_fallback",
            },
        )

    def _compact_fallback_text(self, value: str | None) -> str:
        return " ".join((value or "").strip().split())[:320]

    def _recent_context_safety_concern(
        self,
        *,
        conversation_memories: Sequence[ContextMemory],
        daily_comment_memories: Sequence[ContextMemory],
    ) -> bool:
        memories = [
            memory
            for memory in [*conversation_memories, *daily_comment_memories]
            if not bool((memory.metadata or {}).get("is_current_turn", False))
        ]
        memories.sort(key=lambda row: row.entry_date or date.min, reverse=True)
        return self._safety_gate_service.has_recent_context_safety_concern(
            [memory.text for memory in memories[:3]]
        )

    def _dedupe_request_chunks(self, *, user_id: str, chunks: Sequence[MemoryChunk]) -> list[MemoryChunk]:
        out: list[MemoryChunk] = []
        seen: set[tuple[str, str, str]] = set()
        for chunk in chunks:
            normalized_text = self._normalize_text_for_dedupe(chunk.text)
            role = str(chunk.metadata.get("role") or "")
            dedupe_key = (user_id, normalized_text, role)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            out.append(chunk)
        return out

    def _normalize_text_for_dedupe(self, value: str | None) -> str:
        if not value:
            return ""
        return " ".join(value.strip().lower().split())

    def _build_memory_query(
        self,
        *,
        payload: WellbeingSignalsRequest,
        latest_user_message: str | None,
        latest_diary_note: str | None,
    ) -> str:
        signals = payload.signals
        return " ".join(
            part
            for part in [latest_user_message, latest_diary_note, signals.diary_note, signals.emotion_marker]
            if part
        ).strip()

    def _build_debug_payload(
        self,
        *,
        memory_index: "_MemoryIndexSummary",
        practice_cards: Sequence[PracticeCard],
        safety: SafetyGateResult,
        safety_precheck: SafetyPrecheckResult,
        assessor_meta: AssessorMeta,
        assessor_draft: AssessorDecisionDraft,
        overlay: "_AssessorOverlaySummary",
        raw_text_stored: bool,
    ) -> dict[str, Any]:
        return {
            "pipeline": "context_first",
            "safety_mode": safety.mode,
            "risk_level": safety.safety_assessment.risk_level.value,
            "precheck_risk_level": safety_precheck.risk_level,
            "retention_policy": safety_precheck.retention_policy,
            "risk_flags": list(safety.risk_flags),
            "raw_text_stored": raw_text_stored,
            "vector_indexed": memory_index.current_turn_vector_indexed,
            "memory_retrieval_skipped": memory_index.memory_retrieval_skipped,
            "chunk_count": memory_index.chunk_count,
            "memories_count": len(memory_index.retrieved_memories),
            "memory_chunk_ids": list(memory_index.chunk_ids),
            "practice_cards_count": len(practice_cards),
            "practice_ids": [card.card_id for card in practice_cards],
            "embedding_provider": memory_index.provider,
            "indexed_count": memory_index.indexed_count,
            "upserted_count": memory_index.upserted_count,
            "reembedded_count": memory_index.reembedded_count,
            "skipped_count": memory_index.skipped_count,
            "retrieved_count": memory_index.retrieved_count,
            "retrieval_latency_ms": memory_index.retrieval_latency_ms,
            "used_memory_index_fallback": memory_index.used_memory_index_fallback,
            "assessor_prompt_version": assessor_meta.prompt_version,
            "assessor_used_fallback": assessor_meta.used_fallback,
            "assessor_fallback_reason": assessor_meta.fallback_reason,
            "assessor_raw_risk_hint": assessor_draft.raw_risk_hint,
            "deterministic_safety_level": overlay.deterministic_safety_level,
            "final_risk_level": overlay.final_risk_level,
            "safety_override_applied": overlay.safety_override_applied,
            "closing_override_applied": overlay.closing_override_applied,
            "allowed_memory_ids": list(assessor_draft.allowed_memory_ids),
        }

    def _log_orchestration(
        self,
        *,
        request_id: str,
        session_id: str,
        safety: SafetyGateResult,
        memory_index: "_MemoryIndexSummary",
        practice_cards: Sequence[PracticeCard],
        validated_result: ComposeResult,
        assessor_meta: AssessorMeta,
        overlay: "_AssessorOverlaySummary",
        next_dialogue_state: str,
        pipeline_latency_ms: int,
    ) -> None:
        payload = {
            "request_id": request_id,
            "session_id": session_id,
            "pipeline": "context_first",
            "safety_mode": safety.mode,
            "risk_level": safety.safety_assessment.risk_level.value,
            "risk_flags": list(safety.risk_flags),
            "safe_mode": bool(safety.safe_mode),
            "chunk_count": memory_index.chunk_count,
            "memories_count": len(memory_index.retrieved_memories),
            "practice_cards_count": len(practice_cards),
            "practice_ids": [card.card_id for card in practice_cards],
            "memory_chunk_ids": list(memory_index.chunk_ids),
            "embedding_provider": memory_index.provider,
            "indexed_count": memory_index.indexed_count,
            "upserted_count": memory_index.upserted_count,
            "reembedded_count": memory_index.reembedded_count,
            "skipped_count": memory_index.skipped_count,
            "retrieved_count": memory_index.retrieved_count,
            "retrieval_latency_ms": memory_index.retrieval_latency_ms,
            "used_memory_index_fallback": memory_index.used_memory_index_fallback,
            "fallback_used": validated_result.meta.used_fallback,
            "fallback_reason": validated_result.meta.fallback_reason,
            "llm_latency_ms": validated_result.meta.latency_ms,
            "assessor_prompt_version": assessor_meta.prompt_version,
            "assessor_used_fallback": assessor_meta.used_fallback,
            "assessor_fallback_reason": assessor_meta.fallback_reason,
            "assessor_latency_ms": assessor_meta.latency_ms,
            "assessor_raw_risk_hint": overlay.assessor_raw_risk_hint,
            "final_risk_level": overlay.final_risk_level,
            "safety_override_applied": overlay.safety_override_applied,
            "closing_override_applied": overlay.closing_override_applied,
            "next_dialogue_state": next_dialogue_state,
            "pipeline_latency_ms": pipeline_latency_ms,
        }
        logger.info("chat_orchestration %s", json.dumps(payload, ensure_ascii=False, sort_keys=True))

    async def _invoke_repo_method(self, repo: Any, method_name: str, **kwargs: Any) -> Any:
        if repo is None:
            return None
        method = getattr(repo, method_name, None)
        if method is None:
            return None
        result = method(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    def _parse_date(self, value: Any) -> date | None:
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
            except ValueError:
                try:
                    return date.fromisoformat(value)
                except ValueError:
                    return None
        return None

    def _new_request_id(self) -> str:
        return f"req_{uuid4().hex}"

    def _new_session_id(self) -> str:
        return f"sess_{uuid4().hex}"


@dataclass(frozen=True)
class _AssessorOverlaySummary:
    assessor_raw_risk_hint: str
    deterministic_safety_level: str
    final_risk_level: str
    safety_override_applied: bool
    closing_override_applied: bool


@dataclass(frozen=True)
class _MemoryIndexSummary:
    retrieved_memories: list[ContextMemory]
    chunk_count: int
    indexed_count: int
    upserted_count: int
    reembedded_count: int
    skipped_count: int
    provider: str
    retrieved_count: int
    retrieval_latency_ms: int
    used_memory_index_fallback: bool
    chunk_ids: list[str]
    current_turn_vector_indexed: bool
    memory_retrieval_skipped: bool


class DecisionPipeline(ChatOrchestratorService):
    """Backward-compatible alias used by existing API dependencies."""
