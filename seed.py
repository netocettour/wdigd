"""Genera datos ficticios para trabajar la sesión semanal sin capturar a mano.

Cuatro semanas hacia atrás (offsets 3..0):
- W-3: entries + review CERRADA (fija las prioridades que rigen W-2).
- W-2: entries alineados a esas prioridades + review CERRADA completa
       (highlights, journal). Es la semana rica.
- W-1: entries alineados + review A MEDIAS (sin cerrar).
- W0 (actual): entries hasta hoy, sin review.

Uso: python seed.py  →  usuario demo@wdigd.local / contraseña demo1234
No usarlo en producción: crea un usuario demo con contraseña conocida.
"""

from datetime import date, datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import (
    DEFAULT_TIMEZONE,
    Achievement,
    Entry,
    ReviewItem,
    User,
    WeeklyReview,
    achievement_entries,
)
from app.security import hash_password

EMAIL = "demo@wdigd.local"
PASSWORD = "demo1234"

PRIOS_A = ["Cerrar quarter comercial", "Evaluación del equipo", "Mañanas para plataforma"]
PRIOS_B = ["Cerrar etapa plataforma", "Firmar con Brasil", "Mañanas para plataforma"]

# (día 0=lun..6=dom, texto, categoría, prioridad alineada | None)
WEEK_MINUS_3 = [
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Primer borrador del roadmap de la plataforma", "avance", None),
    (1, "Reunión de pipeline con el equipo comercial", "avance", None),
    (2, "Definir criterios de evaluación del equipo", "avance", None),
    (3, "Avanzar la integración de pagos", "avance", None),
    (4, "Cerrar el presupuesto del trimestre", "logro", None),
]

WEEK_MINUS_2 = [
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Revisión del prototipo de la plataforma", "avance", "Mañanas para plataforma"),
    (1, "Reunión de pipeline con el equipo comercial", "avance", "Cerrar quarter comercial"),
    (1, "Feedback 1:1 con Luis", "logro", "Evaluación del equipo"),
    (2, "Contestar el pedido urgente de Socios", "desbloqueo", None),
    (2, "Auditar el prototipo de la nueva plataforma", "avance", "Mañanas para plataforma"),
    (3, "Preparar propuesta para Socios", "avance", None),
    (4, "Evaluación de performance de Luis", "logro", "Evaluación del equipo"),
    (4, "Cerrar nuevas ventas en Brasil", "avance", "Cerrar quarter comercial"),
]

WEEK_MINUS_1 = [
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Seguimiento del pipeline comercial", "avance", "Firmar con Brasil"),
    (1, "Iterar el onboarding de la plataforma", "avance", "Cerrar etapa plataforma"),
    (2, "Apagar el incendio del deploy del viernes", "desbloqueo", None),
    (3, "Sesión con Socios por el presupuesto", "avance", None),
    (3, "Nueva revisión de la plataforma", "avance", "Mañanas para plataforma"),
]

CURRENT_WEEK = [
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Reunión de seguimiento con el equipo", "avance", None),
    (1, "Avanzar el rediseño de la plataforma", "avance", "Cerrar etapa plataforma"),
    (2, "Responder la auditoría del cliente grande", "desbloqueo", "Firmar con Brasil"),
    (3, "Propuesta de precios nueva", "avance", None),
]

# (texto del bullet de origen, texto del highlight en limpio)
HIGHLIGHTS_MINUS_2 = [
    (
        "Evaluación de performance de Luis",
        "Cerré la evaluación de performance de Luis, con un plan claro.",
    ),
    ("Cerrar nuevas ventas en Brasil", "Brasil pasó a etapa de contrato."),
]

NARRATIVE_MINUS_2 = (
    "Fue una semana de cerrar cosas que venían abiertas hace rato. "
    "Lo de Luis salió mejor de lo que esperaba: la conversación difícil "
    "era conmigo, no con él.\n\n"
    "La plataforma sigue avanzando pero sin un logro a la vista; quiero "
    "definir qué significaría cerrar esa etapa."
)


def _get_or_create_user(db: Session) -> User:
    user = db.execute(select(User).where(User.email == EMAIL)).scalar_one_or_none()
    if user is None:
        user = User(
            email=EMAIL, password_hash=hash_password(PASSWORD), timezone=DEFAULT_TIMEZONE
        )
        db.add(user)
        db.flush()
    return user


