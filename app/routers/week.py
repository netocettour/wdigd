from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db import get_db
from app.deps import get_current_user
from app.models import (
    CATEGORY_LABELS,
    REVIEW_ITEM_KINDS,
    Achievement,
    Entry,
    ReviewItem,
    User,
    WeeklyReview,
    achievement_entries,
)
from app.observations import recurrence_notes, week_observations
from app.priorities import priorities_for_week
from app.templating import templates
from app.weeks import (
    DIAS_ABBR,
    iso_week_str,
    next_iso,
    parse_iso_week,
    prev_iso,
    user_today,
    week_label,
    week_monday,
)

router = APIRouter()

FUERA = "Fuera de las prioridades de la semana"


def get_review(
    db: Session, user: User, iso_year: int, iso_week: int, create: bool = False
) -> WeeklyReview | None:
    review = db.execute(
        select(WeeklyReview).where(
            WeeklyReview.user_id == user.id,
            WeeklyReview.iso_year == iso_year,
            WeeklyReview.iso_week == iso_week,
        )
    ).scalar_one_or_none()
    if review is None and create:
        review = WeeklyReview(user_id=user.id, iso_year=iso_year, iso_week=iso_week)
        db.add(review)
        db.commit()
    return review


def _week_entries(db: Session, user: User, monday: date) -> list[Entry]:
    return list(
        db.execute(
            select(Entry)
            .where(
                Entry.user_id == user.id,
                Entry.entry_date >= monday,
                Entry.entry_date <= monday + timedelta(days=6),
            )
            .order_by(Entry.entry_date, Entry.position, Entry.id)
        ).scalars()
    )


def _material_context(request: Request, db: Session, user: User, iso: str) -> dict:
    iso_year, iso_week = parse_iso_week(iso)
    monday = week_monday(iso_year, iso_week)
    review = get_review(db, user, iso_year, iso_week)
    editable = review is None or review.closed_at is None
    entries = _week_entries(db, user, monday)
    priorities = priorities_for_week(db, user, iso_year, iso_week)

    promoted: dict[int, int] = {}
    achievements = []
    if review is not None:
        achs = list(
            db.execute(
                select(Achievement)
                .options(joinedload(Achievement.entries))
                .where(Achievement.weekly_review_id == review.id)
                .order_by(Achievement.position, Achievement.id)
            )
            .unique()
            .scalars()
        )
        for a in achs:
            temas = sorted({e.priority_label for e in a.entries if e.priority_label})
            for e in a.entries:
                promoted[e.id] = a.id
            achievements.append(
                {"id": a.id, "text": a.text, "temas": ", ".join(temas) or "Fuera de prioridades"}
            )

    def make_item(e: Entry, in_priority_group: bool) -> dict:
        uncat = e.category is None
        return {
            "id": e.id,
            "text": e.text,
            "day_abbr": DIAS_ABBR[e.entry_date.weekday()],
            "category_label": CATEGORY_LABELS.get(e.category, ""),
            "priority_label": e.priority_label,
            "promoted": e.id in promoted,
            "achievement_id": promoted.get(e.id),
            "show_chips": editable and uncat and in_priority_group,
            "show_cat_text": (not uncat) and in_priority_group,
            "show_align": editable and not in_priority_group,
        }

    # Grupos: primero las prioridades vigentes que tienen bullets (en su orden),
    # después cualquier etiqueta suelta, y al final los que quedaron fuera.
    groups = []
    used = set()
    for label in priorities:
        items = [e for e in entries if e.priority_label == label]
        if items:
            used.add(label)
            groups.append(
                {"name": label, "is_fuera": False, "items": [make_item(e, True) for e in items]}
            )
    leftover_labels = sorted(
        {e.priority_label for e in entries if e.priority_label and e.priority_label not in used},
        key=str.lower,
    )
    for label in leftover_labels:
        items = [e for e in entries if e.priority_label == label]
        groups.append(
            {"name": label, "is_fuera": False, "items": [make_item(e, True) for e in items]}
        )
    fuera = [e for e in entries if not e.priority_label]
    if fuera:
        groups.append(
            {"name": FUERA, "is_fuera": True, "items": [make_item(e, False) for e in fuera]}
        )

    return {
        "iso": iso,
        "editable": editable,
        "groups": groups,
        "achievements": achievements,
        "priorities": priorities,
        "can_align": bool(priorities),
        "obs": week_observations(db, user, iso_year, iso_week, entries),
    }


def material_response(request: Request, db: Session, user: User, iso: str):
    return templates.TemplateResponse(
        request, "components/week_material.html", _material_context(request, db, user, iso)
    )


