"""Bloque 2: números sin adjetivos, calculados al vuelo sobre entries.

Copy y estructura tomados de los prototipos (docs/designs). Tono neutro siempre:
nada acá califica, alerta ni reta.
"""

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Entry, User, WeeklyReview
from app.weeks import week_monday

LOOKBACK_WEEKS = 8


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def week_observations(
    db: Session, user: User, iso_year: int, iso_week: int, entries: list[Entry]
) -> list[str]:
    monday = week_monday(iso_year, iso_week)
    lines: list[str] = []
    total = len(entries)

    if total:
        counts = Counter(e.category for e in entries)
        logro, avance, desbloqueo = counts["logro"], counts["avance"], counts["desbloqueo"]
        sin = counts[None]
        parts = [
            f"{logro} {_plural(logro, 'logro', 'logros')}",
            f"{avance} {_plural(avance, 'avance', 'avances')}",
            f"{desbloqueo} {_plural(desbloqueo, 'desbloqueo', 'desbloqueos')}",
        ]
        if sin:
            parts.append(f"{sin} sin categoría")
        lines.append("Esta semana: " + " · ".join(parts) + ".")

        fuera = sum(1 for e in entries if not e.priority_label)
        lines.append(
            f"{fuera} de {total} {_plural(total, 'bullet', 'bullets')} "
            "quedaron fuera de las prioridades de la semana."
        )

        categorized = total - sin
        if categorized:
            construccion = logro + avance
            lines.append(
                f"Construcción / reacción: {construccion} de {total} bullets fueron construcción."
            )

        aligned = Counter(e.priority_label for e in entries if e.priority_label)
        if aligned:
            top = max(aligned.items(), key=lambda kv: (kv[1], kv[0]))[0]
            lines.append(f"La prioridad con más presencia fue {top}.")

        lines.extend(_avance_sin_logro(db, user, iso_year, iso_week))

    distinct_days = len({e.entry_date for e in entries})
    lines.append(f"Capturaste {distinct_days} de 7 días.")
    return lines


def _avance_sin_logro(db: Session, user: User, iso_year: int, iso_week: int) -> list[str]:
    """Prioridades con N semanas consecutivas (incluida esta) de avance sin logro."""
    monday = week_monday(iso_year, iso_week)
    start = monday - timedelta(days=7 * (LOOKBACK_WEEKS - 1))
    end = monday + timedelta(days=6)
    rows = db.execute(
        select(Entry.entry_date, Entry.category, Entry.priority_label).where(
            Entry.user_id == user.id,
            Entry.entry_date >= start,
            Entry.entry_date <= end,
            Entry.priority_label.is_not(None),
            Entry.category.in_(["avance", "logro"]),
        )
    ).all()

    by_prio: dict[str, dict[int, set[str]]] = {}
    for entry_date, category, label in rows:
        weeks_back = (monday - week_monday(*entry_date.isocalendar()[:2])).days // 7
        by_prio.setdefault(label, {}).setdefault(weeks_back, set()).add(category)

    lines = []
    for label in sorted(by_prio, key=str.lower):
        weeks = by_prio[label]
        streak = 0
        for back in range(LOOKBACK_WEEKS):
            cats = weeks.get(back)
            if cats and "avance" in cats and "logro" not in cats:
                streak += 1
            else:
                break
        if streak >= 2:
            lines.append(f"{label} lleva {streak} semanas con avances y ningún logro.")
    return lines
