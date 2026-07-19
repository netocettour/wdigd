"""Prioridades vigentes de una semana y alineación de bullets con ellas.

En los prototipos, el "tema" de un bullet es una de las prioridades que el
usuario definió el domingo anterior. Esas prioridades salen de la última review
cerrada previa a la semana en cuestión.
"""

from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.models import User, WeeklyReview
from app.weeks import parse_priorities, prev_iso


def review_in_effect(
    db: Session, user: User, iso_year: int, iso_week: int
) -> WeeklyReview | None:
    """Review cuyas prioridades rigen esta semana: la de la semana anterior si
    está cerrada; si no, la última cerrada antes de esta semana."""
    prev_year, prev_week = prev_iso(iso_year, iso_week)
    previous = db.execute(
        select(WeeklyReview).where(
            WeeklyReview.user_id == user.id,
            WeeklyReview.iso_year == prev_year,
            WeeklyReview.iso_week == prev_week,
        )
    ).scalar_one_or_none()
    if previous is not None and previous.closed_at is not None:
        return previous
    return db.execute(
        select(WeeklyReview)
        .where(
            WeeklyReview.user_id == user.id,
            WeeklyReview.closed_at.is_not(None),
            or_(
                WeeklyReview.iso_year < iso_year,
                and_(
                    WeeklyReview.iso_year == iso_year,
                    WeeklyReview.iso_week < iso_week,
                ),
            ),
        )
        .order_by(WeeklyReview.iso_year.desc(), WeeklyReview.iso_week.desc())
    ).scalars().first()


def priorities_for_week(db: Session, user: User, iso_year: int, iso_week: int) -> list[str]:
    review = review_in_effect(db, user, iso_year, iso_week)
    return parse_priorities(review.priorities) if review is not None else []


def priorities_for_date(db: Session, user: User, d: date) -> list[str]:
    iso = d.isocalendar()
    return priorities_for_week(db, user, iso.year, iso.week)


def next_priority(current: str | None, priorities: list[str]) -> str | None:
    """Ciclo del botón 'alinear con prioridades': null → primera → … → última → null."""
    if not priorities:
        return None
    try:
        idx = priorities.index(current) if current is not None else -1
    except ValueError:
        idx = -1
    return priorities[idx + 1] if idx + 1 < len(priorities) else None
