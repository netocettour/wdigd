"""Búsqueda de usuarios por email.

El email se guarda normalizado (minúsculas, sin espacios), pero la búsqueda
compara igual en minúsculas para tolerar filas viejas o cargadas a mano.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(email) and "@" in email


def find_by_email(db: Session, email: str, *, exclude_id: int | None = None) -> User | None:
    query = select(User).where(func.lower(User.email) == normalize_email(email))
    if exclude_id is not None:
        query = query.where(User.id != exclude_id)
    return db.execute(query).scalar_one_or_none()
