from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.capture import entries_between, entries_for_date
from app.db import get_db
from app.deps import get_current_user
from app.models import DailyNote, User
from app.priorities import priorities_for_week
from app.templating import templates
from app.weeks import DIAS, fecha_larga, monday_of, user_today

router = APIRouter()


def _find_note(db: Session, user: User, day: date) -> DailyNote | None:
    return db.execute(
        select(DailyNote).where(DailyNote.user_id == user.id, DailyNote.note_date == day)
    ).scalar_one_or_none()


def _get_or_create_note(db: Session, user: User, day: date) -> DailyNote:
    """Devuelve la nota del día, creándola si todavía no existe.

    Dos pedidos casi simultáneos del mismo usuario (doble click en "Cerrar el
    día", o el autoguardado de la nota pisándose con el cierre) llegan los dos
    sin encontrar la fila e intentan crearla. El segundo INSERT espera en el
    índice único y falla cuando el primero commitea; el savepoint deja la sesión
    usable para releer la fila que quedó.
    """
    note = _find_note(db, user, day)
    if note is not None:
        return note

    try:
        with db.begin_nested():
            note = DailyNote(user_id=user.id, note_date=day)
            db.add(note)
    except IntegrityError:
        note = _find_note(db, user, day)
        if note is None:
            raise
    return note


def _days_before_today(db: Session, user: User, today: date) -> list[dict]:
    """Bullets de los días anteriores de la misma semana, agrupados por día."""
    monday = monday_of(today)
    if monday == today:
        return []

    days: list[dict] = []
    for entry in entries_between(db, user, monday, today - timedelta(days=1)):
        if not days or days[-1]["date"] != entry.entry_date:
            days.append(
                {
                    "date": entry.entry_date,
                    "day": DIAS[entry.entry_date.weekday()].lower(),
                    "rows": [],
                }
            )
        days[-1]["rows"].append(entry.text)
    return days


@router.get("/today")
def today_page(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = user_today(user)
    iso = today.isocalendar()
    priorities = priorities_for_week(db, user, iso.year, iso.week)
    note = _find_note(db, user, today)

    bullets = entries_for_date(db, user, today)
    logros = sum(1 for b in bullets if b.category == "logro")

    return templates.TemplateResponse(
        request,
        "pages/today.html",
        {
            "user": user,
            "date_label": fecha_larga(today),
            "today_iso": today.isoformat(),
            "bullets": bullets,
            "logros": logros,
            "prev_days": _days_before_today(db, user, today),
            "priorities": priorities,
            "can_align": bool(priorities),
            "note": note.text if note else "",
            "closed": note is not None and note.closed_at is not None,
        },
    )


@router.patch("/today/note")
def save_daily_note(
    text: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _get_or_create_note(db, user, user_today(user))
    note.text = text
    db.commit()
    return Response(status_code=204)


@router.post("/today/close")
def close_day(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _get_or_create_note(db, user, user_today(user))
    note.closed_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse("/today", status_code=303)


@router.post("/today/reopen")
def reopen_day(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _get_or_create_note(db, user, user_today(user))
    note.closed_at = None
    db.commit()
    return RedirectResponse("/today", status_code=303)
