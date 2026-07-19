from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.security import hash_password, verify_password
from app.templating import templates

router = APIRouter()

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


def _render(request, user, msgs=None, status_code=200):
    return templates.TemplateResponse(
        request,
        "pages/settings.html",
        {"user": user, "timezones": TIMEZONES, "msgs": msgs or {}},
        status_code=status_code,
    )


@router.get("/settings")
def settings_page(request: Request, user: User = Depends(get_current_user)):
    return _render(request, user)


@router.post("/settings/profile")
def update_profile(
    request: Request,
    email: str = Form(""),
    timezone: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    timezone = timezone.strip()
    if not email or "@" not in email:
        return _render(request, user, {"profile_error": "Ingresá un email válido."}, 400)
    try:
        ZoneInfo(timezone)
    except Exception:
        return _render(
            request, user, {"profile_error": "Esa zona horaria no existe."}, 400
        )
    taken = db.execute(
        select(User).where(func.lower(User.email) == email, User.id != user.id)
    ).scalar_one_or_none()
    if taken is not None:
        return _render(
            request, user, {"profile_error": "Ese email ya está registrado."}, 400
        )
    user.email = email
    user.timezone = timezone
    db.commit()
    return _render(request, user, {"profile_ok": "Listo."})


@router.post("/settings/password")
def update_password(
    request: Request,
    current: str = Form(""),
    new: str = Form(""),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(current, user.password_hash):
        return _render(
            request, user, {"password_error": "La contraseña actual no coincide."}, 400
        )
    if len(new) < 8:
        return _render(
            request,
            user,
            {"password_error": "La contraseña nueva necesita al menos 8 caracteres."},
            400,
        )
    user.password_hash = hash_password(new)
    db.commit()
    return _render(request, user, {"password_ok": "Listo."})
