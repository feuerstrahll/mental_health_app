"""Tests for ResponseValidator."""

import asyncio
import json

import httpx
import pytest
from app.llm.qwen_client import OpenAICompatibleQwenClient
from app.llm.prompt_builder import PromptBuilder
from app.llm.response_composer import FallbackResponseFactory, QwenResponseService
from app.llm.response_validator import ResponseValidator, ValidationError
from app.models.user_memory_embedding import UserMemoryEmbedding
from app.schemas.decision import StructuredDecision


GENERIC_RESOURCE_GUIDANCE = (
    "localized crisis resources unavailable; advise local emergency services or a trusted nearby person"
)


@pytest.fixture
def validator() -> ResponseValidator:
    """Fixture providing ResponseValidator instance."""
    return ResponseValidator()


def test_user_memory_embedding_orm_exposes_required_db_columns() -> None:
    columns = UserMemoryEmbedding.__table__.columns
    required = {
        "id",
        "user_id",
        "memory_chunk_id",
        "source_type",
        "date",
        "text",
        "model",
        "dim",
        "metadata_jsonb",
        "embedding",
        "content_hash",
        "created_at",
        "updated_at",
    }

    assert required <= set(columns.keys())
    for name in required:
        assert not columns[name].nullable


class _StaticModelClient:
    def __init__(self, output: str) -> None:
        self.output = output

    async def generate_chat(self, *, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        return self.output


class _FailingModelClient:
    async def generate_chat(self, *, messages: list[dict[str, str]], timeout_seconds: float) -> str:
        raise RuntimeError("qwen unavailable")


class _FakeHttpResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class _FakeAsyncClient:
    calls: int = 0
    responses: list[_FakeHttpResponse | Exception] = []

    def __init__(self, *_args, **_kwargs) -> None:
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args) -> None:
        return None

    async def post(self, *_args, **_kwargs):
        type(self).calls += 1
        item = type(self).responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _valid_chat_response(content: str) -> str:
    return json.dumps({"choices": [{"message": {"content": content}}]})


def _qwen_client() -> OpenAICompatibleQwenClient:
    return OpenAICompatibleQwenClient(
        enabled=True,
        base_url="http://qwen.test",
        api_key="",
        model="qwen-test",
    )


def _qwen_response_service(model_client) -> QwenResponseService:
    return QwenResponseService(
        model_client=model_client,
        prompt_builder=PromptBuilder(),
        fallback_factory=FallbackResponseFactory(),
        timeout_seconds=1.0,
        max_response_chars=700,
    )


