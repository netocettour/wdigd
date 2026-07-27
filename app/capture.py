"""Captura diaria: lectura de bullets y parseo del texto del formulario.

El campo de captura acepta varias líneas de una vez (pegar una lista) y comandos
rápidos de categoría: `/l` logro, `/a` avance, `/d` desbloqueo, al principio o al
final de la línea.
"""

import re
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Entry, User
from app.weeks import DAYS_IN_WEEK

QUICK_COMMANDS = {
    "/l": "logro",
    "/a": "avance",
    "/d": "desbloqueo",
}

# Viñeta o numeración al principio de una línea pegada desde otro lado.
_LIST_PREFIX = re.compile(r"^(?:[*\-•]\s+|\d+[.)]\s+)")


# — Lectura —

def entries_between(db: Session, user: User, start: date, end: date) -> list[Entry]:
    """Bullets del usuario entre dos fechas, ambas incluidas, en orden de captura."""
    return list(
        db.execute(
            select(Entry)
            .where(
                Entry.user_id == user.id,
                Entry.entry_date >= start,
                Entry.entry_date <= end,
            )
            .order_by(Entry.entry_date, Entry.position, Entry.id)
        ).scalars()
    )


def entries_for_date(db: Session, user: User, day: date) -> list[Entry]:
    return entries_between(db, user, day, day)


def entries_for_week(db: Session, user: User, monday: date) -> list[Entry]:
    return entries_between(db, user, monday, monday + timedelta(days=DAYS_IN_WEEK - 1))


def next_position(db: Session, user: User, day: date) -> int:
    last = db.execute(
        select(func.max(Entry.position)).where(
            Entry.user_id == user.id, Entry.entry_date == day
        )
    ).scalar()
    return (last or 0) + 1


# — Parseo del formulario —

def _parse_quick_command(text: str) -> tuple[str, str | None]:
    lower = text.lower()
    for command, category in QUICK_COMMANDS.items():
        if lower.startswith(command + " "):
            return text[len(command):].strip(), category
        if lower.endswith(" " + command):
            return text[:-len(command)].strip(), category
    return text, None


def parse_capture(raw: str) -> list[tuple[str, str | None]]:
    """Texto del formulario a pares (texto del bullet, categoría o None)."""
    parsed = []
    for raw_line in raw.splitlines():
        line = _LIST_PREFIX.sub("", raw_line).strip()
        if not line:
            continue
        text, category = _parse_quick_command(line)
        if text:
            parsed.append((text, category))
    return parsed


def parse_date(value: str, default: date) -> date:
    """Fecha de un campo del formulario; el default cubre valores inválidos."""
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return default
