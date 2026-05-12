from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.wellbeing_record import Base


class MemoryChunk(Base):
    __tablename__ = "memory_chunks"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    text_value: Mapped[str] = mapped_column("text", Text(), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    importance_score: Mapped[float | None] = mapped_column(Float(), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_current_turn: Mapped[bool] = mapped_column(Boolean(), nullable=False, server_default=text("false"))
    request_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    metadata_jsonb: Mapped[dict] = mapped_column(JSON(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
