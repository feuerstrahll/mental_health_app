# ML Integration (Realistic MVP, Product ML)

## 1. Product Principle

Мы не диагностируем психические расстройства и не пытаемся предсказать "истинное психическое состояние".

В MVP ML-слой решает продуктовую задачу:
- оценить потребность в поддержке: `support_need_score` (0..1),
- определить рабочий паттерн поддержки: `support_profile`,
- поднять `risk_flags`,
- выбрать безопасный тип ответа через шаблоны.

## 2. Layered Architecture

```
L0 Client Runtime (on-device)
  Flutter client
    ├─ local DB
    ├─ FeatureExtractor
    └─ ClientSafetyEngine
            │
            │ request payload + client safety result
            ▼
L1 Server API
  FastAPI server
    └─ ServerSafetyGate
            ├─ StructuredSupportModel
            ├─ NoteSignalDetector
            ├─ RecommendationEngine
            └─ ResponseComposer
                    │
                    ▼
             Structured decision object
```

## 3. Component Responsibilities

- `Flutter client`
  - Сбор check-in/chat input, отправка событий на сервер, рендер структурированного ответа.
- `local DB`
  - Локальная история check-in/чатов, последние решения, кэш шаблонов и safety-справочников.
- `FeatureExtractor`
  - Нормализует клиентские признаки (стресс, сон, частота check-in, базовые агрегаты по истории) без медицинских выводов.
- `ClientSafetyEngine`
  - Быстрый on-device pre-check (опасные ключевые фразы, self-harm hints, panic spike hints).
  - Может немедленно показать emergency UI, но не заменяет серверный safety.
- `FastAPI server`
  - Точка оркестрации и версионирования API/моделей, аудит решений.
- `ServerSafetyGate`
  - Главный policy-барьер: проверка риска, ограничение допустимых шаблонов, запрет небезопасных стратегий ответа.
- `StructuredSupportModel`
  - Выдает `support_need_score` и `support_profile`:
    - `stable_pattern`
    - `elevated_stress_pattern`
    - `depleted_pattern`
    - `unstable_pattern`
- `NoteSignalDetector`
  - Извлекает текстовые сигналы из заметки/сообщения и формирует `risk_flags` + evidence.
- `RecommendationEngine`
  - Объединяет: model output + note signals + history + rule-based контекст + user prefs/time-of-day.
  - Выбирает next-best-action и тип шаблона.
- `ResponseComposer`
  - Собирает ответ строго из русскоязычных шаблонов и блоков.
  - В MVP свободная генерация не используется как основной режим.

## 4. Data Flow (check-in -> response)

1. Пользователь отправляет check-in (эмоция, стресс, заметка, контекст).
2. `FeatureExtractor` формирует стандартизированный `feature_bundle`.
3. `ClientSafetyEngine` вычисляет `client_safety_result`.
4. Клиент отправляет запрос в `FastAPI server` с сырыми данными + `feature_bundle` + `client_safety_result`.
5. `ServerSafetyGate` выполняет первичный серверный risk/policy check.
6. `StructuredSupportModel` считает `support_need_score` и `support_profile`.
7. `NoteSignalDetector` выделяет сигналы из текста и формирует `risk_flags`.
8. `RecommendationEngine` агрегирует все источники и выбирает стратегию поддержки.
9. `ServerSafetyGate` повторно применяет policy к выбранной стратегии.
10. `ResponseComposer` формирует русскоязычный шаблонный ответ.
11. Сервер возвращает `decision_object` (структурированный), клиент рендерит блоки и CTA.

## 5. Decision Object Contract

```json
{
  "decision_id": "uuid",
  "timestamp_utc": "2026-04-21T10:15:30Z",
  "support_need_score": 0.78,
  "support_profile": "elevated_stress_pattern",
  "risk_flags": [
    {
      "code": "acute_distress_signal",
      "severity": "medium",
      "evidence": ["note_phrase: 'я не вывожу'"]
    }
  ],
  "safety": {
    "client": {
      "status": "pass",
      "flags": []
    },
    "server": {
      "status": "pass",
      "policy_version": "2026-04-21.1",
      "allowed_response_modes": ["template_only"]
    }
  },
  "recommendations": [
    {
      "id": "breathing_2min",
      "priority": 1,
      "reason_codes": ["high_stress_recent", "acute_distress_signal"]
    }
  ],
  "response_plan": {
    "mode": "template_only",
    "template_id": "ru.support.elevated.v2",
    "blocks": [
      {"type": "empathy", "text": "Похоже, сейчас правда тяжело."},
      {"type": "grounding", "text": "Давай начнем с 2 минут медленного дыхания."},
      {"type": "cta", "action": "open_breathing", "label": "Начать упражнение"}
    ]
  },
  "follow_up": {
    "needed": true,
    "delay_minutes": 180,
    "template_id": "ru.followup.short.v1"
  }
}
```

## 6. Client-Server API Contracts

### 6.1 `POST /v1/checkins/decision`

Назначение: решение по check-in (дневник).

Request:
```json
{
  "user_id": "anon_123",
  "event_id": "checkin_456",
  "client_timestamp": "2026-04-21T13:14:00+03:00",
  "timezone": "Europe/Moscow",
  "checkin": {
    "emotion": "тревога",
    "stress_level": 8,
    "energy_level": 3,
    "sleep_hours_last_night": 5.0,
    "note_text": "всё навалилось и сложно собраться"
  },
  "feature_bundle": {
    "entries_last_7d": 6,
    "avg_stress_7d": 7.1,
    "stress_trend_7d": "up",
    "sleep_avg_7d": 5.8
  },
  "client_safety_result": {
    "status": "pass",
    "flags": []
  }
}
```

Response: `200 OK` + `decision_object`.

### 6.2 `POST /v1/chat/decision`

Назначение: решение по входящему chat turn.

Request:
```json
{
  "user_id": "anon_123",
  "event_id": "chat_789",
  "message_text": "я очень устал и не вижу смысла",
  "conversation_context": {
    "last_decision_id": "uuid-prev",
    "last_5_messages": [
      {"role": "user", "text": "..."}, {"role": "assistant", "text": "..."}
    ]
  },
  "feature_bundle": {
    "avg_stress_7d": 8.0,
    "support_need_score_last": 0.71
  },
  "client_safety_result": {
    "status": "flagged",
    "flags": ["self_harm_hint"]
  }
}
```

Response: `200 OK` + `decision_object`.

### 6.3 `GET /v1/support/schema`

Назначение: получить текущие enum/версии для клиента.

Response:
```json
{
  "support_profiles": [
    "stable_pattern",
    "elevated_stress_pattern",
    "depleted_pattern",
    "unstable_pattern"
  ],
  "risk_flag_codes": [
    "self_harm_hint",
    "acute_distress_signal",
    "panic_spike_signal",
    "sleep_deprivation_signal",
    "social_isolation_signal"
  ],
  "response_mode": "template_only",
  "policy_version": "2026-04-21.1"
}
```

### 6.4 Error Contract (all endpoints)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "stress_level must be in range 1..10",
    "details": {"field": "checkin.stress_level"}
  }
}
```

## 7. MVP Guardrails

- Сервер всегда возвращает `decision_object`, не только `bot_response`.
- Основной режим ответа: `template_only` (русский шаблонный контент).
- ML = один вход в `RecommendationEngine`, но не единственный источник решения.
- Любые high-risk сигналы маршрутизируются через `ServerSafetyGate` и ограниченный набор безопасных ответов.
