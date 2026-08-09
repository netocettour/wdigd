from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.db import get_db
from app.deps import get_current_user
from app.models import CalendarAccount, User
from app.security import MIN_PASSWORD_LENGTH, hash_password, verify_password
from app.templating import templates
from app.users import find_by_email, is_valid_email, normalize_email
from app.weeks import valid_timezone

router = APIRouter()

# Atajos del datalist; el campo acepta cualquier zona válida de la IANA.
TIMEZONES = [
    "America/Argentina/Cordoba",
    "America/Argentina/Buenos_Aires",
    "America/Montevideo",
    "America/Santiago",
    "America/Sao_Paulo",
    "America/Bogota",
    "America/Lima",
    "America/Mexico_City",
    "America/New_York",
    "America/Los_Angeles",
    "Europe/Madrid",
    "Europe/London",
    "UTC",
]


CALENDAR_ERROR_MESSAGES = {
    "cancelado": "Cancelaste la conexión con Google. No pasa nada.",
    "fallo": "No pudimos conectar con Google. Probá de nuevo.",
}


def _render(
    request: Request,
    user: User,
    db: Session,
    msgs: dict[str, str] | None = None,
    status_code: int = 200,
):
    calendar_account = (
        db.query(CalendarAccount).filter_by(user_id=user.id).one_or_none()
    )
    return templates.TemplateResponse(
        request,
        "pages/settings.html",
        {
            "user": user,
            "timezones": TIMEZONES,
            "msgs": msgs or {},
            "calendar_account": calendar_account,
            "calendar_oauth_configured": app_settings.google_oauth_configured,
        },
        status_code=status_code,
    )


@router.get("/settings")
def settings_page(
    request: Request,
    calendar_ok: str | None = None,
    calendar_error: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msgs: dict[str, str] = {}
    if calendar_ok:
        msgs["calendar_ok"] = "Google Calendar conectado."
    if calendar_error:
        msgs["calendar_error"] = CALENDAR_ERROR_MESSAGES.get(
            calendar_error, "Algo salió mal con la conexión."
        )
    return _render(request, user, db, msgs)


@router.post("/settings/profile")
def update_profile(
    request: Request,
    email: str = Form(""),
    timezone: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email = normalize_email(email)
    timezone = timezone.strip()

    error = None
    if not is_valid_email(email):
        error = "Ingresá un email válido."
    elif not valid_timezone(timezone):
        error = "Esa zona horaria no existe."
    elif find_by_email(db, email, exclude_id=user.id) is not None:
        error = "Ese email ya está registrado."
    if error:
        return _render(request, user, db, {"profile_error": error}, 400)

    user.email = email
    user.timezone = timezone
    db.commit()
    return _render(request, user, db, {"profile_ok": "Listo."})


@router.post("/settings/password")
def update_password(
    request: Request,
    current: str = Form(""),
    new: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    error = None
    if not verify_password(current, user.password_hash):
        error = "La contraseña actual no coincide."
    elif len(new) < MIN_PASSWORD_LENGTH:
        error = f"La contraseña nueva necesita al menos {MIN_PASSWORD_LENGTH} caracteres."
    if error:
        return _render(request, user, db, {"password_error": error}, 400)

    user.password_hash = hash_password(new)
    db.commit()
    return _render(request, user, db, {"password_ok": "Listo."})