class TestValidResponseValidation:
    """Test validation of valid LLM responses."""

    def test_valid_normal_response(self, validator: ResponseValidator):
        """Valid response in normal mode."""
        output = '{"response_text": "РЇ РїРѕРЅРёРјР°СЋ, СЌС‚Рѕ РјРѕР¶РµС‚ Р±С‹С‚СЊ СЃР»РѕР¶РЅРѕ.", "followup_question": "РљР°Рє С‚С‹ РѕР±С‹С‡РЅРѕ СЃРїСЂР°РІР»СЏРµС€СЊСЃСЏ?"}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert result.is_valid
        assert result.response_text == "РЇ РїРѕРЅРёРјР°СЋ, СЌС‚Рѕ РјРѕР¶РµС‚ Р±С‹С‚СЊ СЃР»РѕР¶РЅРѕ."
        assert result.followup_question == "РљР°Рє С‚С‹ РѕР±С‹С‡РЅРѕ СЃРїСЂР°РІР»СЏРµС€СЊСЃСЏ?"
        assert len(result.errors) == 0

    def test_valid_crisis_response(self, validator: ResponseValidator):
        """Valid response in crisis mode."""
        output = '{"response_text": "Р’С‹Р·РѕРІРё СЃРєРѕСЂСѓСЋ РїРѕРјРѕС‰СЊ РёР»Рё РѕР±СЂР°С‚РёСЃСЊ Рє Р±Р»РёР·РєРѕРјСѓ С‡РµР»РѕРІРµРєСѓ.", "followup_question": null}'

        result = validator.validate(
            raw_output=output,
            expected_mode="crisis",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert result.is_valid
        assert result.response_text == "Р’С‹Р·РѕРІРё СЃРєРѕСЂСѓСЋ РїРѕРјРѕС‰СЊ РёР»Рё РѕР±СЂР°С‚РёСЃСЊ Рє Р±Р»РёР·РєРѕРјСѓ С‡РµР»РѕРІРµРєСѓ."
        assert result.followup_question is None

    def test_valid_close_response(self, validator: ResponseValidator):
        """Valid response when closing conversation."""
        output = '{"response_text": "РЎРїР°СЃРёР±Рѕ Р·Р° СЂР°Р·РіРѕРІРѕСЂ. РџРѕР·Р°Р±РѕС‚СЊСЃСЏ Рѕ СЃРµР±Рµ.", "followup_question": null}'

        result = validator.validate(
            raw_output=output,
            expected_mode="close_conversation",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert result.is_valid
        assert result.response_text == "РЎРїР°СЃРёР±Рѕ Р·Р° СЂР°Р·РіРѕРІРѕСЂ. РџРѕР·Р°Р±РѕС‚СЊСЃСЏ Рѕ СЃРµР±Рµ."
        assert result.followup_question is None

    def test_missing_followup_question_is_invalid(self, validator: ResponseValidator):
        """followup_question key is required, but may be null."""
        output = '{"response_text": "РЇ СЂСЏРґРѕРј. Р”Р°РІР°Р№С‚Рµ РІС‹Р±РµСЂРµРј РѕРґРёРЅ РјР°Р»РµРЅСЊРєРёР№ С€Р°Рі."}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert not result.is_valid
        assert result.errors[0].code == "missing_required_field"


class TestInvalidJSON:
    """Test JSON parsing errors."""

    def test_invalid_json(self, validator: ResponseValidator):
        """Response is not valid JSON."""
        output = '{"response_text": "broken'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert not result.is_valid
        assert len(result.errors) > 0
        assert result.errors[0].code == "invalid_json"

    def test_json_array_not_object(self, validator: ResponseValidator):
        """Response is JSON array instead of object."""
        output = '["response_text", "value"]'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert not result.is_valid
        assert result.errors[0].code == "not_json_object"

    def test_extra_confidence_field_is_rejected(self, validator: ResponseValidator):
        """Unknown LLM output fields are rejected."""
        output = '{"response_text": "РўРµРєСЃС‚", "followup_question": null, "confidence": 0.8}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert not result.is_valid
        assert result.errors[0].code == "unexpected_output_fields"


def test_extra_llm_output_fields_route_to_safe_fallback() -> None:
    service = QwenResponseService(
        model_client=_StaticModelClient('{"response_text": "РўРµРєСЃС‚", "followup_question": null, "confidence": 0.9}'),
        prompt_builder=PromptBuilder(),
        fallback_factory=FallbackResponseFactory(),
        timeout_seconds=1.0,
        max_response_chars=640,
    )
    decision = StructuredDecision(
        support_mode="context_first_support",
        recommended_action="supportive_response",
        response_mode="normal",
        risk_level="safe",
    )

    result = asyncio.run(
        service.compose(
            decision,
            latest_user_message="Привет",
            latest_diary_note=None,
            dialogue_state={},
        )
    )

    assert result.meta.used_fallback is True
    assert result.meta.fallback_reason == "validation:unexpected_output_fields"


def test_crisis_fallback_uses_generic_guidance_when_resource_list_empty() -> None:
    service = QwenResponseService(
        model_client=_StaticModelClient("not json"),
        prompt_builder=PromptBuilder(),
        fallback_factory=FallbackResponseFactory(),
        timeout_seconds=1.0,
        max_response_chars=640,
    )
    decision = StructuredDecision(
        support_mode="context_first_support",
        recommended_action="supportive_response",
        response_mode="crisis",
        risk_level="crisis",
        safe_mode=True,
        verified_safety_resources=[],
    )

    result = asyncio.run(
        service.compose(
            decision,
            latest_user_message="I want to kill myself",
            latest_diary_note=None,
            dialogue_state={},
        )
    )

    assert result.meta.used_fallback is True
    assert GENERIC_RESOURCE_GUIDANCE in result.text
    assert "http://" not in result.text
    assert "https://" not in result.text
    assert "112" not in result.text


def test_crisis_fallback_does_not_require_qwen() -> None:
    service = QwenResponseService(
        model_client=_FailingModelClient(),
        prompt_builder=PromptBuilder(),
        fallback_factory=FallbackResponseFactory(),
        timeout_seconds=1.0,
        max_response_chars=640,
    )
    decision = StructuredDecision(
        support_mode="context_first_support",
        recommended_action="supportive_response",
        response_mode="crisis",
        risk_level="crisis",
        safe_mode=True,
        verified_safety_resources=[GENERIC_RESOURCE_GUIDANCE],
    )

    result = asyncio.run(
        service.compose(
            decision,
            latest_user_message="I want to kill myself",
            latest_diary_note=None,
            dialogue_state={},
        )
    )

    assert result.meta.used_fallback is True
    assert result.meta.fallback_reason == "model_error"
    assert GENERIC_RESOURCE_GUIDANCE in result.text


def test_qwen_retries_once_and_succeeds(monkeypatch) -> None:
    _FakeAsyncClient.calls = 0
    _FakeAsyncClient.responses = [
        _FakeHttpResponse(503, "temporary provider error"),
        _FakeHttpResponse(
            200,
            _valid_chat_response('{"response_text": "ok", "followup_question": null}'),
        ),
    ]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    result = asyncio.run(
        _qwen_client().generate_chat(
            messages=[{"role": "user", "content": "hello"}],
            timeout_seconds=1.0,
        )
    )

    assert result == '{"response_text": "ok", "followup_question": null}'
    assert _FakeAsyncClient.calls == 2


def test_qwen_4xx_does_not_retry_and_falls_back(monkeypatch) -> None:
    _FakeAsyncClient.calls = 0
    _FakeAsyncClient.responses = [_FakeHttpResponse(400, "bad request with provider detail")]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    decision = StructuredDecision(
        support_mode="context_first_support",
        recommended_action="supportive_response",
        response_mode="normal",
        risk_level="safe",
    )
    result = asyncio.run(
        _qwen_response_service(_qwen_client()).compose(
            decision,
            latest_user_message="hello",
            latest_diary_note=None,
            dialogue_state={},
        )
    )

    assert _FakeAsyncClient.calls == 1
    assert result.meta.used_fallback is True
    assert result.meta.fallback_reason == "model_http_error"
    assert "provider detail" not in result.meta.fallback_reason


def test_qwen_invalid_model_content_does_not_retry_and_falls_back(monkeypatch) -> None:
    _FakeAsyncClient.calls = 0
    _FakeAsyncClient.responses = [_FakeHttpResponse(200, _valid_chat_response("not json"))]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    decision = StructuredDecision(
        support_mode="context_first_support",
        recommended_action="supportive_response",
        response_mode="normal",
        risk_level="safe",
    )
    result = asyncio.run(
        _qwen_response_service(_qwen_client()).compose(
            decision,
            latest_user_message="hello",
            latest_diary_note=None,
            dialogue_state={},
        )
    )

    assert _FakeAsyncClient.calls == 1
    assert result.meta.used_fallback is True
    assert result.meta.fallback_reason == "validation:invalid_json"


def test_qwen_5xx_retries_only_once_then_falls_back(monkeypatch) -> None:
    _FakeAsyncClient.calls = 0
    _FakeAsyncClient.responses = [
        _FakeHttpResponse(503, "temporary provider error one"),
        _FakeHttpResponse(503, "temporary provider error two"),
    ]
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)

    decision = StructuredDecision(
        support_mode="context_first_support",
        recommended_action="supportive_response",
        response_mode="normal",
        risk_level="safe",
    )
    result = asyncio.run(
        _qwen_response_service(_qwen_client()).compose(
            decision,
            latest_user_message="hello",
            latest_diary_note=None,
            dialogue_state={},
        )
    )

    assert _FakeAsyncClient.calls == 2
    assert result.meta.used_fallback is True
    assert result.meta.fallback_reason == "model_http_error"


class TestResponseTextValidation:
    """Test response_text field validation."""

    def test_response_text_missing(self, validator: ResponseValidator):
        """response_text field is missing."""
        output = '{"followup_question": "?"}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert not result.is_valid
        assert result.errors[0].code == "missing_required_field"

    def test_response_text_empty(self, validator: ResponseValidator):
        """response_text is empty string."""
        output = '{"response_text": "", "followup_question": null}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert not result.is_valid
        assert result.errors[0].code == "response_text_empty"

    def test_response_text_exceeds_max_chars(self, validator: ResponseValidator):
        """response_text exceeds max_response_chars."""
        long_text = "Рђ" * 150  # 150 Cyrillic characters
        output = f'{{"response_text": "{long_text}", "followup_question": null}}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=100,
            allow_followup_question=False,
        )

        assert not result.is_valid
        assert result.errors[0].code == "response_too_long"


