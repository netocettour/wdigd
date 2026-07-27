"""Bloque 2: números sin adjetivos, calculados al vuelo sobre entries.

Copy y estructura tomados de los prototipos (docs/designs). Tono neutro siempre:
nada acá califica, alerta ni reta.
"""

from collections import Counter
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CONSTRUCTION_CATEGORIES, Entry, User
from app.weeks import DAYS_IN_WEEK, monday_of, week_monday

# Cuántas semanas hacia atrás se miran para la racha de "avance sin logro".
LOOKBACK_WEEKS = 8
MIN_STREAK_WEEKS = 2


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def week_observations(
    db: Session, user: User, iso_year: int, iso_week: int, entries: list[Entry]
) -> list[str]:
    lines: list[str] = []
    total = len(entries)

    if total:
        counts = Counter(entry.category for entry in entries)
        sin_categoria = counts[None]
        parts = [
            f"{counts['logro']} {_plural(counts['logro'], 'logro', 'logros')}",
            f"{counts['avance']} {_plural(counts['avance'], 'avance', 'avances')}",
            f"{counts['desbloqueo']} "
            f"{_plural(counts['desbloqueo'], 'desbloqueo', 'desbloqueos')}",
        ]
        if sin_categoria:
            parts.append(f"{sin_categoria} sin categoría")
        lines.append("Esta semana: " + " · ".join(parts) + ".")

        fuera = sum(1 for entry in entries if not entry.priority_label)
        lines.append(
            f"{fuera} de {total} {_plural(total, 'bullet', 'bullets')} "
            "quedaron fuera de las prioridades de la semana."
        )

        if total - sin_categoria:
            construccion = sum(counts[category] for category in CONSTRUCTION_CATEGORIES)
            lines.append(
                f"Construcción / reacción: {construccion} de {total} bullets "
                "fueron construcción."
            )

        aligned = Counter(e.priority_label for e in entries if e.priority_label)
        if aligned:
            # Empate: gana la etiqueta más frecuente y, entre iguales, la primera alfabética.
            top = max(aligned.items(), key=lambda item: (item[1], item[0]))[0]
            lines.append(f"La prioridad con más presencia fue {top}.")

        lines.extend(_avance_sin_logro(db, user, iso_year, iso_week))

    distinct_days = len({entry.entry_date for entry in entries})
    lines.append(f"Capturaste {distinct_days} de {DAYS_IN_WEEK} días.")
    return lines


def _avance_sin_logro(db: Session, user: User, iso_year: int, iso_week: int) -> list[str]:
    """Prioridades con N semanas consecutivas (incluida esta) de avance sin logro."""
    monday = week_monday(iso_year, iso_week)
    start = monday - timedelta(days=DAYS_IN_WEEK * (LOOKBACK_WEEKS - 1))
    end = monday + timedelta(days=DAYS_IN_WEEK - 1)
    rows = db.execute(
        select(Entry.entry_date, Entry.category, Entry.priority_label).where(
            Entry.user_id == user.id,
            Entry.entry_date >= start,
            Entry.entry_date <= end,
            Entry.priority_label.is_not(None),
            Entry.category.in_(["avance", "logro"]),
        )
    ).all()

    # etiqueta → cuántas semanas atrás → categorías vistas esa semana
    by_priority: dict[str, dict[int, set[str]]] = {}
    for entry_date, category, label in rows:
        weeks_back = (monday - monday_of(entry_date)).days // DAYS_IN_WEEK
        by_priority.setdefault(label, {}).setdefault(weeks_back, set()).add(category)

    lines = []
    for label in sorted(by_priority, key=str.lower):
        weeks = by_priority[label]
        streak = 0
        for weeks_back in range(LOOKBACK_WEEKS):
            categories = weeks.get(weeks_back)
            if categories and "avance" in categories and "logro" not in categories:
                streak += 1
            else:
                break
        if streak >= MIN_STREAK_WEEKS:
            lines.append(f"{label} lleva {streak} semanas con avances y ningún logro.")
    return lines
