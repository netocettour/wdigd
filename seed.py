"""Genera datos ficticios para trabajar la sesión semanal sin capturar a mano.

Cuatro semanas hacia atrás (offsets 3..0):
- W-3: entries + review CERRADA (fija las prioridades que rigen W-2).
- W-2: entries alineados a esas prioridades + review CERRADA completa
       (highlights, journal, preocupaciones/seguimientos). Es la semana rica.
- W-1: entries alineados + review A MEDIAS (sin cerrar).
- W0 (actual): entries hasta hoy, sin review.

Las preocupaciones se repiten entre semanas para mostrar la nota de recurrencia.

Uso: python seed.py  →  usuario demo@wdigd.local / contraseña demo1234
"""

from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import (
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
TZ = "America/Argentina/Cordoba"

PRIOS_A = ["Cerrar quarter comercial", "Evaluación del equipo", "Mañanas para plataforma"]
PRIOS_B = ["Cerrar etapa plataforma", "Firmar con Brasil", "Mañanas para plataforma"]

PREO_RECURRENTE = "No quiero subestimar el costo de la decisión de la plataforma."

# (día 0=lun..6=dom, texto, categoría, prioridad-alineada|None)
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


def main() -> None:
    db = SessionLocal()
    try:
        user = db.execute(select(User).where(User.email == EMAIL)).scalar_one_or_none()
        if user is None:
            user = User(email=EMAIL, password_hash=hash_password(PASSWORD), timezone=TZ)
            db.add(user)
            db.flush()

        _wipe_user_data(db, user)

        today = datetime.now(ZoneInfo(TZ)).date()
        monday = today - timedelta(days=today.weekday())

        def add_week(offset_weeks: int, rows) -> None:
            base = monday - timedelta(days=7 * offset_weeks)
            positions: dict = {}
            for day, text, category, prio in rows:
                d = base + timedelta(days=day)
                if offset_weeks == 0 and d > today:
                    continue
                positions[d] = positions.get(d, 0) + 1
                db.add(
                    Entry(
                        user_id=user.id,
                        entry_date=d,
                        text=text,
                        category=category,
                        priority_label=prio,
                        position=positions[d],
                    )
                )

        add_week(3, WEEK_MINUS_3)
        add_week(2, WEEK_MINUS_2)
        add_week(1, WEEK_MINUS_1)
        add_week(0, CURRENT_WEEK)
        db.flush()

        def iso_of(offset_weeks: int) -> tuple[int, int]:
            iso = (monday - timedelta(days=7 * offset_weeks)).isocalendar()
            return iso.year, iso.week

        def entry_by_text(text: str) -> Entry | None:
            return db.execute(
                select(Entry).where(Entry.user_id == user.id, Entry.text == text)
            ).scalars().first()

        # W-3: review cerrada, fija las prioridades que rigen W-2.
        y3, w3 = iso_of(3)
        r3 = WeeklyReview(
            user_id=user.id,
            iso_year=y3,
            iso_week=w3,
            narrative="Semana de arranque del trimestre.",
            priorities="\n".join(PRIOS_A),
            closed_at=datetime.now(dt_timezone.utc) - timedelta(days=20),
        )
        db.add(r3)
        db.flush()
        db.add(
            ReviewItem(
                user_id=user.id, weekly_review_id=r3.id, kind="preocupacion",
                text=PREO_RECURRENTE, position=1,
            )
        )

        # W-2: review cerrada completa (la semana rica).
        y2, w2 = iso_of(2)
        r2 = WeeklyReview(
            user_id=user.id,
            iso_year=y2,
            iso_week=w2,
            narrative=(
                "Fue una semana de cerrar cosas que venían abiertas hace rato. "
                "Lo de Luis salió mejor de lo que esperaba: la conversación difícil "
                "era conmigo, no con él.\n\n"
                "La plataforma sigue avanzando pero sin un logro a la vista; quiero "
                "definir qué significaría cerrar esa etapa."
            ),
            priorities="\n".join(PRIOS_B),
            closed_at=datetime.now(dt_timezone.utc) - timedelta(days=13),
        )
        db.add(r2)
        db.flush()
        for pos, source in enumerate(
            ["Evaluación de performance de Luis", "Cerrar nuevas ventas en Brasil"], start=1
        ):
            entry = entry_by_text(source)
            ach = Achievement(
                weekly_review_id=r2.id,
                text=(
                    "Cerré la evaluación de performance de Luis, con un plan claro."
                    if pos == 1
                    else "Brasil pasó a etapa de contrato."
                ),
                position=pos,
            )
            if entry is not None:
                ach.entries.append(entry)
            db.add(ach)
        db.add_all(
            [
                ReviewItem(
                    user_id=user.id, weekly_review_id=r2.id, kind="preocupacion",
                    text=PREO_RECURRENTE, position=1,
                ),
                ReviewItem(
                    user_id=user.id, weekly_review_id=r2.id, kind="seguimiento",
                    text="El proveedor no parece serio; el deal permite salirnos.", position=1,
                ),
            ]
        )

        # W-1: review a medias, sin cerrar. Repite la preocupación (recurrencia).
        y1, w1 = iso_of(1)
        r1 = WeeklyReview(
            user_id=user.id,
            iso_year=y1,
            iso_week=w1,
            narrative="Semana cortada por el incendio del deploy. Quedó sin cerrar.",
            priorities="",
            closed_at=None,
        )
        db.add(r1)
        db.flush()
        db.add_all(
            [
                ReviewItem(
                    user_id=user.id, weekly_review_id=r1.id, kind="preocupacion",
                    text=PREO_RECURRENTE, position=1,
                ),
                ReviewItem(
                    user_id=user.id, weekly_review_id=r1.id, kind="seguimiento",
                    text="Presupuesto de Socios: falta la firma final.", position=1,
                ),
            ]
        )

        db.commit()
        print(f"Seed listo: {EMAIL} / {PASSWORD}")
        print(f"Semanas: {iso_of(3)} (cerrada), {iso_of(2)} (cerrada), "
              f"{iso_of(1)} (a medias), {iso_of(0)} (actual).")
    finally:
        db.close()


def _wipe_user_data(db, user) -> None:
    review_ids = [
        r_id
        for (r_id,) in db.execute(
            select(WeeklyReview.id).where(WeeklyReview.user_id == user.id)
        )
    ]
    if review_ids:
        ach_ids = [
            a_id
            for (a_id,) in db.execute(
                select(Achievement.id).where(Achievement.weekly_review_id.in_(review_ids))
            )
        ]
        if ach_ids:
            db.execute(
                achievement_entries.delete().where(
                    achievement_entries.c.achievement_id.in_(ach_ids)
                )
            )
            db.execute(delete(Achievement).where(Achievement.id.in_(ach_ids)))
        db.execute(delete(ReviewItem).where(ReviewItem.user_id == user.id))
        db.execute(delete(WeeklyReview).where(WeeklyReview.user_id == user.id))
    db.execute(delete(Entry).where(Entry.user_id == user.id))
    db.flush()


if __name__ == "__main__":
    main()