class TestFollowupQuestionValidation:
    """Test followup_question constraints."""

    def test_followup_not_allowed(self, validator: ResponseValidator):
        """followup_question provided when not allowed."""
        output = '{"response_text": "РўРµРєСЃС‚", "followup_question": "Р’РѕРїСЂРѕСЃ?"}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert not result.is_valid
        assert result.errors[0].code == "followup_not_allowed"

    def test_followup_not_allowed_in_close_mode(self, validator: ResponseValidator):
        """followup_question provided in close_conversation mode."""
        output = '{"response_text": "Р”Рѕ РІСЃС‚СЂРµС‡Рё", "followup_question": "РљРѕРіРґР° С‚С‹ РІРµСЂРЅРµС€СЊСЃСЏ?"}'

        result = validator.validate(
            raw_output=output,
            expected_mode="close_conversation",
            max_response_chars=1000,
            allow_followup_question=True,  # Even if allowed, not allowed in close mode
        )

        assert not result.is_valid
        assert result.errors[0].code == "followup_not_allowed_in_close"

    def test_followup_null_is_valid(self, validator: ResponseValidator):
        """followup_question can be null."""
        output = '{"response_text": "РўРµРєСЃС‚", "followup_question": null}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert result.is_valid
        assert result.followup_question is None

    def test_more_than_one_followup_question_is_rejected(self, validator: ResponseValidator):
        """More than one question is rejected."""
        output = '{"response_text": "РўРµРєСЃС‚", "followup_question": "Р§С‚Рѕ СЃРµР№С‡Р°СЃ РІР°Р¶РЅРѕ? Р§С‚Рѕ РїРѕРјРѕР¶РµС‚?"}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert not result.is_valid
        assert any(e.code in {"too_many_questions", "followup_too_many_questions"} for e in result.errors)


