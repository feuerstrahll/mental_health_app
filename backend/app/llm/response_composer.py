from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from app.llm.prompt_builder import PromptBuildResult, PromptBuilder
from app.llm.qwen_client import ModelClient, ModelClientError, ModelDisabledError, ModelTimeoutError
from app.llm.response_validator import ResponseValidator
from app.schemas.decision import StructuredDecision

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComposeMeta:
    used_fallback: bool
    fallback_reason: str | None
    latency_ms: int
    raw_model_response: str | None = None


@dataclass(frozen=True)
class ComposeResult:
    text: str
    meta: ComposeMeta


@dataclass(frozen=True)
class ParsedModelOutput:
    response_text: str
    followup_question: str | None


class FallbackResponseFactory:
    ACTION_HINTS: dict[str, str] = {
        "show_emergency_resources": (
            "То, что вы сейчас переживаете — это серьёзно, и вы не должны справляться с этим в одиночку. "
            "Есть люди, которые готовы быть рядом прямо сейчас — экстренные службы вашего региона. "
            "Не нужно ничего объяснять идеально, просто позвоните."
        ),
        "offer_human_support_contact": (
            "Иногда важнее всего просто оказаться рядом с кем-то живым. "
            "Не обязательно говорить много — можно написать одному человеку одно сообщение. "
            "Это уже немало."
        ),
        "suggest_sleep_recovery_plan": (
            "Звучит так, будто тело давно просит передышки. "
            "Вам не нужно «исправлять» сон за одну ночь. "
            "Если получится лечь чуть раньше и убрать экран за полчаса до этого — уже хорошо."
        ),
        "suggest_short_walk": (
            "Когда внутри тесно, иногда помогает просто выйти — без цели, без маршрута. "
            "Пять минут на улице не обязаны ничего решить. "
            "Но иногда тело немного выдыхает."
        ),
        "prompt_short_reflection": (
            "Не нужно разбираться во всём сразу. "
            "Если хочется, можно просто назвать про себя одну вещь, которая сейчас давит сильнее всего. "
            "Иногда это уже чуть легче."
        ),
        "breathing_478": (
            "Сейчас не нужно ничего решать. "
            "Если тело согласно, попробуйте одно медленное дыхание: вдох на 4, задержка на 7, выдох на 8. "
            "Не обязательно повторять много раз — иногда достаточно одного."
        ),
        "box_breathing": (
            "Можно ничего не делать — просто дышать немного ровнее. "
            "Попробуйте: вдох на 4, пауза на 4, выдох на 4, пауза на 4. "
            "Это не упражнение, просто способ побыть с собой."
        ),
        "grounding_5_senses": (
            "Когда мысли уходят далеко, иногда помогает вернуться в комнату. "
            "Можно просто заметить: что вижу, что слышу, что чувствую под руками. "
            "Не нужно делать это «правильно»."
        ),
        "gentle_reflection_only": (
            "Не нужно ничего объяснять или оценивать. "
            "Если хочется, просто назовите про себя одно чувство, которое сейчас есть. "
            "Это уже контакт с собой."
        ),
        "self_compassion_prompt": (
            "То, что вы держитесь — уже немало, даже если кажется иначе. "
            "Сейчас не нужно большего, чем вы можете. "
            "Самый маленький шаг — это тоже шаг."
        ),
        "rest_permission_message": (
            "Отдых — это не слабость и не побег. "
            "Если сейчас нет сил — это сигнал, а не сбой. "
            "Можно остановиться, и это нормально."
        ),
        "hydration_pause": (
            "Иногда тело просит самого простого. "
            "Можно сделать паузу: несколько спокойных вдохов, стакан воды. "
            "Это не решение, но маленькая забота о себе."
        ),
        "tiny_step_reset": (
            "Не нужно решать всё сразу — это невозможно, и никто так не делает. "
            "Если есть что-то совсем маленькое, что можно сделать за пару минут — это уже достаточно. "
            "Остальное подождёт."
        ),
        "closing_support_message": (
            "Хорошо, что вы обозначили это. "
            "Мы останавливаемся здесь — и это правильное решение. "
            "Вы можете вернуться, когда захотите."
        ),
    }

    PROFILE_HINTS: dict[str, str] = {
        "overload_pattern": (
            "Похоже, сейчас всего навалилось разом — это тяжело, и понятно, что сложно. "
            "Вам не нужно справляться со всем этим прямо сейчас."
        ),
        "elevated_stress_pattern": (
            "Звучит так, будто за короткое время произошло много напряжённого. "
            "Это накапливается, и то, что вы чувствуете — закономерно."
        ),
        "depleted_pattern": (
            "Похоже, ресурса сейчас меньше, чем обычно — и это не ваша вина. "
            "Когда сил мало, маленький шаг уже много значит."
        ),
        "unstable_pattern": (
            "Похоже, состояние сейчас меняется — то лучше, то снова тяжело. "
            "Это бывает, и не означает, что что-то пошло не так."
        ),
        "stable_pattern": (
            "Похоже, сейчас есть какая-то опора — пусть и небольшая. "
            "Это важно замечать."
        ),
        "gentle_checkin": (
            "Прежде чем двигаться куда-то дальше, хочется просто спросить: "
            "как вы сейчас, если честно?"
        ),
        "reflective_support": (
            "Иногда важнее всего — просто быть услышанным, без советов и решений. "
            "Я здесь, и никуда не тороплюсь."
        ),
        "low_energy_support": (
            "Когда сил немного, не нужно ничего доказывать. "
            "Самый маленький шаг — уже достаточно."
        ),
        "grounding_support": (
            "Когда внутри неспокойно, иногда помогает просто вернуться в этот момент. "
            "Вы здесь, и это уже точка опоры."
        ),
        "problem_solving_support": (
            "Не нужно решать всё сразу. "
            "Если есть один маленький следующий шаг — его достаточно."
        ),
        "emotion_labeling_support": (
            "Иногда просто назвать то, что есть внутри — уже облегчение. "
            "Без оценки, без «надо» — просто что сейчас."
        ),
        "celebration_or_reinforcement": (
            "То, что произошло — стоит заметить. "
            "Это было непросто, и вы это сделали."
        ),
    }
    
    def build(
        self,
        *,
        decision: StructuredDecision,
        allow_followup_question: bool,
    ) -> str:
        if self._is_crisis_mode(decision):
            return self._build_crisis_response(decision)

        close_mode = self._is_close_mode(decision)
        safe_mode = bool(decision.safe_mode) and not close_mode

        if close_mode:
            return "Понял, остановимся здесь.\nСпасибо, что поделились. Берегите себя."

        explanation = self._build_explanation(decision, safe_mode=safe_mode)
        support_line = "С вами можно бережно, без давления и лишних ожиданий."
        action_line = self.ACTION_HINTS.get(
            decision.recommended_action,
            "Можно выбрать один очень небольшой и посильный шаг прямо сейчас.",
        )

        lines = [explanation, support_line, action_line]
        if allow_followup_question and (not safe_mode):
            question = self._followup_question(decision.followup_mode)
            if question:
                lines.append(question)

        return "\n".join(line for line in lines if line)

    def _build_crisis_response(self, decision: StructuredDecision) -> str:
        resource_text = " ".join(decision.verified_safety_resources or []).strip()
        if not resource_text:
            resource_text = (
                "localized crisis resources unavailable; advise local emergency services or a trusted nearby person"
            )
        return "\n".join(
            [
                "Мне жаль, что сейчас настолько тяжело.",
                resource_text,
            ]
        )

    def _build_explanation(self, decision: StructuredDecision, *, safe_mode: bool) -> str:
        if safe_mode:
            return (
                "Сейчас не нужно никуда торопиться. "
                "Можно двигаться совсем медленно — это тоже движение."
            )

        support_profile = (decision.support_profile or "").strip().lower()
        if support_profile in self.PROFILE_HINTS:
            return self.PROFILE_HINTS[support_profile]

        support_mode = (decision.support_mode or "").strip().lower()
        if support_mode == "crisis_support":
            return (
                "Слышу, что сейчас очень тяжело. "
                "Вы не должны справляться с этим в одиночку, и не нужно."
            )
        if support_mode == "high_touch_support":
            return (
                "Похоже, сейчас нужна особая бережность — и это нормально. "
                "Я здесь, и никуда не тороплюсь."
            )
        if support_mode == "guided_checkin":
            return (
                "Иногда помогает просто немного замедлиться и посмотреть, что есть прямо сейчас. "
                "Не нужно разбираться во всём — только один маленький шаг."
            )
        return (
            "Не нужно решать всё сразу. "
            "Самый маленький посильный шаг — уже достаточно."
        )

    def _followup_question(self, followup_mode: str | None) -> str | None:
        mode = (followup_mode or "").strip().lower()
        if mode in {"no_followup", "close_conversation", "none", ""}:
            return None
        if mode == "clarifying":
            return "Если смотреть только на ближайший час — что кажется хоть немного посильным?"
        if mode == "gentle_action":
            return "Есть ли что-то совсем маленькое, что было бы чуть легче попробовать прямо сейчас?"
        return "Что могло бы дать вам сейчас хоть немного больше опоры?"

    def _is_close_mode(self, decision: StructuredDecision) -> bool:
        followup_mode = (decision.followup_mode or "").strip().lower()
        if followup_mode == "close_conversation":
            return True
        response_mode = (decision.response_mode or "").strip().lower()
        risk_level = (decision.risk_level or "").strip().lower()
        if response_mode in {"closing", "closing_support"} or risk_level == "closing":
            return True
        stop_flags = {"stop_intent", "boundary_request"}
        return any(flag in stop_flags for flag in decision.risk_flags)

    def _is_crisis_mode(self, decision: StructuredDecision) -> bool:
        return (decision.response_mode or "").strip().lower() == "crisis" or (
            decision.risk_level or ""
        ).strip().lower() == "crisis"


