from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import CATEGORY_VALUES, Entry, User, achievement_entries
from app.priorities import next_priority, priorities_for_date
from app.templating import templates
from app.weeks import user_today

router = APIRouter()

QUICK_COMMANDS = {
    "/l": "logro",
    "/a": "avance",
    "/d": "desbloqueo",
}


def _parse_quick_command(text: str) -> tuple[str, str | None]:
    lower = text.lower()
    for cmd, category in QUICK_COMMANDS.items():
        if lower.startswith(cmd + " "):
            return text[len(cmd):].strip(), category
        if lower.endswith(" " + cmd):
            return text[:-len(cmd)].strip(), category
    return text, None


def _own_entry(db: Session, user: User, entry_id: int) -> Entry:
    entry = db.get(Entry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404)
    return entry


def _next_position(db: Session, user: User, entry_date: date) -> int:
    current = db.execute(
        select(func.max(Entry.position)).where(
            Entry.user_id == user.id, Entry.entry_date == entry_date
        )
    ).scalar()
    return (current or 0) + 1


def today_bullets_response(request: Request, db: Session, user: User):
    hoy = user_today(user)
    bullets = list(
        db.execute(
            select(Entry)
            .where(Entry.user_id == user.id, Entry.entry_date == hoy)
            .order_by(Entry.position, Entry.id)
        ).scalars()
    )
    prioridades = priorities_for_date(db, user, hoy)
    return templates.TemplateResponse(
        request,
        "components/bullets_today.html",
        {"bullets": bullets, "prioridades": prioridades, "can_align": bool(prioridades)},
    )


def _bullet_response(request: Request, db: Session, user: User, entry: Entry):
    return templates.TemplateResponse(
        request,
        "components/bullet.html",
        {"b": entry, "can_align": bool(priorities_for_date(db, user, entry.entry_date))},
    )


@router.post("/entries")
async def create_entry(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    form = await request.form()
    text = str(form.get("text", "")).strip()
    if text:
        text, quick_cat = _parse_quick_command(text)
        category = quick_cat or str(form.get("category", "")) or None
        if category not in CATEGORY_VALUES:
            category = None
        entry_date = user_today(user)
        raw_date = str(form.get("entry_date", "")).strip()
        if raw_date:
            try:
                entry_date = date.fromisoformat(raw_date)
            except ValueError:
                pass
        entry = Entry(
            user_id=user.id,
            entry_date=entry_date,
            text=text,
            category=category,
            position=_next_position(db, user, entry_date),
        )
        db.add(entry)
        db.commit()
    return today_bullets_response(request, db, user)


@router.get("/entries/{entry_id}/edit")
def edit_entry_form(
    entry_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _own_entry(db, user, entry_id)
    return templates.TemplateResponse(request, "components/bullet_edit.html", {"b": entry})


def _week_or_bullet(request: Request, db: Session, user: User, entry: Entry, ctx: str, iso):
    if ctx == "week" and iso:
        from app.routers.week import material_response

        return material_response(request, db, user, iso)
    return _bullet_response(request, db, user, entry)


@router.patch("/entries/{entry_id}")
async def update_entry(
    entry_id: int,
    request: Request,
    ctx: str = Query("today"),
    iso: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _own_entry(db, user, entry_id)
    form = await request.form()
    if "text" in form:
        text = str(form["text"]).strip()
        if text:
            entry.text = text
    if "category" in form:
        value = str(form["category"])
        entry.category = value if value in CATEGORY_VALUES else None
    if "entry_date" in form:
        try:
            entry.entry_date = date.fromisoformat(str(form["entry_date"]))
        except ValueError:
            pass
    db.commit()
    return _week_or_bullet(request, db, user, entry, ctx, iso)


@router.post("/entries/{entry_id}/align")
async def align_entry(
    entry_id: int,
    request: Request,
    ctx: str = Query("today"),
    iso: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _own_entry(db, user, entry_id)
    priorities = priorities_for_date(db, user, entry.entry_date)
    form = await request.form()
    if "label" in form:
        # el cliente cicla la etiqueta y confirma la elegida (debounce de 1.7s)
        label = str(form["label"]).strip()
        entry.priority_label = label if label in priorities else None
    else:
        # fallback sin JS: ciclar a la siguiente prioridad
        entry.priority_label = next_priority(entry.priority_label, priorities)
    db.commit()
    return _week_or_bullet(request, db, user, entry, ctx, iso)


@router.delete("/entries/{entry_id}")
def delete_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _own_entry(db, user, entry_id)
    db.execute(
        achievement_entries.delete().where(achievement_entries.c.entry_id == entry.id)
    )
    db.delete(entry)
    db.commit()
    return Response(content="")
