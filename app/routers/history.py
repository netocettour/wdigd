from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Entry, User, WeeklyReview
from app.templating import templates
from app.weeks import iso_week_str, parse_priorities, user_today, week_label, week_monday

router = APIRouter()


@router.get("/history")
def history(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hoy = user_today(user)
    current_monday = week_monday(*hoy.isocalendar()[:2])

    first_entry = db.execute(
        select(func.min(Entry.entry_date)).where(Entry.user_id == user.id)
    ).scalar()
    reviews = {
        (r.iso_year, r.iso_week): r
        for r in db.execute(
            select(WeeklyReview).where(WeeklyReview.user_id == user.id)
        ).scalars()
    }
    entry_counts = dict(
        db.execute(
            select(Entry.entry_date, func.count(Entry.id))
            .where(Entry.user_id == user.id)
            .group_by(Entry.entry_date)
        ).all()
    )

    start_monday = current_monday
    if first_entry is not None:
        start_monday = min(start_monday, week_monday(*first_entry.isocalendar()[:2]))
    for iso_year, iso_week in reviews:
        start_monday = min(start_monday, week_monday(iso_year, iso_week))

    weeks = []
    monday = current_monday
    while monday >= start_monday:
        iso = monday.isocalendar()
        review = reviews.get((iso.year, iso.week))
        count = sum(
            n for d, n in entry_counts.items() if monday <= d <= monday + timedelta(days=6)
        )
        if review is None:
            status = "sin sesión"
        elif review.closed_at is not None:
            status = "cerrada"
        else:
            status = "sin cerrar"
        priorities = parse_priorities(review.priorities) if review else []
        weeks.append(
            {
                "iso": iso_week_str(monday),
                "label": week_label(monday),
                "year": monday.year,
                "status": status,
                "count": count,
                "is_current": monday == current_monday,
                "priorities": priorities,
                "name": review.name if review else "",
            }
        )
        monday -= timedelta(days=7)

    return templates.TemplateResponse(request, "pages/history.html", {"weeks": weeks})
