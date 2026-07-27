"""Material de la sesión semanal: bloques 1 (resumen), 2 (observaciones) y 3 (highlights).

Es el fragmento que se recarga entero por HTMX cada vez que cambia algo de la
semana, así que lo arma un solo lugar y lo usan tanto /week como los endpoints de
bullets y highlights.
"""

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.capture import entries_for_week
from app.models import CATEGORY_LABELS, Achievement, Entry, User, WeeklyReview
from app.observations import week_observations
from app.priorities import priorities_for_week
from app.templating import templates
from app.weeks import DIAS_ABBR, parse_iso_week, week_monday

FUERA = "Fuera de las prioridades de la semana"
SIN_PRIORIDAD = "Fuera de prioridades"

# Qué se ofrece debajo del texto de un bullet en el bloque 1.
META_CHIPS = "chips"       # alineado y sin categoría: chips para categorizarlo
META_CATEGORY = "category"  # alineado y categorizado: la categoría, sólo lectura
META_ALIGN = "align"        # sin alinear: botón para alinearlo con una prioridad


def find_review(db: Session, user: User, iso_year: int, iso_week: int) -> WeeklyReview | None:
    return db.execute(
        select(WeeklyReview).where(
            WeeklyReview.user_id == user.id,
            WeeklyReview.iso_year == iso_year,
            WeeklyReview.iso_week == iso_week,
        )
    ).scalar_one_or_none()


def get_or_create_review(db: Session, user: User, iso_year: int, iso_week: int) -> WeeklyReview:
    """La review se crea lazy: la primera visita a /week/{iso} ya la deja hecha."""
    review = find_review(db, user, iso_year, iso_week)
    if review is None:
        review = WeeklyReview(user_id=user.id, iso_year=iso_year, iso_week=iso_week)
        db.add(review)
        db.commit()
    return review


def _highlights(db: Session, review: WeeklyReview) -> tuple[list[dict], dict[int, int]]:
    """Highlights de la review y, por bullet promovido, el highlight que lo tomó."""
    rows = list(
        db.execute(
            select(Achievement)
            .options(joinedload(Achievement.entries))
            .where(Achievement.weekly_review_id == review.id)
            .order_by(Achievement.position, Achievement.id)
        )
        .unique()
        .scalars()
    )

    highlights = []
    promoted: dict[int, int] = {}
    for achievement in rows:
        labels = sorted({e.priority_label for e in achievement.entries if e.priority_label})
        for entry in achievement.entries:
            promoted[entry.id] = achievement.id
        highlights.append(
            {
                "id": achievement.id,
                "text": achievement.text,
                "priority_labels": ", ".join(labels) or SIN_PRIORIDAD,
            }
        )
    return highlights, promoted


def _meta_mode(entry: Entry, *, aligned: bool, editable: bool, can_align: bool) -> str:
    if not aligned:
        return META_ALIGN if editable and can_align else ""
    if entry.category is not None:
        return META_CATEGORY
    return META_CHIPS if editable else ""


def _group_by_priority(
    entries: list[Entry], priorities: list[str]
) -> list[tuple[str, bool, list[Entry]]]:
    """(nombre del grupo, es "fuera de prioridades", bullets).

    Primero las prioridades vigentes que tienen bullets, en su orden; después las
    etiquetas sueltas (de una review anterior o de una prioridad ya borrada) y al
    final los bullets sin alinear.
    """
    by_label: dict[str | None, list[Entry]] = {}
    for entry in entries:
        by_label.setdefault(entry.priority_label, []).append(entry)

    in_effect = [label for label in priorities if label in by_label]
    leftover = sorted(
        (label for label in by_label if label and label not in priorities), key=str.lower
    )

    groups = [(label, False, by_label[label]) for label in in_effect + leftover]
    unaligned = by_label.get(None, [])
    if unaligned:
        groups.append((FUERA, True, unaligned))
    return groups


def material_context(db: Session, user: User, iso: str) -> dict:
    iso_year, iso_week = parse_iso_week(iso)
    monday = week_monday(iso_year, iso_week)
    review = find_review(db, user, iso_year, iso_week)
    editable = review is None or review.closed_at is None

    entries = entries_for_week(db, user, monday)
    priorities = priorities_for_week(db, user, iso_year, iso_week)
    can_align = bool(priorities)
    highlights, promoted = _highlights(db, review) if review is not None else ([], {})

    def row(entry: Entry, aligned: bool) -> dict:
        return {
            "id": entry.id,
            "text": entry.text,
            "day_abbr": DIAS_ABBR[entry.entry_date.weekday()],
            # `category` lo lee el macro cat_chips para marcar el chip elegido.
            "category": entry.category,
            "category_label": CATEGORY_LABELS.get(entry.category, ""),
            "priority_label": entry.priority_label,
            "promoted": entry.id in promoted,
            "achievement_id": promoted.get(entry.id),
            "meta": _meta_mode(
                entry, aligned=aligned, editable=editable, can_align=can_align
            ),
        }

    groups = [
        {
            "name": name,
            "is_fuera": is_fuera,
            "rows": [row(entry, aligned=not is_fuera) for entry in group_entries],
        }
        for name, is_fuera, group_entries in _group_by_priority(entries, priorities)
    ]

    return {
        "iso": iso,
        "editable": editable,
        "groups": groups,
        "highlights": highlights,
        "priorities": priorities,
        "can_align": can_align,
        "observations": week_observations(db, user, iso_year, iso_week, entries),
    }


def material_response(request: Request, db: Session, user: User, iso: str):
    return templates.TemplateResponse(
        request, "components/week_material.html", material_context(db, user, iso)
    )
