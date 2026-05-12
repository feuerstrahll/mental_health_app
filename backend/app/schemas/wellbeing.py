from datetime import datetime
from pydantic import BaseModel, Field


class WellbeingSignals(BaseModel):
    emotion_marker: str = Field(min_length=1, max_length=50)
    diary_note: str | None = Field(default=None, max_length=500)
    sleep_duration_hours: float = Field(ge=0, le=24)
    sleep_regularity: int = Field(ge=1, le=5)
    sleep_quality: int = Field(ge=1, le=5)
    physical_activity_minutes: int = Field(ge=0, le=1440)
    sedentary_minutes: int = Field(ge=0, le=1440)
    outdoor_minutes: int = Field(ge=0, le=1440)
    social_connectedness: int = Field(ge=1, le=5)
    routine_regularity: int = Field(ge=1, le=5)


class WellbeingSignalsRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    client_timestamp: datetime | None = None
    signals: WellbeingSignals
