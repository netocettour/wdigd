from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Achievement, Entry, User, WeeklyReview, achievement_entries
from app.templating import templates
from app.week_material import (
    find_review,
    get_or_create_review,
    material_context,
    material_response,
)
from app.weeks import (
    format_iso_week,
    iso_week_str,
    next_iso,
    parse_iso_week,
    parse_priorities,
    prev_iso,
    user_today,
    week_label,
    week_monday,
)

router = APIRouter()


@router.get("/week")
def week_index(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atajo: si la semana anterior quedó sin cerrar, la sesión pendiente es esa."""
    today = user_today(user)
    iso = today.isocalendar()
    prev_year, prev_week = prev_iso(iso.year, iso.week)
    previous = find_review(db, user, prev_year, prev_week)
    if previous is not None and previous.closed_at is None:
        return RedirectResponse(f"/week/{format_iso_week(prev_year, prev_week)}", status_code=303)
    return RedirectResponse(f"/week/{iso_week_str(today)}", status_code=303)


@router.get("/week/{iso_week}")
def week_page(
    iso_week: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_or_create_review(db, user, iso_year, week_number)
    is_current_week = iso_week == iso_week_str(user_today(user))

    context = material_context(db, user, iso_week)
    context.update(
        {
            "review": review,
            "label": week_label(week_monday(iso_year, week_number)),
            "closed": review.closed_at is not None,
            "review_priorities": parse_priorities(review.priorities),
            "prev_iso": format_iso_week(*prev_iso(iso_year, week_number)),
            # No se navega hacia adelante más allá de la semana en curso.
            "next_iso": (
                None if is_current_week else format_iso_week(*next_iso(iso_year, week_number))
            ),
        }
    )
    return templates.TemplateResponse(request, "pages/week.html", context)


@router.patch("/week/{iso_week}")
def week_autosave(
    iso_week: str,
    # None = el campo no vino en este autosave y no se toca.
    name: str | None = Form(None),
    narrative: str | None = Form(None),
    priorities: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_or_create_review(db, user, iso_year, week_number)
    if name is not None:
        review.name = name.strip()
    if narrative is not None:
        review.narrative = narrative
    if priorities is not None:
        review.priorities = priorities
    db.commit()
    return Response(status_code=204)


@router.post("/week/{iso_week}/close")
def week_close(
    iso_week: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_or_create_review(db, user, iso_year, week_number)
    review.closed_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse(f"/week/{iso_week}", status_code=303)


@router.post("/week/{iso_week}/reopen")
def week_reopen(
    iso_week: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_or_create_review(db, user, iso_year, week_number)
    review.closed_at = None
    db.commit()
    return RedirectResponse(f"/week/{iso_week}", status_code=303)


# — Highlights (bloque 3): siempre nacen de un bullet del bloque 1 —

def _own_achievement(db: Session, user: User, achievement_id: int) -> Achievement:
    achievement = db.get(Achievement, achievement_id)
    if achievement is None:
        raise HTTPException(status_code=404)
    review = db.get(WeeklyReview, achievement.weekly_review_id)
    if review is None or review.user_id != user.id:
        raise HTTPException(status_code=404)
    return achievement


def _next_achievement_position(db: Session, review: WeeklyReview) -> int:
    last = db.execute(
        select(func.max(Achievement.position)).where(
            Achievement.weekly_review_id == review.id
        )
    ).scalar()
    return (last or 0) + 1


@router.post("/achievements")
def create_achievement(
    request: Request,
    iso_week: str = Form(...),
    entry_id: int = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_or_create_review(db, user, iso_year, week_number)

    entry = db.get(Entry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404)

    if entry.text:
        achievement = Achievement(
            weekly_review_id=review.id,
            text=entry.text,
            position=_next_achievement_position(db, review),
        )
        achievement.entries.append(entry)
        db.add(achievement)
        db.commit()
    return material_response(request, db, user, iso_week)


@router.patch("/achievements/{achievement_id}")
def update_achievement(
    achievement_id: int,
    text: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    achievement = _own_achievement(db, user, achievement_id)
    if text.strip():
        achievement.text = text.strip()
        db.commit()
    return Response(status_code=204)


@router.delete("/achievements/{achievement_id}")
def delete_achievement(
    achievement_id: int,
    request: Request,
    iso: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    achievement = _own_achievement(db, user, achievement_id)
    db.execute(
        achievement_entries.delete().where(
            achievement_entries.c.achievement_id == achievement.id
        )
    )
    db.delete(achievement)
    db.commit()
    return material_response(request, db, user, iso)
