from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.schemas.wellbeing import WellbeingSignalsRequest


class PostgresWellbeingRepository:
    def __init__(self, *, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def save(self, payload: WellbeingSignalsRequest) -> None:
        signals = payload.signals
        entry_date = payload.client_timestamp.date() if payload.client_timestamp else date.today()
        query = text(
            """
            INSERT INTO wellbeing_records (
                user_id,
                emotion_marker,
                diary_note,
                risk_level,
                created_at,
                entry_date,
                sleep_duration_hours,
                sleep_quality,
                sleep_regularity,
                physical_activity_minutes,
                sedentary_time_minutes,
                outdoor_time_minutes,
                social_connectedness_score,
                routine_regularity
            )
            VALUES (
                :user_id,
                :emotion_marker,
                :diary_note,
                :risk_level,
                NOW(),
                :entry_date,
                :sleep_duration_hours,
                :sleep_quality,
                :sleep_regularity,
                :physical_activity_minutes,
                :sedentary_time_minutes,
                :outdoor_time_minutes,
                :social_connectedness_score,
                :routine_regularity
            )
            """
        )
        async with self._session_maker() as session:
            await session.execute(
                query,
                {
                    "user_id": payload.user_id,
                    "emotion_marker": signals.emotion_marker,
                    "diary_note": signals.diary_note,
                    "risk_level": "low",
                    "entry_date": entry_date,
                    "sleep_duration_hours": signals.sleep_duration_hours,
                    "sleep_quality": str(signals.sleep_quality),
                    "sleep_regularity": str(signals.sleep_regularity),
                    "physical_activity_minutes": float(signals.physical_activity_minutes),
                    "sedentary_time_minutes": float(signals.sedentary_minutes),
                    "outdoor_time_minutes": float(signals.outdoor_minutes),
                    "social_connectedness_score": float(signals.social_connectedness),
                    "routine_regularity": str(signals.routine_regularity),
                },
            )
            await session.commit()

    async def get_recent_by_user(self, user_id: str, limit: int = 14) -> Sequence[dict]:
        query = text(
            """
            SELECT
                user_id,
                entry_date,
                emotion_marker,
                diary_note,
                sleep_duration_hours,
                sleep_quality,
                sleep_regularity,
                physical_activity_minutes,
                sedentary_time_minutes,
                outdoor_time_minutes,
                social_connectedness_score,
                routine_regularity
            FROM wellbeing_records
            WHERE user_id = :user_id
            ORDER BY created_at DESC, id DESC
            LIMIT :limit
            """
        )
        async with self._session_maker() as session:
            rows = (await session.execute(query, {"user_id": user_id, "limit": limit})).mappings()
            out: list[dict] = []
            for row in rows:
                out.append(
                    {
                        "source_id": f"wellbeing:{row.get('entry_date') or row.get('created_at')}",
                        "entry_date": row.get("entry_date"),
                        "emotion_marker": row.get("emotion_marker"),
                        "diary_note": row.get("diary_note"),
                        "sleep_duration_hours": row.get("sleep_duration_hours"),
                        "sleep_quality": row.get("sleep_quality"),
                        "sleep_regularity": row.get("sleep_regularity"),
                        "physical_activity_minutes": row.get("physical_activity_minutes"),
                        "sedentary_time_minutes": row.get("sedentary_time_minutes"),
                        "outdoor_time_minutes": row.get("outdoor_time_minutes"),
                        "social_connectedness_score": row.get("social_connectedness_score"),
                        "routine_regularity": row.get("routine_regularity"),
                    }
                )
            return list(reversed(out))
