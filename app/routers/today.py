from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import DailyNote, Entry, User
from app.priorities import priorities_for_week
from app.templating import templates
from app.weeks import DIAS, fecha_larga, user_today, week_monday

router = APIRouter()


@router.get("/today")
def today(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hoy = user_today(user)
    iso = hoy.isocalendar()
    monday = week_monday(iso.year, iso.week)

    bullets = list(
        db.execute(
            select(Entry)
            .where(Entry.user_id == user.id, Entry.entry_date == hoy)
            .order_by(Entry.position, Entry.id)
        ).scalars()
    )

    previous = list(
        db.execute(
            select(Entry)
            .where(
                Entry.user_id == user.id,
                Entry.entry_date >= monday,
                Entry.entry_date < hoy,
            )
            .order_by(Entry.entry_date, Entry.position, Entry.id)
        ).scalars()
    )
    prev_days: list[dict] = []
    for e in previous:
        if not prev_days or prev_days[-1]["date"] != e.entry_date:
            prev_days.append(
                {"date": e.entry_date, "day": DIAS[e.entry_date.weekday()].lower(), "items": []}
            )
        prev_days[-1]["items"].append(e.text)

    prioridades = priorities_for_week(db, user, iso.year, iso.week)

    note = db.execute(
        select(DailyNote).where(DailyNote.user_id == user.id, DailyNote.note_date == hoy)
    ).scalar_one_or_none()

    return templates.TemplateResponse(
        request,
        "pages/today.html",
        {
            "user": user,
            "fecha": fecha_larga(hoy),
            "today_iso": hoy.isoformat(),
            "bullets": bullets,
            "prev_days": prev_days,
            "prioridades": prioridades,
            "can_align": bool(prioridades),
            "note": note.text if note else "",
            "closed": note is not None and note.closed_at is not None,
        },
    )


def _get_or_create_note(db: Session, user: User) -> DailyNote:
    hoy = user_today(user)
    note = db.execute(
        select(DailyNote).where(DailyNote.user_id == user.id, DailyNote.note_date == hoy)
    ).scalar_one_or_none()
    if note is None:
        note = DailyNote(user_id=user.id, note_date=hoy)
        db.add(note)
        db.flush()
    return note


@router.patch("/today/note")
async def save_daily_note(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    text = str(form.get("text", ""))
    hoy = user_today(user)
    note = db.execute(
        select(DailyNote).where(DailyNote.user_id == user.id, DailyNote.note_date == hoy)
    ).scalar_one_or_none()
    if note is None:
        note = DailyNote(user_id=user.id, note_date=hoy, text=text)
        db.add(note)
    else:
        note.text = text
    db.commit()
    return Response(status_code=204)


@router.post("/today/close")
def close_day(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _get_or_create_note(db, user)
    note.closed_at = datetime.now(timezone.utc)
    db.commit()
    return RedirectResponse("/today", status_code=303)


@router.post("/today/reopen")
def reopen_day(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    note = _get_or_create_note(db, user)
    note.closed_at = None
    db.commit()
    return RedirectResponse("/today", status_code=303)
