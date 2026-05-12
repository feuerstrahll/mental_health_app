"""Repository for safety_classification_record - audit trail of deterministic classifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class SafetyClassificationRecord:
    """Immutable audit record of SafetyClassifier output."""

    id: str
    request_id: str
    user_id: str
    safety_mode: str
    risk_flags: list[str] | None
    safety_instructions: list[str] | None
    confidence: float
    raw_triggers: dict[str, Any] | None
    latency_ms: int | None
    created_at: datetime


class SafetyClassificationRecordRepository:
    """
    Stores deterministic SafetyClassification outputs for audit trail.

    Allows querying what safety decisions were made, what rules fired, latency metrics.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(
        self,
        *,
        id: str,
        request_id: str,
        user_id: str,
        safety_mode: str,
        risk_flags: list[str] | None = None,
        safety_instructions: list[str] | None = None,
        confidence: float = 1.0,
        raw_triggers: dict[str, Any] | None = None,
        latency_ms: int | None = None,
    ) -> SafetyClassificationRecord:
        """Save a safety classification record."""
        stmt = insert("safety_classification_record").values(
            id=id,
            request_id=request_id,
            user_id=user_id,
            safety_mode=safety_mode,
            risk_flags=risk_flags or [],
            safety_instructions=safety_instructions or [],
            confidence=confidence,
            raw_triggers=raw_triggers or {},
            latency_ms=latency_ms,
        )

        await self._session.execute(stmt)
        await self._session.commit()

        return SafetyClassificationRecord(
            id=id,
            request_id=request_id,
            user_id=user_id,
            safety_mode=safety_mode,
            risk_flags=risk_flags,
            safety_instructions=safety_instructions,
            confidence=confidence,
            raw_triggers=raw_triggers,
            latency_ms=latency_ms,
            created_at=datetime.utcnow(),
        )

    async def get_recent_by_user(
        self, *, user_id: str, limit: int = 50
    ) -> list[SafetyClassificationRecord]:
        """Get recent safety classifications for a user (ordered by created_at DESC)."""
        stmt = (
            select("safety_classification_record")
            .where("safety_classification_record.user_id" == user_id)
            .order_by("safety_classification_record.created_at".desc())
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        return [
            SafetyClassificationRecord(
                id=row.id,
                request_id=row.request_id,
                user_id=row.user_id,
                safety_mode=row.safety_mode,
                risk_flags=row.risk_flags,
                safety_instructions=row.safety_instructions,
                confidence=row.confidence,
                raw_triggers=row.raw_triggers,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
            )
            for row in rows
        ]

    async def get_by_request_id(self, *, request_id: str) -> SafetyClassificationRecord | None:
        """Get safety classification for a specific request."""
        stmt = select("safety_classification_record").where(
            "safety_classification_record.request_id" == request_id
        )

        result = await self._session.execute(stmt)
        row = result.first()

        if not row:
            return None

        return SafetyClassificationRecord(
            id=row.id,
            request_id=row.request_id,
            user_id=row.user_id,
            safety_mode=row.safety_mode,
            risk_flags=row.risk_flags,
            safety_instructions=row.safety_instructions,
            confidence=row.confidence,
            raw_triggers=row.raw_triggers,
            latency_ms=row.latency_ms,
            created_at=row.created_at,
        )

    async def get_crisis_records_by_user(
        self, *, user_id: str, days_back: int = 30, limit: int = 20
    ) -> list[SafetyClassificationRecord]:
        """Get crisis-mode safety classifications for a user (recent audit trail)."""
        from datetime import timedelta

        stmt = (
            select("safety_classification_record")
            .where(
                (
                    "safety_classification_record.user_id" == user_id
                )
                & (
                    "safety_classification_record.safety_mode" == "crisis"
                )
                & (
                    "safety_classification_record.created_at"
                    >= datetime.utcnow() - timedelta(days=days_back)
                )
            )
            .order_by("safety_classification_record.created_at".desc())
            .limit(limit)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        return [
            SafetyClassificationRecord(
                id=row.id,
                request_id=row.request_id,
                user_id=row.user_id,
                safety_mode=row.safety_mode,
                risk_flags=row.risk_flags,
                safety_instructions=row.safety_instructions,
                confidence=row.confidence,
                raw_triggers=row.raw_triggers,
                latency_ms=row.latency_ms,
                created_at=row.created_at,
            )
            for row in rows
        ]
