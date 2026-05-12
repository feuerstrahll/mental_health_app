from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.wellbeing_record import Base


class DailyComment(Base):
    __tablename__ = "daily_comments"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    entry_date: Mapped[date] = mapped_column(Date(), nullable=False)
    emotion_marker: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comment_text: Mapped[str] = mapped_column(Text(), nullable=False)
    metadata_jsonb: Mapped[dict] = mapped_column(JSON(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
