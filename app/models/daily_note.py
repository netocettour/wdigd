from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DailyNote(Base):
    __tablename__ = "daily_notes"
    __table_args__ = (
        UniqueConstraint("user_id", "note_date", name="uq_daily_notes_user_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    note_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
