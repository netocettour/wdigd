"""Helpers de fechas y semanas ISO, siempre en la timezone del usuario."""

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException

from app.models import User
from app.models.user import DEFAULT_TIMEZONE

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_ABBR = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

DAYS_IN_WEEK = 7

_ISO_WEEK_RE = re.compile(r"^(\d{4})-W(\d{1,2})$")


# — Timezone del usuario —

def valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


def user_tz(user: User) -> ZoneInfo:
    if valid_timezone(user.timezone):
        return ZoneInfo(user.timezone)
    return ZoneInfo(DEFAULT_TIMEZONE)


def user_today(user: User) -> date:
    return datetime.now(user_tz(user)).date()


# — Semanas ISO —

def format_iso_week(iso_year: int, iso_week: int) -> str:
    """Semana ISO en el formato que usan las URLs: 2026-W31."""
    return f"{iso_year}-W{iso_week:02d}"


def iso_week_str(d: date) -> str:
    iso = d.isocalendar()
    return format_iso_week(iso.year, iso.week)


def parse_iso_week(s: str) -> tuple[int, int]:
    m = _ISO_WEEK_RE.match(s)
    if m:
        year, week = int(m.group(1)), int(m.group(2))
        try:
            date.fromisocalendar(year, week, 1)
            return year, week
        except ValueError:
            pass
    raise HTTPException(status_code=404, detail="Semana inválida")


def week_monday(iso_year: int, iso_week: int) -> date:
    return date.fromisocalendar(iso_year, iso_week, 1)


def monday_of(d: date) -> date:
    """Lunes de la semana ISO a la que pertenece una fecha."""
    return d - timedelta(days=d.weekday())


def prev_iso(iso_year: int, iso_week: int) -> tuple[int, int]:
    iso = (week_monday(iso_year, iso_week) - timedelta(days=DAYS_IN_WEEK)).isocalendar()
    return iso.year, iso.week


def next_iso(iso_year: int, iso_week: int) -> tuple[int, int]:
    iso = (week_monday(iso_year, iso_week) + timedelta(days=DAYS_IN_WEEK)).isocalendar()
    return iso.year, iso.week


# — Texto para la interfaz —

def week_label(monday: date) -> str:
    sunday = monday + timedelta(days=DAYS_IN_WEEK - 1)
    if monday.month == sunday.month:
        return f"Semana del {monday.day} al {sunday.day} de {MESES[monday.month - 1]}"
    return (
        f"Semana del {monday.day} de {MESES[monday.month - 1]} "
        f"al {sunday.day} de {MESES[sunday.month - 1]}"
    )


def fecha_larga(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day} de {MESES[d.month - 1]}"


def parse_priorities(text: str) -> list[str]:
    """Prioridades guardadas como texto, una por línea, con o sin viñeta."""
    priorities = []
    for raw in (text or "").splitlines():
        line = raw.strip().lstrip("-•*").strip()
        if line:
            priorities.append(line)
    return priorities
