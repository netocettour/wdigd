from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CalendarAccount(Base):
    """Cuenta de Google conectada. Uno por usuario."""

    __tablename__ = "calendar_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    google_email: Mapped[str] = mapped_column(String(255), nullable=False)
    # Fernet ciphertext; ver app/crypto.py.
    refresh_token_enc: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    sources: Mapped[list["CalendarSource"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
    )


class CalendarSource(Base):
    """Cada calendario individual dentro de la cuenta. El usuario tildea cuáles
    quiere ver en /today."""

    __tablename__ = "calendar_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("calendar_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    google_calendar_id: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(String(255), nullable=False)
    # Hex "#rrggbb" que devuelve Google en calendarList.
    background_color: Mapped[str] = mapped_column(String(7), nullable=False, default="#4d7ec5")
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    account: Mapped["CalendarAccount"] = relationship(back_populates="sources")