class TestForbiddenPhrases:
    """Test forbidden phrase detection."""

    def test_detects_diagnosis_phrase(self, validator: ResponseValidator):
        """Detects diagnosis language."""
        output = json.dumps({"response_text": "\u0423 \u0432\u0430\u0441 \u0435\u0441\u0442\u044c \u0434\u0435\u043f\u0440\u0435\u0441\u0441\u0438\u044f.", "followup_question": None})

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert not result.is_valid
        assert any("forbidden_phrase" in e.code for e in result.errors)

    def test_detects_treatment_prescription(self, validator: ResponseValidator):
        """Detects treatment prescription."""
        output = json.dumps({"response_text": "\u0412\u0430\u043c \u043d\u0443\u0436\u043d\u043e \u043f\u0440\u0438\u043d\u044f\u0442\u044c \u0430\u043d\u0442\u0438\u0434\u0435\u043f\u0440\u0435\u0441\u0441\u0430\u043d\u0442\u044b.", "followup_question": None})

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert not result.is_valid
        assert any("forbidden_phrase" in e.code for e in result.errors)

    def test_detects_invented_hotline(self, validator: ResponseValidator):
        """Detects invented hotline mention."""
        output = json.dumps({"response_text": "\u041f\u043e\u0437\u0432\u043e\u043d\u0438 \u043d\u0430 \u0433\u043e\u0440\u044f\u0447\u0443\u044e \u043b\u0438\u043d\u0438\u044e 123-45-67.", "followup_question": None})

        result = validator.validate(
            raw_output=output,
            expected_mode="crisis",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert not result.is_valid
        assert any("forbidden_phrase" in e.code for e in result.errors)

    def test_detects_invented_crisis_resource_url(self, validator: ResponseValidator):
        """Detects unsupported crisis resource URLs."""
        output = '{"response_text": "РћР±СЂР°С‚РёСЃСЊ РЅР° СЃР°Р№С‚ https://fake-crisis.example.", "followup_question": null}'

        result = validator.validate(
            raw_output=output,
            expected_mode="crisis",
            max_response_chars=1000,
            allow_followup_question=False,
            verified_safety_resources=[],
        )

        assert not result.is_valid
        assert any(e.code == "unsupported_crisis_resource" for e in result.errors)

    def test_detects_manipulative_language(self, validator: ResponseValidator):
        """Detects manipulative intimate language."""
        output = json.dumps({"response_text": "\u0422\u044b \u043c\u043d\u0435 \u043e\u0447\u0435\u043d\u044c \u043d\u0443\u0436\u0435\u043d.", "followup_question": None})

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert not result.is_valid
        assert any("forbidden_phrase" in e.code for e in result.errors)

    def test_detects_clinical_certainty(self, validator: ResponseValidator):
        """Detects clinical certainty."""
        output = json.dumps({"response_text": "\u042d\u0442\u043e \u0442\u043e\u0447\u043d\u043e \u0434\u0435\u043f\u0440\u0435\u0441\u0441\u0438\u044f.", "followup_question": None})

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert not result.is_valid
        assert any("forbidden_phrase" in e.code for e in result.errors)

    def test_rejects_over_personalized_history_claim_for_no_personalization(self, validator: ResponseValidator):
        """Continuity claims are rejected when personalization is none."""
        output = '{"response_text": "Based on your history, this keeps happening.", "followup_question": null}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
            personalization_level="none",
            memory_retrieval_quality="good",
        )

        assert not result.is_valid
        assert any(e.code == "over_personalized_continuity_claim" for e in result.errors)

    def test_rejects_russian_history_claim_for_weak_memory(self, validator: ResponseValidator):
        """Russian continuity claims are rejected when memory is weak."""
        output = json.dumps({"response_text": "\u0421\u0443\u0434\u044f \u043f\u043e \u0442\u0432\u043e\u0435\u0439 \u0438\u0441\u0442\u043e\u0440\u0438\u0438, \u0442\u044b \u043e\u0431\u044b\u0447\u043d\u043e \u0442\u0430\u043a \u0440\u0435\u0430\u0433\u0438\u0440\u0443\u0435\u0448\u044c.", "followup_question": None})

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
            personalization_level="normal",
            memory_retrieval_quality="weak",
        )

        assert not result.is_valid
        assert any(e.code == "over_personalized_continuity_claim" for e in result.errors)

    def test_no_false_positives_on_normal_text(self, validator: ResponseValidator):
        """Normal supportive text doesn't trigger false positives."""
        output = '{"response_text": "РЇ СЃР»С‹С€Сѓ, С‡С‚Рѕ С‚РµР±Рµ С‚СЏР¶РµР»Рѕ. РњРѕР¶РµС‚ РїРѕРјРѕС‡СЊ СЂР°Р·РіРѕРІРѕСЂ?", "followup_question": null}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert result.is_valid


