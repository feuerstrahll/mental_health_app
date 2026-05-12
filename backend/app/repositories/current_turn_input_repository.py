"""Repository for current_turn_input - MVP structured input capture."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, AsyncIterator

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class CurrentTurnInputRecord:
    """Immutable record of a single turn's structured input."""

    id: str
    user_id: str
    session_id: str | None
    emotion_marker: str
    user_text: str | None
    sleep_hours: float | None
    sleep_quality: int | None
    activity_minutes: int | None
    social_connection: int | None
    input_row_id: str
    created_at: datetime


class CurrentTurnInputRepository:
    """
    Saves MVP form input: emotion_marker, optional text, and daily signals.

    Each input row gets a unique input_row_id which links back from
    conversation_message and daily_comment records via FK.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(
        self,
        *,
        id: str,
        user_id: str,
        session_id: str | None,
        emotion_marker: str,
        user_text: str | None = None,
        sleep_hours: float | None = None,
        sleep_quality: int | None = None,
        activity_minutes: int | None = None,
        social_connection: int | None = None,
        input_row_id: str,
    ) -> CurrentTurnInputRecord:
        """Save a current_turn_input record and return it."""
        stmt = insert("current_turn_input").values(
            id=id,
            user_id=user_id,
            session_id=session_id,
            emotion_marker=emotion_marker,
            user_text=user_text,
            sleep_hours=sleep_hours,
            sleep_quality=sleep_quality,
            activity_minutes=activity_minutes,
            social_connection=social_connection,
            input_row_id=input_row_id,
        )

        await self._session.execute(stmt)
        await self._session.commit()

        return CurrentTurnInputRecord(
            id=id,
            user_id=user_id,
            session_id=session_id,
            emotion_marker=emotion_marker,
            user_text=user_text,
            sleep_hours=sleep_hours,
            sleep_quality=sleep_quality,
            activity_minutes=activity_minutes,
            social_connection=social_connection,
            input_row_id=input_row_id,
            created_at=datetime.utcnow(),
        )

    async def get_by_input_row_id(self, *, input_row_id: str) -> CurrentTurnInputRecord | None:
        """Get record by mobile-generated input_row_id."""
        stmt = select("current_turn_input").where(
            "current_turn_input.input_row_id" == input_row_id
        )

        result = await self._session.execute(stmt)
        row = result.first()

        if not row:
            return None

        return CurrentTurnInputRecord(
            id=row.id,
            user_id=row.user_id,
            session_id=row.session_id,
            emotion_marker=row.emotion_marker,
            user_text=row.user_text,
            sleep_hours=row.sleep_hours,
            sleep_quality=row.sleep_quality,
            activity_minutes=row.activity_minutes,
            social_connection=row.social_connection,
            input_row_id=row.input_row_id,
            created_at=row.created_at,
        )

    async def get_recent_by_user(
        self, *, user_id: str, limit: int = 30
    ) -> AsyncIterator[CurrentTurnInputRecord]:
        """Stream recent input records for a user (ordered by created_at DESC)."""
        stmt = (
            select("current_turn_input")
            .where("current_turn_input.user_id" == user_id)
            .order_by("current_turn_input.created_at".desc())
            .limit(limit)
        )

        result = await self._session.stream(stmt)

        async for row in result:
            yield CurrentTurnInputRecord(
                id=row.id,
                user_id=row.user_id,
                session_id=row.session_id,
                emotion_marker=row.emotion_marker,
                user_text=row.user_text,
                sleep_hours=row.sleep_hours,
                sleep_quality=row.sleep_quality,
                activity_minutes=row.activity_minutes,
                social_connection=row.social_connection,
                input_row_id=row.input_row_id,
                created_at=row.created_at,
            )
