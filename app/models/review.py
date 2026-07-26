from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.entry import Entry

REVIEW_ITEM_KINDS = ("preocupacion", "seguimiento")

achievement_entries = Table(
    "achievement_entries",
    Base.metadata,
    Column("achievement_id", ForeignKey("achievements.id"), primary_key=True),
    Column("entry_id", ForeignKey("entries.id"), primary_key=True),
)


class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "iso_year", "iso_week", name="uq_reviews_user_week"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    iso_year: Mapped[int] = mapped_column(Integer, nullable=False)
    iso_week: Mapped[int] = mapped_column(Integer, nullable=False)
    # Nombre opcional de la semana: una etiqueta para reconocerla en /history.
    name: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    narrative: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    priorities: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True)
    weekly_review_id: Mapped[int] = mapped_column(
        ForeignKey("weekly_reviews.id"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    entries: Mapped[list[Entry]] = relationship(secondary=achievement_entries)


class ReviewItem(Base):
    """Legado: "Preocupaciones y seguimientos" se sacó de /week. El modelo y la
    tabla quedan para no perder lo ya escrito; nada de la app los usa."""

    __tablename__ = "review_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    weekly_review_id: Mapped[int] = mapped_column(
        ForeignKey("weekly_reviews.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(
        SAEnum(*REVIEW_ITEM_KINDS, name="review_item_kind", native_enum=False, length=15),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
