from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Entry, User, WeeklyReview
from app.templating import templates
from app.weeks import (
    DAYS_IN_WEEK,
    iso_week_str,
    monday_of,
    parse_priorities,
    user_today,
    week_label,
    week_monday,
)

router = APIRouter()

STATUS_SIN_SESION = "sin sesión"
STATUS_CERRADA = "cerrada"
STATUS_SIN_CERRAR = "sin cerrar"


def _bullets_per_week(db: Session, user: User) -> dict[date, int]:
    rows = db.execute(
        select(Entry.entry_date, func.count(Entry.id))
        .where(Entry.user_id == user.id)
        .group_by(Entry.entry_date)
    ).all()
    per_week: dict[date, int] = {}
    for entry_date, count in rows:
        monday = monday_of(entry_date)
        per_week[monday] = per_week.get(monday, 0) + count
    return per_week


def _status(review: WeeklyReview | None) -> str:
    if review is None:
        return STATUS_SIN_SESION
    return STATUS_CERRADA if review.closed_at is not None else STATUS_SIN_CERRAR


@router.get("/history")
def history(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_monday = monday_of(user_today(user))

    reviews = {
        (r.iso_year, r.iso_week): r
        for r in db.execute(
            select(WeeklyReview).where(WeeklyReview.user_id == user.id)
        ).scalars()
    }
    bullets_per_week = _bullets_per_week(db, user)

    # La lista arranca en la semana en curso y baja hasta la más vieja con material.
    start_monday = min(
        [current_monday]
        + list(bullets_per_week)
        + [week_monday(iso_year, iso_week) for iso_year, iso_week in reviews]
    )

    weeks = []
    monday = current_monday
    while monday >= start_monday:
        iso = monday.isocalendar()
        review = reviews.get((iso.year, iso.week))
        weeks.append(
            {
                "iso": iso_week_str(monday),
                "label": week_label(monday),
                "year": monday.year,
                "status": _status(review),
                "count": bullets_per_week.get(monday, 0),
                "is_current": monday == current_monday,
                "priorities": parse_priorities(review.priorities) if review else [],
                "name": review.name if review else "",
            }
        )
        monday -= timedelta(days=DAYS_IN_WEEK)

    return templates.TemplateResponse(request, "pages/history.html", {"weeks": weeks})
