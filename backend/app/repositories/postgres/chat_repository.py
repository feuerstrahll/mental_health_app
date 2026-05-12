from __future__ import annotations

import json
from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class PostgresChatMessageRepository:
    def __init__(self, *, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self._session_maker = session_maker

    async def upsert_session(self, *, session_id: str, user_id: str, state: str) -> None:
        _ = (session_id, user_id, state)

    async def save_user_message(
        self,
        *,
        session_id: str,
        user_id: str,
        text_value: str,
        request_id: str,
    ) -> str:
        message_id = f"chat_{uuid4().hex}"
        payload = {
            "session_id": session_id,
            "request_id": request_id,
            "role": "user",
        }
        query = text(
            """
            INSERT INTO chat_messages (id, user_id, role, content, metadata_jsonb, created_at)
            VALUES (:id, :user_id, :role, :content, CAST(:metadata_jsonb AS jsonb), NOW())
            """
        )
        async with self._session_maker() as session:
            await session.execute(
                query,
                {
                    "id": message_id,
                    "user_id": user_id,
                    "role": "user",
                    "content": text_value,
                    "metadata_jsonb": json.dumps(payload, ensure_ascii=False),
                },
            )
            await session.commit()
        return message_id

    async def save_bot_message(
        self,
        *,
        session_id: str,
        user_id: str,
        text_value: str,
        request_id: str,
        fallback_used: bool,
    ) -> str:
        message_id = f"chat_{uuid4().hex}"
        payload = {
            "session_id": session_id,
            "request_id": request_id,
            "role": "assistant",
            "fallback_used": bool(fallback_used),
        }
        query = text(
            """
            INSERT INTO chat_messages (id, user_id, role, content, metadata_jsonb, created_at)
            VALUES (:id, :user_id, :role, :content, CAST(:metadata_jsonb AS jsonb), NOW())
            """
        )
        async with self._session_maker() as session:
            await session.execute(
                query,
                {
                    "id": message_id,
                    "user_id": user_id,
                    "role": "assistant",
                    "content": text_value,
                    "metadata_jsonb": json.dumps(payload, ensure_ascii=False),
                },
            )
            await session.commit()
        return message_id

    async def get_recent_messages(self, *, user_id: str, session_id: str, limit: int = 12) -> Sequence[dict]:
        query = text(
            """
            SELECT id, user_id, role, content, created_at, metadata_jsonb
            FROM chat_messages
            WHERE user_id = :user_id
              AND COALESCE(metadata_jsonb->>'session_id', '') = :session_id
            ORDER BY created_at DESC
            LIMIT :limit
            """
        )
        async with self._session_maker() as session:
            rows = (await session.execute(query, {"user_id": user_id, "session_id": session_id, "limit": limit})).mappings()
            out: list[dict] = []
            for row in rows:
                metadata = dict(row.get("metadata_jsonb") or {})
                out.append(
                    {
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "role": row["role"],
                        "text": row["content"],
                        "created_at": row["created_at"],
                        "metadata": metadata,
                    }
                )
            return list(reversed(out))

    async def mark_messages_not_current_turn(self, *, user_id: str, request_id: str) -> None:
        query = text(
            """
            UPDATE memory_chunks
            SET is_current_turn = FALSE
            WHERE user_id = :user_id
              AND request_id = :request_id
            """
        )
        async with self._session_maker() as session:
            await session.execute(query, {"user_id": user_id, "request_id": request_id})
            await session.commit()