class QwenResponseService:
    FORBIDDEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("diagnosis_claim", re.compile(r"\b(диагноз|диагностир|у вас .*расстройств|you have)\b", re.IGNORECASE)),
        ("medical_claim", re.compile(r"\b(вам нужно лечение|назначаю|клиническ|medical certainty)\b", re.IGNORECASE)),
        ("certainty_claim", re.compile(r"\b(точно|однозначно|без сомнений)\b", re.IGNORECASE)),
        ("manipulative_intimacy", re.compile(r"\b(не уходи|ты мне нужен|я всегда с тобой|без меня)\b", re.IGNORECASE)),
        ("guilt_language", re.compile(r"\b(ты должен|ты обязана?|ты обязан)\b", re.IGNORECASE)),
    )

    STOP_MODE_CONTRADICTION = re.compile(
        r"\b(давай продолжим|можем продолжить|пиши дальше прямо сейчас|останься в чате)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        *,
        model_client: ModelClient,
        prompt_builder: PromptBuilder,
        fallback_factory: FallbackResponseFactory,
        timeout_seconds: float,
        max_response_chars: int,
        include_raw_model_response: bool = False,
        response_validator: ResponseValidator | None = None,
    ) -> None:
        self._model_client = model_client
        self._prompt_builder = prompt_builder
        self._fallback_factory = fallback_factory
        self._timeout_seconds = timeout_seconds
        self._max_response_chars = max_response_chars
        self._include_raw_model_response = include_raw_model_response
        self._response_validator = response_validator or ResponseValidator()

    async def compose(
        self,
        decision: StructuredDecision,
        *,
        latest_user_message: str | None = None,
        latest_diary_note: str | None = None,
        dialogue_state: dict[str, Any] | None = None,
    ) -> ComposeResult:
        start = time.perf_counter()
        allow_followup_question = self._allow_followup_question(decision)

        prompt = self._prompt_builder.build_messages(
            decision=decision,
            latest_user_message=latest_user_message,
            latest_diary_note=latest_diary_note,
            dialogue_state=dialogue_state,
            max_response_chars=self._max_response_chars,
            allow_followup_question=allow_followup_question,
        )

        raw_model_response: str | None = None
        try:
            raw_model_response = await self._model_client.generate_chat(
                messages=prompt.messages,
                timeout_seconds=self._timeout_seconds,
            )
            validation = self._response_validator.validate(
                raw_output=raw_model_response,
                expected_mode=self._expected_mode(prompt),
                max_response_chars=min(self._max_response_chars, 360) if prompt.safe_mode else self._max_response_chars,
                allow_followup_question=allow_followup_question and not prompt.close_mode,
                personalization_level=getattr(decision, "personalization_level", "none"),
                memory_retrieval_quality=getattr(decision, "memory_retrieval_quality", "none"),
                verified_safety_resources=getattr(decision, "verified_safety_resources", None) or [],
                allowed_citations=self._allowed_citations_from_practice_cards(decision),
            )
            if not validation.is_valid:
                first_error = validation.errors[0].code if validation.errors else "invalid_output"
                return self._fallback_result(
                    decision=decision,
                    reason=f"validation:{first_error}",
                    start_time=start,
                    raw_model_response=raw_model_response,
                    allow_followup_question=allow_followup_question,
                )

            parsed = ParsedModelOutput(
                response_text=validation.response_text or "",
                followup_question=validation.followup_question,
            )
            composed = self._merge_output(
                parsed=parsed,
                allow_followup_question=allow_followup_question,
            )
            sanitized = self._sanitize_output(
                composed,
                allow_followup_question=allow_followup_question,
                safe_mode=prompt.safe_mode,
            )
            violation = self._validate_output(
                sanitized,
                allow_followup_question=allow_followup_question,
                close_mode=prompt.close_mode,
            )
            if violation is not None:
                return self._fallback_result(
                    decision=decision,
                    reason=violation,
                    start_time=start,
                    raw_model_response=raw_model_response,
                    allow_followup_question=allow_followup_question,
                )

            return ComposeResult(
                text=sanitized,
                meta=ComposeMeta(
                    used_fallback=False,
                    fallback_reason=None,
                    latency_ms=self._latency_ms(start),
                    raw_model_response=raw_model_response if self._include_raw_model_response else None,
                ),
            )
        except ModelTimeoutError:
            return self._fallback_result(
                decision=decision,
                reason="model_timeout",
                start_time=start,
                raw_model_response=raw_model_response,
                allow_followup_question=allow_followup_question,
            )
        except ModelDisabledError:
            return self._fallback_result(
                decision=decision,
                reason="model_disabled",
                start_time=start,
                raw_model_response=raw_model_response,
                allow_followup_question=allow_followup_question,
            )
        except ModelClientError as exc:
            reason = self._fallback_reason_for_model_error(exc)
            logger.warning("qwen_model_client_error reason=%s detail=%s", reason, getattr(exc, "detail", None))
            return self._fallback_result(
                decision=decision,
                reason=reason,
                start_time=start,
                raw_model_response=raw_model_response,
                allow_followup_question=allow_followup_question,
            )
        except Exception as exc:  # defensive guard for malformed outputs
            logger.warning("qwen_unexpected_error error=%s", exc.__class__.__name__)
            return self._fallback_result(
                decision=decision,
                reason="model_error",
                start_time=start,
                raw_model_response=raw_model_response,
                allow_followup_question=allow_followup_question,
            )

    def _fallback_reason_for_model_error(self, exc: ModelClientError) -> str:
        reason = getattr(exc, "reason", str(exc))
        if reason == "model_http_error":
            return "model_http_error"
        if reason == "model_connection_error":
            return "model_client_error"
        if reason == "invalid_model_json":
            return "invalid_json"
        if reason == "empty_model_content":
            return "model_client_error"
        return "model_client_error"

    def _parse_model_output(self, raw_text: str) -> ParsedModelOutput:
        content = raw_text.strip()
        if content.startswith("```"):
            content = self._strip_code_fence(content)

        parsed = self._try_parse_json(content)
        if parsed is None:
            parsed = self._try_parse_json_from_braces(content)
        if parsed is None:
            raise ValueError("invalid_json_output")

        extra_fields = set(parsed) - {"response_text", "followup_question"}
        if extra_fields:
            raise ValueError("unexpected_output_fields")

        response_text = parsed.get("response_text")
        if not isinstance(response_text, str) or not response_text.strip():
            raise ValueError("missing_response_text")

        followup = parsed.get("followup_question")
        if followup is not None and not isinstance(followup, str):
            raise ValueError("invalid_followup_question")
        followup_question = followup.strip() if isinstance(followup, str) and followup.strip() else None
        return ParsedModelOutput(response_text=response_text.strip(), followup_question=followup_question)

    def _expected_mode(self, prompt: PromptBuildResult) -> str:
        if prompt.crisis_mode:
            return "crisis"
        if prompt.close_mode:
            return "close_conversation"
        if prompt.safe_mode:
            return "safe_support"
        return "normal"

    def _allowed_citations_from_practice_cards(self, decision: StructuredDecision) -> list[str]:
        out: list[str] = []
        for card in decision.practice_cards or []:
            for marker in ("источники=", "sources="):
                if marker in card:
                    out.append(card.split(marker, 1)[1].strip())
        return out

    def _merge_output(self, *, parsed: ParsedModelOutput, allow_followup_question: bool) -> str:
        text = parsed.response_text.strip()
        if allow_followup_question and parsed.followup_question:
            question = self._normalize_question(parsed.followup_question)
            if question:
                return f"{text}\n\n{question}"
        return text

    def _sanitize_output(self, text: str, *, allow_followup_question: bool, safe_mode: bool) -> str:
        cleaned = re.sub(r"[ \t]+", " ", text).strip()

        if not allow_followup_question:
            cleaned = cleaned.replace("?", ".")

        cleaned = self._enforce_one_question(cleaned)

        max_chars = self._max_response_chars
        if safe_mode:
            max_chars = min(max_chars, 560)
        cleaned = self._truncate(cleaned, max_chars=max_chars)

        paragraphs = [chunk.strip() for chunk in cleaned.split("\n") if chunk.strip()]
        if not paragraphs:
            return ""
        return "\n".join(paragraphs)

    def _validate_output(self, text: str, *, allow_followup_question: bool, close_mode: bool) -> str | None:
        if not text.strip():
            return "empty_output"

        for code, pattern in self.FORBIDDEN_PATTERNS:
            if pattern.search(text):
                return f"forbidden_phrase:{code}"

        question_count = text.count("?")
        if question_count > 1:
            return "too_many_questions"
        if (not allow_followup_question) and question_count > 0:
            return "followup_not_allowed"

        if close_mode and self.STOP_MODE_CONTRADICTION.search(text):
            return "stop_mode_contradiction"

        return None

    def _fallback_result(
        self,
        *,
        decision: StructuredDecision,
        reason: str,
        start_time: float,
        raw_model_response: str | None,
        allow_followup_question: bool,
    ) -> ComposeResult:
        text = self._fallback_factory.build(
            decision=decision,
            allow_followup_question=allow_followup_question,
        )
        text = self._sanitize_output(
            text,
            allow_followup_question=allow_followup_question,
            safe_mode=bool(decision.safe_mode),
        )
        logger.warning("qwen_response_fallback reason=%s", reason)
        return ComposeResult(
            text=text,
            meta=ComposeMeta(
                used_fallback=True,
                fallback_reason=reason,
                latency_ms=self._latency_ms(start_time),
                raw_model_response=raw_model_response if self._include_raw_model_response else None,
            ),
        )

    def _allow_followup_question(self, decision: StructuredDecision) -> bool:
        if decision.should_continue_dialogue is False:
            return False
        if self._is_close_mode(decision):
            return False
        mode = (decision.followup_mode or "").strip().lower()
        if mode in {"close_conversation", "no_followup", "none"}:
            return False
        if decision.safe_mode and mode not in {"clarifying", "reflective"}:
            return False
        return True

    def _is_close_mode(self, decision: StructuredDecision) -> bool:
        followup_mode = (decision.followup_mode or "").strip().lower()
        if followup_mode == "close_conversation":
            return True
        response_mode = (decision.response_mode or "").strip().lower()
        risk_level = (decision.risk_level or "").strip().lower()
        if response_mode in {"closing", "closing_support"} or risk_level == "closing":
            return True
        stop_flags = {"stop_intent", "boundary_request"}
        return any(flag in stop_flags for flag in decision.risk_flags)

    def _enforce_one_question(self, text: str) -> str:
        if text.count("?") <= 1:
            return text
        question_seen = False
        out_chars: list[str] = []
        for char in text:
            if char != "?":
                out_chars.append(char)
                continue
            if not question_seen:
                out_chars.append(char)
                question_seen = True
            else:
                out_chars.append(".")
        return "".join(out_chars)

    def _truncate(self, text: str, *, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text
        trimmed = text[:max_chars].rstrip()
        last_break = max(trimmed.rfind(". "), trimmed.rfind("\n"))
        if last_break >= int(max_chars * 0.65):
            trimmed = trimmed[: last_break + 1].rstrip()
        return trimmed

    def _normalize_question(self, text: str) -> str:
        question = text.strip()
        if not question:
            return ""
        if not question.endswith("?"):
            question = f"{question.rstrip('.!')}?"
        return question

    def _try_parse_json(self, text: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _try_parse_json_from_braces(self, text: str) -> dict[str, Any] | None:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = text[start : end + 1]
        return self._try_parse_json(candidate)

    def _strip_code_fence(self, text: str) -> str:
        stripped = text.strip()
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
        return stripped

    def _latency_ms(self, start_time: float) -> int:
        return int((time.perf_counter() - start_time) * 1000)


class ResponseComposer:
    """Compatibility wrapper around QwenResponseService."""

    def __init__(self, qwen_response_service: QwenResponseService) -> None:
        self._service = qwen_response_service

    async def compose(
        self,
        decision: StructuredDecision,
        *,
        latest_user_message: str | None = None,
        latest_diary_note: str | None = None,
        dialogue_state: dict[str, Any] | None = None,
    ) -> ComposeResult:
        return await self._service.compose(
            decision,
            latest_user_message=latest_user_message,
            latest_diary_note=latest_diary_note,
            dialogue_state=dialogue_state,
        )


def build_default_qwen_response_service(
    *,
    model_client: ModelClient,
    prompt_builder: PromptBuilder,
    timeout_seconds: float,
    max_response_chars: int,
    include_raw_model_response: bool,
) -> QwenResponseService:
    return QwenResponseService(
        model_client=model_client,
        prompt_builder=prompt_builder,
        fallback_factory=FallbackResponseFactory(),
        timeout_seconds=timeout_seconds,
        max_response_chars=max_response_chars,
        include_raw_model_response=include_raw_model_response,
    )