class TestModeDetection:
    """Test response mode detection."""

    def test_detects_crisis_mode_from_indicators(self, validator: ResponseValidator):
        """Detects crisis mode from emergency indicators."""
        output = json.dumps({"response_text": "\u0412\u044b\u0437\u043e\u0432\u0438 \u0441\u043a\u043e\u0440\u0443\u044e \u043f\u043e\u043c\u043e\u0449\u044c \u0441\u0435\u0439\u0447\u0430\u0441.", "followup_question": None})

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert result.detected_mode == "crisis"
        assert len(result.warnings) > 0
        assert result.warnings[0].code == "mode_mismatch"

    def test_detects_close_mode_from_indicators(self, validator: ResponseValidator):
        """Detects close mode from closing indicators."""
        output = json.dumps({"response_text": "\u0423\u0434\u0430\u0447\u0438, \u043f\u043e\u0437\u0430\u0431\u043e\u0442\u044c\u0441\u044f \u043e \u0441\u0435\u0431\u0435.", "followup_question": None})

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert result.detected_mode == "close_conversation"
        assert len(result.warnings) > 0


class TestWhitespaceHandling:
    """Test whitespace trimming."""

    def test_trims_response_text_whitespace(self, validator: ResponseValidator):
        """Whitespace is trimmed from response_text."""
        output = '{"response_text": "  РўРµРєСЃС‚ СЃ РїСЂРѕР±РµР»Р°РјРё  ", "followup_question": null}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=False,
        )

        assert result.is_valid
        assert result.response_text == "РўРµРєСЃС‚ СЃ РїСЂРѕР±РµР»Р°РјРё"

    def test_trims_followup_question_whitespace(self, validator: ResponseValidator):
        """Whitespace is trimmed from followup_question."""
        output = '{"response_text": "РўРµРєСЃС‚", "followup_question": "  Р’РѕРїСЂРѕСЃ?  "}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert result.is_valid
        assert result.followup_question == "Р’РѕРїСЂРѕСЃ?"

    def test_empty_followup_becomes_null(self, validator: ResponseValidator):
        """Empty followup_question after trimming becomes null."""
        output = '{"response_text": "РўРµРєСЃС‚", "followup_question": "   "}'

        result = validator.validate(
            raw_output=output,
            expected_mode="normal",
            max_response_chars=1000,
            allow_followup_question=True,
        )

        assert result.is_valid
        assert result.followup_question is None

