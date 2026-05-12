from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import date
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class PostgresDailyCommentRepository:
    def __init__(self, *, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def save_comment(
        self,
        *,
        user_id: str,
        entry_date: date,
        emotion_marker: str | None,
        comment_text: str,
        request_id: str,
    ) -> str:
        comment_id = f"daily_{uuid4().hex}"
        query = text(
            """
            INSERT INTO daily_comments (
                id,
                user_id,
                entry_date,
                emotion_marker,
                comment_text,
                metadata_jsonb,
                created_at
            )
            VALUES (
                :id,
                :user_id,
                :entry_date,
                :emotion_marker,
                :comment_text,
                CAST(:metadata_jsonb AS jsonb),
                NOW()
            )
            """
        )
        async with self._session_maker() as session:
            await session.execute(
                query,
                {
                    "id": comment_id,
                    "user_id": user_id,
                    "entry_date": entry_date,
                    "emotion_marker": emotion_marker,
                    "comment_text": comment_text,
                    "metadata_jsonb": json.dumps({"request_id": request_id}, ensure_ascii=False),
                },
            )
            await session.commit()
        return comment_id

    async def get_recent_comments(self, *, user_id: str, limit: int = 14) -> Sequence[dict]:
        query = text(
            """
            SELECT id, entry_date, emotion_marker, comment_text, created_at, metadata_jsonb
            FROM daily_comments
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit
            """
        )
        async with self._session_maker() as session:
            rows = (await session.execute(query, {"user_id": user_id, "limit": limit})).mappings()
            out: list[dict] = []
            for row in rows:
                out.append(
                    {
                        "id": row["id"],
                        "entry_date": row["entry_date"],
                        "emotion_marker": row["emotion_marker"],
                        "comment_text": row["comment_text"],
                        "created_at": row["created_at"],
                        "metadata": dict(row.get("metadata_jsonb") or {}),
                    }
                )
            return list(reversed(out))
