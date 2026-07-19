from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

# Categorías tal como aparecen en los prototipos (docs/designs)
CATEGORY_VALUES = ("logro", "avance", "desbloqueo")
CATEGORY_LABELS = {"logro": "Logro", "avance": "Avance", "desbloqueo": "Desbloqueo"}

# Construcción vs reacción (para las observaciones neutras)
CONSTRUCTION_CATEGORIES = ("logro", "avance")


class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    entry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(
        SAEnum(*CATEGORY_VALUES, name="entry_category", native_enum=False, length=12),
        nullable=True,
    )
    # Alineación con una prioridad de la semana (texto libre de la review anterior).
    priority_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
