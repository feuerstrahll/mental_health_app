from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class WellbeingSnapshot:
    user_id: str
    captured_at: datetime
    entry_date: date

    emotion_marker: str

    diary_note: str | None = None

    sleep_duration_hours: float | None = None
    sleep_quality: int | None = None
    sleep_regular: bool | None = None

    physical_activity_minutes: int | None = None
    sedentary_minutes: int | None = None
    outdoor_minutes: int | None = None

    had_meaningful_social_interaction: bool | None = None
    routine_stability: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def has_user_text(self) -> bool:
        return bool(self.diary_note and self.diary_note.strip())

    def has_sleep_signal(self) -> bool:
        return (
            self.sleep_duration_hours is not None
            or self.sleep_quality is not None
            or self.sleep_regular is not None
        )

    def has_activity_signal(self) -> bool:
        return (
            self.physical_activity_minutes is not None
            or self.sedentary_minutes is not None
            or self.outdoor_minutes is not None
        )

    def has_social_signal(self) -> bool:
        return self.had_meaningful_social_interaction is not None

    def has_routine_signal(self) -> bool:
        return self.routine_stability is not None