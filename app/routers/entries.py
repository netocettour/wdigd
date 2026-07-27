from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.capture import (
    entries_for_date,
    next_position,
    parse_capture,
    parse_date,
)
from app.db import get_db
from app.deps import get_current_user
from app.models import CATEGORY_VALUES, Entry, User, achievement_entries
from app.priorities import next_priority, priorities_for_date
from app.templating import templates
from app.week_material import material_response
from app.weeks import user_today

router = APIRouter()

# Desde dónde se editó el bullet: cambia qué fragmento se devuelve.
CTX_WEEK = "week"


def _own_entry(db: Session, user: User, entry_id: int) -> Entry:
    entry = db.get(Entry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404)
    return entry


def today_bullets_response(request: Request, db: Session, user: User):
    today = user_today(user)
    priorities = priorities_for_date(db, user, today)
    return templates.TemplateResponse(
        request,
        "components/bullets_today.html",
        {
            "bullets": entries_for_date(db, user, today),
            "priorities": priorities,
            "can_align": bool(priorities),
        },
    )


def _bullet_response(request: Request, db: Session, user: User, entry: Entry):
    return templates.TemplateResponse(
        request,
        "components/bullet.html",
        {"b": entry, "can_align": bool(priorities_for_date(db, user, entry.entry_date))},
    )


def _updated_response(
    request: Request, db: Session, user: User, entry: Entry, ctx: str, iso: str | None
):
    """En /week cambia el agrupamiento, así que se recarga el material entero."""
    if ctx == CTX_WEEK and iso:
        return material_response(request, db, user, iso)
    return _bullet_response(request, db, user, entry)


@router.post("/entries")
def create_entry(
    request: Request,
    text: str = Form(""),
    entry_date: str = Form(""),
    category: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    lines = parse_capture(text.strip())
    if lines:
        day = parse_date(entry_date, default=user_today(user))
        form_category = category if category in CATEGORY_VALUES else None
        position = next_position(db, user, day)
        for line_text, quick_category in lines:
            db.add(
                Entry(
                    user_id=user.id,
                    entry_date=day,
                    text=line_text,
                    category=quick_category or form_category,
                    position=position,
                )
            )
            position += 1
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


@router.patch("/entries/{entry_id}")
def update_entry(
    entry_id: int,
    request: Request,
    ctx: str = Query("today"),
    iso: str | None = Query(None),
    # None = el campo no vino y no se toca; "" = vino vacío y sí se aplica.
    text: str | None = Form(None),
    category: str | None = Form(None),
    entry_date: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _own_entry(db, user, entry_id)
    if text is not None and text.strip():
        entry.text = text.strip()
    if category is not None:
        entry.category = category if category in CATEGORY_VALUES else None
    if entry_date is not None:
        entry.entry_date = parse_date(entry_date, default=entry.entry_date)
    db.commit()
    return _updated_response(request, db, user, entry, ctx, iso)


@router.post("/entries/{entry_id}/align")
def align_entry(
    entry_id: int,
    request: Request,
    ctx: str = Query("today"),
    iso: str | None = Query(None),
    label: str | None = Form(None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = _own_entry(db, user, entry_id)
    priorities = priorities_for_date(db, user, entry.entry_date)
    if label is None:
        # Fallback sin JS: cada POST cicla a la prioridad siguiente.
        entry.priority_label = next_priority(entry.priority_label, priorities)
    else:
        # El cliente cicla la etiqueta y confirma la elegida (debounce de 1.7s).
        entry.priority_label = label.strip() if label.strip() in priorities else None
    db.commit()
    return _updated_response(request, db, user, entry, ctx, iso)


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
    # 200 con cuerpo vacío: htmx reemplaza el bullet por nada. Un 204 no swapea.
    return Response(content="")
