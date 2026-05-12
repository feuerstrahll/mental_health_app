"""Response validator - ensures LLM outputs follow safety constraints."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence

from app.services.safety.safety_classifier import SafetyGateResult, SafetyResourceService

if TYPE_CHECKING:
    from app.llm.response_composer import ComposeResult


@dataclass(frozen=True)
class ValidationError:
    """Single validation error."""

    code: str
    message: str
    severity: str  # "critical" | "warning" | "recoverable"


@dataclass(frozen=True)
class ResponseValidationResult:
    """Result of validating LLM response."""

    is_valid: bool
    response_text: str | None = None
    followup_question: str | None = None
    detected_mode: str | None = None
    errors: tuple[ValidationError, ...] = ()
    warnings: tuple[ValidationError, ...] = ()


@dataclass(frozen=True)
class _RawValidationStage:
    payload: dict[str, Any] | None
    errors: tuple[ValidationError, ...]


@dataclass(frozen=True)
class _SchemaValidationStage:
    response_text: str | None
    followup_question: str | None
    errors: tuple[ValidationError, ...]


class ResponseValidator:
    """
    Validates LLM output against safety constraints.

    Enforces:
    1. Valid JSON structure
    2. response_text is non-empty string
    3. Response mode matches SafetyClassification.mode (immutable)
    4. No forbidden phrases (diagnoses, medical certainty, invented resources, etc.)
    5. followup_question constraints per safety mode
    """

    ALLOWED_FIELDS = {"response_text", "followup_question"}

    # Forbidden patterns - responses must not contain these
    FORBIDDEN_PHRASES = {
        # Medical diagnosis
        "диагноз": ("diagnosis", "Responses must not suggest diagnoses"),
        "у вас есть": ("diagnosed_condition", "Cannot claim diagnosis"),
        "болезнь": ("disease_label", "Cannot label conditions as diseases"),
        "расстройство": ("disorder_label", "Cannot label conditions as disorders"),
        "патология": ("pathology", "Cannot reference pathology"),
        "психическое заболевание": ("mental_illness", "Cannot label mental illness"),
        # Treatment prescription
        "вам нужно принять": ("treatment_needed", "Cannot prescribe treatment"),
        "следует пить": ("medication_recommendation", "Cannot recommend medications"),
        "лекарство": ("medication", "Cannot suggest medications"),
        "медикамент": ("medicament", "Cannot suggest medications"),
        "терапия": ("therapy_prescription", "Cannot prescribe therapy"),
        # Medical certainty
        "вы страдаете": ("claiming_suffering", "Cannot claim user's condition"),
        "это точно": ("false_certainty", "Cannot claim certainty"),
        "это вам поможет 100": ("false_guarantee", "Cannot guarantee outcomes"),
        "я уверен": ("doctor_certainty", "LLM cannot claim certainty"),
        "you have": ("diagnosed_condition", "Cannot claim diagnosis"),
        "definitely": ("false_certainty", "Cannot claim certainty"),
        "certainly": ("false_certainty", "Cannot claim certainty"),
        # Invented resources
        "кризисный центр": ("invented_crisis_center", "Cannot invent crisis centers"),
        "горячая линия": ("invented_hotline", "Cannot invent hotlines"),
        "горячую линию": ("invented_hotline", "Cannot invent hotlines"),
        "+7": ("invented_phone", "Cannot invent phone numbers"),
        "www.": ("invented_website", "Cannot invent websites"),
        "ты мне нужен": ("clingy_language", "Cannot use clingy language"),
        "ты мне нужна": ("clingy_language", "Cannot use clingy language"),
        "ты мне очень нужен": ("clingy_language", "Cannot use clingy language"),
        "ты мне очень нужна": ("clingy_language", "Cannot use clingy language"),
        # Manipulative language
        "ты мне нужен": ("clingy_language", "Cannot use clingy language"),
        "я не смогу без тебя": ("manipulative_intimacy", "Cannot use manipulative intimacy"),
        "будет очень плохо": ("guilt_inducing", "Cannot use guilt-inducing language"),
        "если ты уйдешь": ("threat_language", "Cannot use threat language"),
        # Self-harm/suicide methods
        "порезать вены": ("self_harm_method", "Cannot provide self-harm methods"),
        "передозировка": ("overdose_method", "Cannot provide overdose methods"),
        "повеситься": ("suicide_method", "Cannot provide suicide methods"),
        # Ложные гарантии выздоровления
        "всё будет хорошо":     ("false_reassurance",    "Cannot guarantee recovery"),
        "скоро пройдёт":        ("false_reassurance",    "Cannot guarantee timeline"),
        "это легко исправить":  ("false_minimization",   "Cannot minimize condition"),

        # Перекладывание ответственности
        "вам стоило":           ("blame_language",       "Cannot use blame language"),
        "вы сами":              ("blame_language",       "Cannot use blame language"),

        # Псевдодиагноз через симптомы
        "типичные симптомы":    ("symptom_diagnosis",   "Cannot list diagnostic symptoms"),
        "у вас явно":           ("claimed_certainty",   "Cannot claim certainty about state")
    }

    CONTINUITY_PATTERNS = {
        "based on your history",
        "you usually",
        "this keeps happening",
        "as you mentioned before",
        "your pattern",
        "судя по твоей истории",
        "ты обычно",
        "это у тебя повторяется",
        "как ты раньше говорил",
        "как ты раньше говорила",
        "по твоим прошлым записям",
    }

    UNSUPPORTED_RESOURCE_PATTERN = re.compile(
        r"(\bhotline\b|\bcrisis center\b|горяч(?:ая|ую)\s+лини[яю]|кризисн(?:ый|ого)\s+центр|"
        r"https?://|www\.|\+?\d[\d\s().-]{5,}\d)",
        re.IGNORECASE | re.UNICODE,
    )

    # Response mode detection patterns
    CRISIS_MODE_INDICATORS = {
        # Экстренные службы — прямые упоминания
        "скорая",
        "скорой помощи",
        "скорую помощь",
        "служба спасения",
        "экстренная помощь",
        # Призывы к звонку / вызову
        "вызови скорую",
        "вызвать скорую",
        "позвони в службу",
        "звони 112",
        "набери 112",
        "вызови 112",
    }

    
    CLOSE_MODE_INDICATORS = {
        # Явные прощания — специфичные для завершения сессии
        "до встречи",
        "спокойной ночи",
        "хорошего вечера",
        "хорошего дня",
        "береги себя",
        "позаботься о себе",
        "возвращайтесь, если",
        "возвращайся, если",
        "рад был помочь",
        "рада была помочь",
        "если понадоблюсь",
    }

    def __init__(self):
        """Initialize validator with forbidden phrases."""
        self._forbidden_pattern = self._compile_forbidden_pattern()

    def validate(
        self,
        *,
        raw_output: str,
        expected_mode: str,
        max_response_chars: int,
        allow_followup_question: bool,
        personalization_level: str = "normal",
        memory_retrieval_quality: str = "good",
        verified_safety_resources: Sequence[str] | None = None,
        allowed_citations: Sequence[str] | None = None,
    ) -> ResponseValidationResult:
        """
        Validate LLM response against constraints.

        Args:
            raw_output: Raw JSON string from LLM
            expected_mode: SafetyClassification.mode (immutable constraint)
            max_response_chars: Maximum allowed response length
            allow_followup_question: Whether followup is allowed

        Returns:
            ResponseValidationResult with validation status and extracted fields
        """
        raw_result = self._validate_raw_json(raw_output)
        if raw_result.errors:
            return ResponseValidationResult(is_valid=False, errors=raw_result.errors)

        schema_result = self._validate_schema(raw_result.payload or {})
        if schema_result.errors:
            return ResponseValidationResult(is_valid=False, errors=schema_result.errors)

        response_text = schema_result.response_text or ""
        followup_question = schema_result.followup_question
        errors = list(
            self._validate_structured_response(
                response_text=response_text,
                followup_question=followup_question,
                expected_mode=expected_mode,
                max_response_chars=max_response_chars,
                allow_followup_question=allow_followup_question,
            )
        )

        detected_mode = self._detect_mode(response_text, expected_mode)
        errors.extend(
            self._validate_final_text_safety(
                response_text=response_text,
                followup_question=followup_question,
                expected_mode=expected_mode,
                personalization_level=personalization_level,
                memory_retrieval_quality=memory_retrieval_quality,
                verified_safety_resources=verified_safety_resources or (),
                allowed_citations=allowed_citations or (),
            )
        )

        warnings: list[ValidationError] = []
        if detected_mode != expected_mode and detected_mode is not None:
            warnings.append(
                ValidationError(
                    code="mode_mismatch",
                    message=f"Response appears to be in {detected_mode} mode but {expected_mode} expected",
                    severity="warning",
                )
            )

        is_valid = len(errors) == 0

        return ResponseValidationResult(
            is_valid=is_valid,
            response_text=response_text if is_valid else None,
            followup_question=followup_question if is_valid else None,
            detected_mode=detected_mode,
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    def _validate_raw_json(self, raw_output: str) -> "_RawValidationStage":
        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            return _RawValidationStage(
                payload=None,
                errors=(
                    ValidationError(
                        code="invalid_json",
                        message=f"LLM output is not valid JSON: {str(exc)}",
                        severity="critical",
                    ),
                ),
            )

        if not isinstance(parsed, dict):
            return _RawValidationStage(
                payload=None,
                errors=(
                    ValidationError(
                        code="not_json_object",
                        message="LLM output must be JSON object, not array",
                        severity="critical",
                    ),
                ),
            )

        return _RawValidationStage(payload=parsed, errors=())

    def _validate_schema(self, parsed: dict[str, Any]) -> "_SchemaValidationStage":
        extra_fields = set(parsed) - self.ALLOWED_FIELDS
        if extra_fields:
            return _SchemaValidationStage(
                response_text=None,
                followup_question=None,
                errors=(
                    ValidationError(
                        code="unexpected_output_fields",
                        message="LLM output contains unsupported fields",
                        severity="critical",
                    ),
                ),
            )

        required_fields = {"response_text", "followup_question"}
        missing_fields = required_fields - set(parsed)
        if missing_fields:
            return _SchemaValidationStage(
                response_text=None,
                followup_question=None,
                errors=(
                    ValidationError(
                        code="missing_required_field",
                        message=f"LLM output is missing required field: {sorted(missing_fields)[0]}",
                        severity="critical",
                    ),
                ),
            )

        response_text = parsed.get("response_text")
        if not isinstance(response_text, str):
            return _SchemaValidationStage(
                response_text=None,
                followup_question=None,
                errors=(
                    ValidationError(
                        code="response_text_missing",
                        message="response_text field must be string",
                        severity="critical",
                    ),
                ),
            )

        response_text = response_text.strip()
        if not response_text:
            return _SchemaValidationStage(
                response_text=None,
                followup_question=None,
                errors=(
                    ValidationError(
                        code="response_text_empty",
                        message="response_text cannot be empty",
                        severity="critical",
                    ),
                ),
            )

        followup_question = parsed.get("followup_question")
        if followup_question is not None:
            if not isinstance(followup_question, str):
                return _SchemaValidationStage(
                    response_text=response_text,
                    followup_question=None,
                    errors=(
                        ValidationError(
                            code="followup_not_string",
                            message="followup_question must be string or null",
                            severity="critical",
                        ),
                    ),
                )
            followup_question = followup_question.strip() or None

        return _SchemaValidationStage(
            response_text=response_text,
            followup_question=followup_question,
            errors=(),
        )

    def _validate_structured_response(
        self,
        *,
        response_text: str,
        followup_question: str | None,
        expected_mode: str,
        max_response_chars: int,
        allow_followup_question: bool,
    ) -> tuple[ValidationError, ...]:
        errors: list[ValidationError] = []
        if len(response_text) > max_response_chars:
            errors.append(
                ValidationError(
                    code="response_too_long",
                    message=f"response_text exceeds {max_response_chars} characters",
                    severity="critical",
                )
            )

        if followup_question is not None and not allow_followup_question:
            errors.append(
                ValidationError(
                    code="followup_not_allowed",
                    message="followup_question not allowed in this safety mode",
                    severity="critical",
                )
            )

        if expected_mode == "close_conversation" and followup_question is not None:
            errors.append(
                ValidationError(
                    code="followup_not_allowed_in_close",
                    message="followup_question not allowed when closing conversation",
                    severity="critical",
                )
            )

        question_count = self._count_question_marks(response_text, followup_question)
        if not allow_followup_question and question_count > 0:
            errors.append(
                ValidationError(
                    code="followup_not_allowed",
                    message="Questions are not allowed in this safety mode",
                    severity="critical",
                )
            )

        if question_count > 1:
            errors.append(
                ValidationError(
                    code="too_many_questions",
                    message="LLM output contains more than one question",
                    severity="critical",
                )
            )

        if followup_question is not None and self._count_question_marks("", followup_question) > 1:
            errors.append(
                ValidationError(
                    code="followup_too_many_questions",
                    message="followup_question contains more than one question",
                    severity="critical",
                )
            )

        return tuple(errors)

    def _validate_final_text_safety(
        self,
        *,
        response_text: str,
        followup_question: str | None,
        expected_mode: str,
        personalization_level: str,
        memory_retrieval_quality: str,
        verified_safety_resources: Sequence[str],
        allowed_citations: Sequence[str],
    ) -> tuple[ValidationError, ...]:
        errors: list[ValidationError] = []
        combined_text = "\n".join(part for part in (response_text, followup_question) if part)
        for match in self._check_forbidden_phrases(combined_text):
            errors.append(
                ValidationError(
                    code=f"forbidden_phrase_{match['code']}",
                    message=f"Response contains forbidden phrase: {match['phrase']}",
                    severity="critical",
                )
            )

        if self._uses_unsupported_resource(
            combined_text,
            verified_safety_resources=verified_safety_resources,
            allowed_citations=allowed_citations,
        ):
            errors.append(
                ValidationError(
                    code="unsupported_crisis_resource",
                    message="Response contains unsupported crisis resource",
                    severity="critical",
                )
            )

        if self._over_personalizes(
            combined_text,
            personalization_level=personalization_level,
            memory_retrieval_quality=memory_retrieval_quality,
        ):
            errors.append(
                ValidationError(
                    code="over_personalized_continuity_claim",
                    message="Response claims continuity beyond available personalization context",
                    severity="critical",
                )
            )

        return tuple(errors)

    def _compile_forbidden_pattern(self) -> re.Pattern:
        """Compile regex pattern for forbidden phrases."""
        phrases = [re.escape(phrase) for phrase in self.FORBIDDEN_PHRASES.keys()]
        pattern_str = "|".join(phrases)
        return re.compile(pattern_str, re.IGNORECASE | re.UNICODE)

    def _check_forbidden_phrases(self, text: str) -> list[dict[str, str]]:
        """Find forbidden phrases in text."""
        matches = []
        for match in self._forbidden_pattern.finditer(text):
            phrase = match.group()
            code, _ = self.FORBIDDEN_PHRASES.get(phrase.lower(), ("unknown", ""))
            matches.append({"phrase": phrase, "code": code})
        return matches

    def _uses_unsupported_resource(
        self,
        text: str,
        *,
        verified_safety_resources: Sequence[str],
        allowed_citations: Sequence[str],
    ) -> bool:
        match = self.UNSUPPORTED_RESOURCE_PATTERN.search(text)
        if match is None:
            return False

        allowed_blob = "\n".join(
            str(value).strip().lower()
            for value in (*verified_safety_resources, *allowed_citations)
            if str(value).strip()
        )
        if not allowed_blob:
            return True

        matched_text = match.group().strip().lower()
        return matched_text not in allowed_blob

    def _over_personalizes(
        self,
        text: str,
        *,
        personalization_level: str,
        memory_retrieval_quality: str,
    ) -> bool:
        level = (personalization_level or "none").strip().lower()
        quality = (memory_retrieval_quality or "none").strip().lower()
        if level != "none" and quality not in {"weak", "none"}:
            return False

        normalized = text.lower()
        return any(pattern in normalized for pattern in self.CONTINUITY_PATTERNS)

    def _count_question_marks(self, response_text: str, followup_question: str | None) -> int:
        total = response_text.count("?") + response_text.count("Шџ")
        if followup_question:
            total += followup_question.count("?") + followup_question.count("Шџ")
        return total

    def _detect_mode(self, response_text: str, expected_mode: str) -> str | None:
        text_lower = response_text.lower()
        if any(indicator in text_lower for indicator in self.CRISIS_MODE_INDICATORS):
            return "crisis"
        if any(indicator in text_lower for indicator in self.CLOSE_MODE_INDICATORS):
            return "close_conversation"
        return expected_mode

    async def validate_with_fallback(
        self,
        *,
        raw_output: str,
        expected_mode: str,
        max_response_chars: int,
        allow_followup_question: bool,
        fallback_responses: dict[str, str] | None = None,
    ) -> ResponseValidationResult:
        result = self.validate(
            raw_output=raw_output,
            expected_mode=expected_mode,
            max_response_chars=max_response_chars,
            allow_followup_question=allow_followup_question,
        )

        if not result.is_valid and fallback_responses:
            fallback_text = fallback_responses.get(expected_mode)
            if fallback_text:
                return ResponseValidationResult(
                    is_valid=True,
                    response_text=fallback_text,
                    followup_question=None,
                    detected_mode=expected_mode,
                    errors=result.errors,
                    warnings=(
                        *result.warnings,
                        ValidationError(
                            code="used_fallback_response",
                            message="Fell back to safe response due to validation errors",
                            severity="warning",
                        ),
                    ),
                )

        return result



class LLMResponseValidator:
    """Deprecated compatibility adapter; live Qwen output uses app.llm.ResponseValidator."""

    def __init__(self, *, max_response_chars: int = 640) -> None:
        self._max_response_chars = max_response_chars
        self._validator = ResponseValidator()

    def validate(
        self,
        *,
        text: str,
        safety: SafetyGateResult,
        allowed_citations: Sequence[str],
    ) -> ComposeResult:
        from app.llm.response_composer import ComposeMeta, ComposeResult

        cleaned = self._sanitize(text=text, safety=safety)
        raw_output = json.dumps({"response_text": cleaned, "followup_question": None}, ensure_ascii=False)
        result = self._validator.validate(
            raw_output=raw_output,
            expected_mode=self._expected_mode(safety),
            max_response_chars=min(self._max_response_chars, 520) if safety.mode == "crisis" else self._max_response_chars,
            allow_followup_question=False,
            personalization_level="normal",
            memory_retrieval_quality="good",
            allowed_citations=allowed_citations,
        )
        if result.is_valid:
            return ComposeResult(
                text=result.response_text or cleaned,
                meta=ComposeMeta(
                    used_fallback=False,
                    fallback_reason=None,
                    latency_ms=0,
                    raw_model_response=text,
                ),
            )
        reason = result.errors[0].code if result.errors else "validation_failed"
        return ComposeResult(
            text=self._fallback_text(safety),
            meta=ComposeMeta(
                used_fallback=True,
                fallback_reason=f"validation_{reason}",
                latency_ms=0,
                raw_model_response=text,
            ),
        )

    def _sanitize(self, *, text: str, safety: SafetyGateResult) -> str:
        cleaned = re.sub(r"[ \t]+", " ", text or "").strip()
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        max_chars = min(self._max_response_chars, 650 if safety.mode == "crisis" else self._max_response_chars)
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars].rstrip() + "..."
        return cleaned

    def _expected_mode(self, safety: SafetyGateResult) -> str:
        if safety.mode == "crisis":
            return "crisis"
        if safety.mode == "closing":
            return "close_conversation"
        if safety.safe_mode:
            return "safe_support"
        return "normal"

    def _fallback_text(self, safety: SafetyGateResult) -> str:
        if safety.mode == "crisis":
            resource_text = " ".join(resource.as_prompt_text() for resource in safety.verified_resources).strip()
            guidance = resource_text or SafetyResourceService.GENERIC_UNAVAILABLE_GUIDANCE
            return f"I am really sorry you are going through this. {guidance}."
        if safety.mode == "closing":
            return "Understood. I will stop here."
        return "I am here with you. Let's keep this very simple and take one small safe step."


class ResponseValidationService(LLMResponseValidator):
    """Backward-compatible alias."""
