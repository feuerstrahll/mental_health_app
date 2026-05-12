from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text, text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.wellbeing_record import Base


class UserMemoryEmbedding(Base):
    __tablename__ = "user_memory_embeddings"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    memory_chunk_id: Mapped[str] = mapped_column(String(96), index=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    date: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    text: Mapped[str] = mapped_column(Text(), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    dim: Mapped[int] = mapped_column(Integer(), nullable=False)
    metadata_jsonb: Mapped[dict] = mapped_column(JSON(), default=dict)
    # Stored as text in ORM model to avoid pgvector ORM dependency in app code.
    embedding: Mapped[str] = mapped_column(Text(), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sql_text("CURRENT_TIMESTAMP"),
    )