def _items_context(db: Session, user: User, iso: str) -> dict:
    iso_year, iso_week = parse_iso_week(iso)
    review = get_review(db, user, iso_year, iso_week)
    editable = review is None or review.closed_at is None
    items: list[ReviewItem] = []
    if review is not None:
        items = list(
            db.execute(
                select(ReviewItem)
                .where(ReviewItem.weekly_review_id == review.id)
                .order_by(ReviewItem.position, ReviewItem.id)
            ).scalars()
        )
    notes = recurrence_notes(db, user, review, items) if review is not None else {}

    def col(kind: str):
        return [
            {"id": it.id, "text": it.text, "note": notes.get(it.id)}
            for it in items
            if it.kind == kind
        ]

    return {
        "iso": iso,
        "editable": editable,
        "cols": [
            {
                "kind": "preocupacion",
                "label": "Preocupaciones",
                "prompt": "¿De qué tenés miedo esta semana?",
                "items": col("preocupacion"),
            },
            {
                "kind": "seguimiento",
                "label": "Seguimientos",
                "prompt": "Cosas que hay que estarles atrás.",
                "items": col("seguimiento"),
            },
        ],
    }


def _items_response(request: Request, db: Session, user: User, iso: str):
    return templates.TemplateResponse(
        request, "components/review_items.html", _items_context(db, user, iso)
    )


@router.get("/week")
def week_index(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hoy = user_today(user)
    current_iso = iso_week_str(hoy)
    iso = hoy.isocalendar()
    prev_year, prev_week = prev_iso(iso.year, iso.week)
    prev_review = get_review(db, user, prev_year, prev_week)
    if prev_review is not None and prev_review.closed_at is None:
        return RedirectResponse(f"/week/{prev_year}-W{prev_week:02d}", status_code=303)
    return RedirectResponse(f"/week/{current_iso}", status_code=303)


@router.get("/week/{iso_week}")
def week_page(
    iso_week: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_review(db, user, iso_year, week_number, create=True)
    monday = week_monday(iso_year, week_number)
    current_iso = iso_week_str(user_today(user))

    context = _material_context(request, db, user, iso_week)
    context.update(_items_context(db, user, iso_week))
    context.update(
        {
            "review": review,
            "label": week_label(monday),
            "closed": review.closed_at is not None,
            "prev_iso": "%d-W%02d" % prev_iso(iso_year, week_number),
            "next_iso": (
                "%d-W%02d" % next_iso(iso_year, week_number)
                if iso_week != current_iso
                else None
            ),
        }
    )
    return templates.TemplateResponse(request, "pages/week.html", context)


@router.patch("/week/{iso_week}")
async def week_autosave(
    iso_week: str,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_review(db, user, iso_year, week_number, create=True)
    form = await request.form()
    if "narrative" in form:
        review.narrative = str(form["narrative"])
    if "priorities" in form:
        review.priorities = str(form["priorities"])
    db.commit()
    return Response(status_code=204)


@router.post("/week/{iso_week}/close")
def week_close(
    iso_week: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_review(db, user, iso_year, week_number, create=True)
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
    review = get_review(db, user, iso_year, week_number, create=True)
    review.closed_at = None
    db.commit()
    return RedirectResponse(f"/week/{iso_week}", status_code=303)


def _own_achievement(db: Session, user: User, achievement_id: int) -> Achievement:
    achievement = db.get(Achievement, achievement_id)
    if achievement is None:
        raise HTTPException(status_code=404)
    review = db.get(WeeklyReview, achievement.weekly_review_id)
    if review is None or review.user_id != user.id:
        raise HTTPException(status_code=404)
    return achievement


@router.post("/achievements")
def create_achievement(
    request: Request,
    iso_week: str = Form(...),
    entry_id: int = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_review(db, user, iso_year, week_number, create=True)

    entry = db.get(Entry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404)

    if entry.text:
        position = (
            db.execute(
                select(func.max(Achievement.position)).where(
                    Achievement.weekly_review_id == review.id
                )
            ).scalar()
            or 0
        ) + 1
        achievement = Achievement(weekly_review_id=review.id, text=entry.text, position=position)
        achievement.entries.append(entry)
        db.add(achievement)
        db.commit()
    return material_response(request, db, user, iso_week)


@router.patch("/achievements/{achievement_id}")
async def update_achievement(
    achievement_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    achievement = _own_achievement(db, user, achievement_id)
    form = await request.form()
    text = str(form.get("text", "")).strip()
    if text:
        achievement.text = text
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


def _own_item(db: Session, user: User, item_id: int) -> ReviewItem:
    item = db.get(ReviewItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404)
    return item


@router.post("/review-items")
def create_review_item(
    request: Request,
    iso_week: str = Form(...),
    kind: str = Form(...),
    text: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if kind not in REVIEW_ITEM_KINDS:
        raise HTTPException(status_code=400)
    iso_year, week_number = parse_iso_week(iso_week)
    review = get_review(db, user, iso_year, week_number, create=True)
    text = text.strip()
    if text:
        position = (
            db.execute(
                select(func.max(ReviewItem.position)).where(
                    ReviewItem.weekly_review_id == review.id, ReviewItem.kind == kind
                )
            ).scalar()
            or 0
        ) + 1
        db.add(
            ReviewItem(
                user_id=user.id,
                weekly_review_id=review.id,
                kind=kind,
                text=text,
                position=position,
            )
        )
        db.commit()
    return _items_response(request, db, user, iso_week)


@router.delete("/review-items/{item_id}")
def delete_review_item(
    item_id: int,
    request: Request,
    iso: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = _own_item(db, user, item_id)
    db.delete(item)
    db.commit()
    return _items_response(request, db, user, iso)
