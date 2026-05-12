from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Sequence

from app.services.context.recent_context_summary_service import ContextDailyEntry, ContextMemory


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(str(value).strip().split())


@dataclass(frozen=True)
class UserMemoryChunk:
    id: str
    user_id: str
    date: str
    source_type: str  # chat_message | daily_comment | wellbeing_record | legacy_embedding
    source_id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    is_current_turn: bool = False
    request_id: str | None = None


class UserMemoryChunkService:
    """Build short, date-preserving memory chunks for retrieval."""

    def build_chunks(
        self,
        *,
        user_id: str,
        daily_entries: Sequence[ContextDailyEntry],
        chat_memories: Sequence[ContextMemory],
        daily_comments: Sequence[ContextMemory] | None = None,
    ) -> list[UserMemoryChunk]:
        chunks: list[UserMemoryChunk] = []

        for entry in daily_entries:
            chunks.extend(self._chunks_from_daily_entry(user_id=user_id, entry=entry))

        for memory in chat_memories:
            chunk = self._chunk_from_context_memory(user_id=user_id, memory=memory, source_type="chat_message")
            if chunk is not None:
                chunks.append(chunk)

        for comment in daily_comments or []:
            chunk = self._chunk_from_context_memory(user_id=user_id, memory=comment, source_type="daily_comment")
            if chunk is not None:
                chunks.append(chunk)

        # Stable order helps deterministic tests and deterministic embedding writes.
        chunks.sort(key=lambda item: (item.date, item.source_type, item.id))
        return chunks

    def _chunks_from_daily_entry(self, *, user_id: str, entry: ContextDailyEntry) -> list[UserMemoryChunk]:
        entry_iso = entry.entry_date.isoformat()

        metadata = {
            "emotion": _clean_text(entry.emotion_marker) or None,
            "sleep_duration": entry.sleep_duration_hours,
            "sleep_quality": entry.sleep_quality,
            "sleep_regularity": entry.sleep_regularity,
            "physical_activity": entry.physical_activity_minutes,
            "sedentary_time": entry.sedentary_time_minutes,
            "outdoor_time": entry.outdoor_time_minutes,
            "social_connectedness": entry.social_connectedness_score,
            "routine_regularity": entry.routine_regularity,
        }
        metadata = {key: value for key, value in metadata.items() if value is not None}

        diary_text = _clean_text(entry.diary_note)
        checkin_text = self._build_checkin_summary_text(entry=entry)

        chunks: list[UserMemoryChunk] = []
        if diary_text:
            chunks.append(
                self._build_chunk(
                    user_id=user_id,
                    date_iso=entry_iso,
                    source_type="wellbeing_record",
                    source_id=str(entry.metadata.get("source_id") or f"{entry_iso}:diary"),
                    text=f"Date: {entry_iso}. Diary: {diary_text}",
                    metadata=metadata,
                )
            )

        # Always keep check-in chunk, even if diary is empty.
        chunks.append(
            self._build_chunk(
                user_id=user_id,
                date_iso=entry_iso,
                source_type="wellbeing_record",
                source_id=str(entry.metadata.get("source_id") or f"{entry_iso}:checkin"),
                text=checkin_text,
                metadata=metadata,
            )
        )
        return chunks

    def _build_checkin_summary_text(self, *, entry: ContextDailyEntry) -> str:
        entry_iso = entry.entry_date.isoformat()
        parts = [f"Date: {entry_iso}."]
        if entry.emotion_marker:
            parts.append(f"Emotion: {_clean_text(entry.emotion_marker)}.")
        if entry.sleep_duration_hours is not None:
            sleep_part = f"Sleep: {entry.sleep_duration_hours:g}h"
            if entry.sleep_quality:
                sleep_part += f", quality {entry.sleep_quality}"
            parts.append(f"{sleep_part}.")
        if entry.sleep_regularity:
            parts.append(f"Sleep regularity: {_clean_text(str(entry.sleep_regularity))}.")
        if entry.physical_activity_minutes is not None:
            parts.append(f"Physical activity: {entry.physical_activity_minutes:g} min.")
        if entry.sedentary_time_minutes is not None:
            parts.append(f"Sedentary time: {entry.sedentary_time_minutes:g} min.")
        if entry.outdoor_time_minutes is not None:
            parts.append(f"Outdoor time: {entry.outdoor_time_minutes:g} min.")
        if entry.social_connectedness_score is not None:
            parts.append(f"Social connection: {entry.social_connectedness_score:g}/5.")
        if entry.routine_regularity:
            parts.append(f"Routine: {_clean_text(str(entry.routine_regularity))}.")
        if entry.diary_note:
            parts.append(f"Diary: {_clean_text(entry.diary_note)}.")
        return " ".join(parts)

    def _chunk_from_context_memory(
        self,
        *,
        user_id: str,
        memory: ContextMemory,
        source_type: str,
    ) -> UserMemoryChunk | None:
        text = _clean_text(memory.text)
        if not text:
            return None
        memory_date = memory.entry_date or date.today()
        date_iso = memory_date.isoformat()
        return self._build_chunk(
            user_id=user_id,
            date_iso=date_iso,
            source_type=source_type,
            source_id=str(memory.metadata.get("source_id") or f"{date_iso}:{source_type}"),
            text=f"Date: {date_iso}. {text}",
            metadata=dict(memory.metadata or {}),
            is_current_turn=bool(memory.metadata.get("is_current_turn", False)),
            request_id=str(memory.metadata.get("request_id")) if memory.metadata.get("request_id") else None,
        )

    def _build_chunk(
        self,
        *,
        user_id: str,
        date_iso: str,
        source_type: str,
        source_id: str,
        text: str,
        metadata: dict[str, Any],
        is_current_turn: bool = False,
        request_id: str | None = None,
    ) -> UserMemoryChunk:
        norm_metadata = self._normalize_metadata(metadata)
        base = f"{user_id}|{date_iso}|{source_type}|{source_id}|{text}"
        chunk_id = hashlib.sha1(base.encode("utf-8")).hexdigest()
        content_hash = self._content_hash(text=text, metadata=norm_metadata)
        return UserMemoryChunk(
            id=chunk_id,
            user_id=user_id,
            date=date_iso,
            source_type=source_type,
            source_id=source_id,
            text=text,
            metadata=norm_metadata,
            content_hash=content_hash,
            is_current_turn=is_current_turn,
            request_id=request_id,
        )

    def _content_hash(self, *, text: str, metadata: dict[str, Any]) -> str:
        raw = json.dumps({"text": text, "metadata": metadata}, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _normalize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                normalized[key] = value
            else:
                normalized[key] = str(value)
        return normalized
