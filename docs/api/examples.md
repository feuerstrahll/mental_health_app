# API Examples

## Health
```http
GET /api/v1/health
```

## Wellbeing Signals
```json
{
  "user_id": "u_123",
  "signals": {
    "emotion_marker": "anxious",
    "diary_note": "I feel exhausted today",
    "sleep_duration_hours": 5.5,
    "sleep_regularity": 2,
    "sleep_quality": 2,
    "physical_activity_minutes": 20,
    "sedentary_minutes": 720,
    "outdoor_minutes": 10,
    "social_connectedness": 2,
    "routine_regularity": 2
  }
}
```