def _wipe_user_data(db: Session, user: User) -> None:
    review_ids = list(
        db.execute(
            select(WeeklyReview.id).where(WeeklyReview.user_id == user.id)
        ).scalars()
    )
    if review_ids:
        achievement_ids = list(
            db.execute(
                select(Achievement.id).where(
                    Achievement.weekly_review_id.in_(review_ids)
                )
            ).scalars()
        )
        if achievement_ids:
            db.execute(
                achievement_entries.delete().where(
                    achievement_entries.c.achievement_id.in_(achievement_ids)
                )
            )
            db.execute(delete(Achievement).where(Achievement.id.in_(achievement_ids)))
        db.execute(delete(ReviewItem).where(ReviewItem.user_id == user.id))
        db.execute(delete(WeeklyReview).where(WeeklyReview.user_id == user.id))
    db.execute(delete(Entry).where(Entry.user_id == user.id))
    db.flush()


def _monday_of_offset(monday: date, offset_weeks: int) -> date:
    return monday - timedelta(days=7 * offset_weeks)


def _add_entries(db: Session, user: User, base_monday: date, rows: list, today: date) -> None:
    positions: dict[date, int] = {}
    for weekday, text, category, priority in rows:
        day = base_monday + timedelta(days=weekday)
        if day > today:
            continue
        positions[day] = positions.get(day, 0) + 1
        db.add(
            Entry(
                user_id=user.id,
                entry_date=day,
                text=text,
                category=category,
                priority_label=priority,
                position=positions[day],
            )
        )


def _add_review(
    db: Session,
    user: User,
    monday: date,
    *,
    name: str = "",
    narrative: str = "",
    priorities: list[str] | None = None,
    closed_days_ago: int | None = None,
) -> WeeklyReview:
    iso = monday.isocalendar()
    closed_at = (
        None
        if closed_days_ago is None
        else datetime.now(dt_timezone.utc) - timedelta(days=closed_days_ago)
    )
    review = WeeklyReview(
        user_id=user.id,
        iso_year=iso.year,
        iso_week=iso.week,
        name=name,
        narrative=narrative,
        priorities="\n".join(priorities or []),
        closed_at=closed_at,
    )
    db.add(review)
    db.flush()
    return review


def _add_highlights(db: Session, user: User, review: WeeklyReview) -> None:
    for position, (source_text, highlight_text) in enumerate(HIGHLIGHTS_MINUS_2, start=1):
        entry = db.execute(
            select(Entry).where(Entry.user_id == user.id, Entry.text == source_text)
        ).scalars().first()
        achievement = Achievement(
            weekly_review_id=review.id, text=highlight_text, position=position
        )
        if entry is not None:
            achievement.entries.append(entry)
        db.add(achievement)


def main() -> None:
    db = SessionLocal()
    try:
        user = _get_or_create_user(db)
        _wipe_user_data(db, user)

        today = datetime.now(ZoneInfo(user.timezone)).date()
        monday = today - timedelta(days=today.weekday())
        mondays = {offset: _monday_of_offset(monday, offset) for offset in (3, 2, 1, 0)}

        for offset, rows in (
            (3, WEEK_MINUS_3),
            (2, WEEK_MINUS_2),
            (1, WEEK_MINUS_1),
            (0, CURRENT_WEEK),
        ):
            _add_entries(db, user, mondays[offset], rows, today)
        db.flush()

        # W-3: cerrada, fija las prioridades que rigen W-2.
        _add_review(
            db,
            user,
            mondays[3],
            name="Arranque del trimestre",
            narrative="Semana de arranque del trimestre.",
            priorities=PRIOS_A,
            closed_days_ago=20,
        )

        # W-2: cerrada y completa, la semana rica.
        review_minus_2 = _add_review(
            db,
            user,
            mondays[2],
            name="La semana de Luis",
            narrative=NARRATIVE_MINUS_2,
            priorities=PRIOS_B,
            closed_days_ago=13,
        )
        _add_highlights(db, user, review_minus_2)

        # W-1: a medias, sin cerrar.
        _add_review(
            db,
            user,
            mondays[1],
            narrative="Semana cortada por el incendio del deploy. Quedó sin cerrar.",
        )

        db.commit()
        print(f"Seed listo: {EMAIL} / {PASSWORD}")
        for offset, label in ((3, "cerrada"), (2, "cerrada"), (1, "a medias"), (0, "actual")):
            iso = mondays[offset].isocalendar()
            print(f"  {iso.year}-W{iso.week:02d} ({label})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
