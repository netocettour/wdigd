"""Cuenta demo para grabar video: cinco semanas cerradas + semana corriente
con lunes a viernes capturados (5/7) y SIN cerrar, para poder hacer la sesión
semanal en vivo. Sábados y domingos quedan en blanco a propósito.

Usuario: demo-video@wdigd.local / videodemo1234

Uso local:
    python seed_demo.py

Uso contra Railway (desde la máquina, con el CLI logueado):
    railway link --project surprising-adventure --environment production
    railway service wdigd
    railway run python seed_demo.py

Como seed.py, borra los datos previos del usuario demo-video antes de sembrar.
No borra a nadie más.
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

EMAIL = "demo-video@wdigd.local"
PASSWORD = "videodemo1234"

# Prioridades que van rotando trimestre a trimestre. La review de la semana N
# fija las prioridades que rigen la semana N+1.
PRIOS_W5 = ["Cerrar quarter comercial", "Contratar tech lead", "Mañanas para plataforma"]
PRIOS_W4 = ["Cerrar quarter comercial", "Onboarding tech lead", "Mañanas para plataforma"]
PRIOS_W3 = ["Etapa 1 de la plataforma", "Presupuesto del próximo quarter", "Mañanas para plataforma"]
PRIOS_W2 = ["Etapa 1 de la plataforma", "Firmar con Brasil", "Mañanas para plataforma"]
PRIOS_W1 = ["Cerrar etapa 1 de la plataforma", "Firmar con Brasil", "Foco en producto"]
# La review W-1 fija las prioridades para la semana corriente:
PRIOS_CURRENT = ["Lanzar etapa 1 de la plataforma", "Cerrar Brasil", "Empezar planificación Q4"]

# Formato de cada fila: (weekday 0=lun..6=dom, texto, categoría, prioridad|None)

WEEK_MINUS_5 = [
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Kickoff del quarter con el equipo", "avance", "Cerrar quarter comercial"),
    (1, "Sesión de pipeline con comercial", "avance", "Cerrar quarter comercial"),
    (1, "Filtrar CVs para el tech lead", "avance", "Contratar tech lead"),
    (2, "Primera entrevista con candidata para tech lead", "avance", "Contratar tech lead"),
    (2, "Revisar prototipo de la plataforma", "avance", "Mañanas para plataforma"),
    (3, "Reunión con proveedor de pagos", "avance", None),
    (4, "Cerré ronda de entrevistas para tech lead", "logro", "Contratar tech lead"),
    (4, "Enviar propuesta a cliente grande", "avance", "Cerrar quarter comercial"),
]

WEEK_MINUS_4 = [
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Definir oferta final para la tech lead", "avance", "Onboarding tech lead"),
    (1, "Aceptó la oferta la tech lead", "logro", "Onboarding tech lead"),
    (1, "Prep del onboarding con RRHH", "avance", "Onboarding tech lead"),
    (2, "Cerré la venta grande del quarter", "logro", "Cerrar quarter comercial"),
    (3, "Corte de números del trimestre", "avance", "Cerrar quarter comercial"),
    (3, "Trabajar el roadmap de plataforma", "avance", "Mañanas para plataforma"),
    (4, "Presentación de números al board", "logro", "Cerrar quarter comercial"),
]

WEEK_MINUS_3 = [
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Primer día de la tech lead: onboarding y contexto", "avance", None),
    (1, "Definir alcance de la etapa 1 de la plataforma", "avance", "Etapa 1 de la plataforma"),
    (2, "Draft del presupuesto Q4", "avance", "Presupuesto del próximo quarter"),
    (2, "Sesión de arquitectura con la tech lead", "avance", "Mañanas para plataforma"),
    (3, "Revisión del presupuesto con finanzas", "avance", "Presupuesto del próximo quarter"),
    (3, "Contestar pedido urgente de un cliente", "desbloqueo", None),
    (4, "Cerrar el scope de la etapa 1", "logro", "Etapa 1 de la plataforma"),
]

WEEK_MINUS_2 = [
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Sesión de foco en la plataforma", "avance", "Mañanas para plataforma"),
    (1, "Primera reunión con el prospect de Brasil", "avance", "Firmar con Brasil"),
    (1, "Review del avance de la etapa 1", "avance", "Etapa 1 de la plataforma"),
    (2, "Segunda vuelta con Brasil por el pricing", "avance", "Firmar con Brasil"),
    (2, "Pair con la tech lead sobre el modelo de datos", "avance", "Etapa 1 de la plataforma"),
    (3, "Apagar incendio del deploy del jueves", "desbloqueo", None),
    (4, "Propuesta formal enviada a Brasil", "logro", "Firmar con Brasil"),
    (4, "Cierre de sprint de plataforma", "avance", "Etapa 1 de la plataforma"),
]

WEEK_MINUS_1 = [
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Sesión de foco en la plataforma", "avance", "Foco en producto"),
    (1, "Ajustes finales al contrato de Brasil", "avance", "Firmar con Brasil"),
    (1, "Revisión de QA de la etapa 1", "avance", "Cerrar etapa 1 de la plataforma"),
    (2, "Sesión larga de código con la tech lead", "avance", "Foco en producto"),
    (3, "Firmé el contrato con Brasil", "logro", "Firmar con Brasil"),
    (3, "Preparar demo interna de la plataforma", "avance", "Cerrar etapa 1 de la plataforma"),
    (4, "Demo interna: quedó bien, quedan detalles", "avance", "Cerrar etapa 1 de la plataforma"),
    (4, "1:1 con la tech lead para bajar tensión", "desbloqueo", None),
]

# Semana corriente: 7/7, sin review.
CURRENT_WEEK = [
    # Lunes
    (0, "Planificar la semana", "desbloqueo", None),
    (0, "Kickoff del sprint de lanzamiento", "avance", "Lanzar etapa 1 de la plataforma"),
    (0, "Sesión con marketing por el anuncio", "avance", "Lanzar etapa 1 de la plataforma"),
    # Martes
    (1, "Terminar la doc para clientes de Brasil", "avance", "Cerrar Brasil"),
    (1, "Repasar el checklist de lanzamiento con la tech lead", "avance", "Lanzar etapa 1 de la plataforma"),
    # Miércoles
    (2, "Primera reunión de kickoff con el cliente de Brasil", "logro", "Cerrar Brasil"),
    (2, "Fix urgente en el flujo de onboarding", "desbloqueo", "Lanzar etapa 1 de la plataforma"),
    (2, "Draft del post de anuncio", "avance", "Lanzar etapa 1 de la plataforma"),
    # Jueves
    (3, "Revisión del plan de Q4 con finanzas", "avance", "Empezar planificación Q4"),
    (3, "Ensayo de la demo pública", "avance", "Lanzar etapa 1 de la plataforma"),
    # Viernes
    (4, "Lanzamos etapa 1 al público", "logro", "Lanzar etapa 1 de la plataforma"),
    (4, "Cliente de Brasil confirmó primer pago", "logro", "Cerrar Brasil"),
    (4, "Sesión de retro rápida con el equipo", "avance", None),
    # Sábado y domingo: en blanco a propósito (no trabajo los fines de semana).
]

# Highlights de cada review cerrada: (texto del bullet origen, texto del highlight)
HIGHLIGHTS_W5 = [
    ("Cerré ronda de entrevistas para tech lead", "Terminé el proceso de tech lead con una candidata fuerte."),
    ("Enviar propuesta a cliente grande", "Dejé la propuesta grande enviada antes del cierre."),
]

HIGHLIGHTS_W4 = [
    ("Cerré la venta grande del quarter", "Cerramos la venta grande, el quarter comercial quedó en verde."),
    ("Aceptó la oferta la tech lead", "La tech lead aceptó; arranca la próxima semana."),
    ("Presentación de números al board", "Presentación al board salió mejor de lo esperado."),
]

HIGHLIGHTS_W3 = [
    ("Cerrar el scope de la etapa 1", "Definimos y cerramos el scope de la etapa 1 de plataforma."),
    ("Primer día de la tech lead: onboarding y contexto", "Onboarding de la tech lead arrancado sin fricción."),
]

HIGHLIGHTS_W2 = [
    ("Propuesta formal enviada a Brasil", "Brasil recibió la propuesta y respondió al día siguiente."),
    ("Cierre de sprint de plataforma", "El sprint cerró con el core de la etapa 1 andando."),
]

HIGHLIGHTS_W1 = [
    ("Firmé el contrato con Brasil", "Firmamos con Brasil, primer cliente de la región."),
    ("Demo interna: quedó bien, quedan detalles", "La demo interna dejó claro que la etapa 1 está lista."),
]

NARRATIVE_W5 = (
    "Semana de arranque del quarter. Mucho tiempo en el proceso de hiring y en pipeline.\n\n"
    "Me costó proteger las mañanas para plataforma; algo tengo que cambiar en la agenda."
)

NARRATIVE_W4 = (
    "Semana de cierres. La venta grande y la oferta a la tech lead cayeron el mismo día.\n\n"
    "Empiezo a ver que cuando el pipeline está laburado con anticipación, los cierres se "
    "acumulan solos al final del quarter."
)

NARRATIVE_W3 = (
    "Primera semana con la tech lead adentro. Me sorprendió cuánto liberó de mi cabeza "
    "poder delegar decisiones técnicas.\n\n"
    "El presupuesto del próximo quarter sigue medio a los tumbos, no me convence el número."
)

NARRATIVE_W2 = (
    "El deploy del jueves me costó el resto del día, pero el resto de la semana sostuvo "
    "el foco en Brasil y en la etapa 1.\n\n"
    "Aprendo de nuevo que un incendio no es motivo para tirar la semana entera."
)

NARRATIVE_W1 = (
    "Firmamos Brasil y la demo interna dejó la etapa 1 en pie. La semana que viene es de "
    "lanzamiento, tengo que llegar descansado.\n\n"
    "La tech lead está pisando fuerte; el 1:1 fue más para bajar mi ansiedad que la de ella."
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


def _add_highlights(
    db: Session, user: User, review: WeeklyReview, highlights: list[tuple[str, str]]
) -> None:
    for position, (source_text, highlight_text) in enumerate(highlights, start=1):
        entry = (
            db.execute(
                select(Entry).where(Entry.user_id == user.id, Entry.text == source_text)
            )
            .scalars()
            .first()
        )
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
        mondays = {offset: _monday_of_offset(monday, offset) for offset in range(6)}

        weeks = [
            (5, WEEK_MINUS_5),
            (4, WEEK_MINUS_4),
            (3, WEEK_MINUS_3),
            (2, WEEK_MINUS_2),
            (1, WEEK_MINUS_1),
            (0, CURRENT_WEEK),
        ]
        for offset, rows in weeks:
            _add_entries(db, user, mondays[offset], rows, today)
        db.flush()

        closed_specs = [
            (5, "Kickoff de quarter", NARRATIVE_W5, PRIOS_W5, HIGHLIGHTS_W5, 35),
            (4, "Los cierres del quarter", NARRATIVE_W4, PRIOS_W4, HIGHLIGHTS_W4, 28),
            (3, "Arranque de la nueva etapa", NARRATIVE_W3, PRIOS_W3, HIGHLIGHTS_W3, 21),
            (2, "Semana de la propuesta a Brasil", NARRATIVE_W2, PRIOS_W2, HIGHLIGHTS_W2, 14),
            (1, "Firmamos Brasil", NARRATIVE_W1, PRIOS_W1, HIGHLIGHTS_W1, 7),
        ]
        for offset, name, narrative, priorities, highlights, days_ago in closed_specs:
            review = _add_review(
                db,
                user,
                mondays[offset],
                name=name,
                narrative=narrative,
                priorities=priorities,
                closed_days_ago=days_ago,
            )
            _add_highlights(db, user, review, highlights)

        # Semana corriente: NO se crea WeeklyReview -> la sesión aparece pendiente
        # y las prioridades que muestra al usuario vienen de la review de W-1
        # (PRIOS_W1 arriba). Los bullets de la semana corriente están alineados a
        # PRIOS_CURRENT porque el usuario ya vio esa propuesta durante la semana;
        # cuando cierre la review, va a fijar estas nuevas prioridades para la
        # semana siguiente.
        _ = PRIOS_CURRENT  # documentado arriba; no se persiste hasta cerrar la review

        db.commit()
        print(f"Seed listo: {EMAIL} / {PASSWORD}")
        for offset, label in (
            (5, "cerrada"),
            (4, "cerrada"),
            (3, "cerrada"),
            (2, "cerrada"),
            (1, "cerrada"),
            (0, "actual (lun-vie, sin review)"),
        ):
            iso = mondays[offset].isocalendar()
            print(f"  {iso.year}-W{iso.week:02d} ({label})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
