"""Endpoints del OAuth con Google Calendar. Ver docs/plan-google-calendar.md."""

import logging
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from app.calendar_google import (
    CalendarAuthError,
    build_authorize_url,
    exchange_code,
    get_user_email,
)
from app.config import settings
from app.crypto import encrypt
from app.db import get_db
from app.deps import get_current_user
from app.models import CalendarAccount, User

logger = logging.getLogger(__name__)
router = APIRouter()

STATE_SALT = "wdigd:calendar-oauth"
STATE_MAX_AGE = 600  # 10 minutos

_serializer = URLSafeTimedSerializer(settings.secret_key, salt=STATE_SALT)


def _redirect_uri(request: Request) -> str:
    """URI exacto al que Google va a redirigir. Tiene que coincidir con el que
    está registrado en Google Cloud."""
    if settings.google_redirect_uri:
        return settings.google_redirect_uri
    return str(request.url_for("calendar_callback"))


def _sign_state(user_id: int) -> str:
    # Nonce aleatorio para que dos redirects consecutivos del mismo usuario
    # tengan states distintos.
    return _serializer.dumps({"uid": user_id, "n": secrets.token_urlsafe(8)})


def _verify_state(token: str, user_id: int) -> None:
    try:
        payload = _serializer.loads(token, max_age=STATE_MAX_AGE)
    except SignatureExpired as exc:
        raise HTTPException(400, "El pedido de conexión expiró. Probá de nuevo.") from exc
    except BadSignature as exc:
        raise HTTPException(400, "State inválido.") from exc
    if payload.get("uid") != user_id:
        raise HTTPException(400, "State no corresponde a este usuario.")


@router.get("/calendar/connect")
def calendar_connect(
    request: Request,
    user: User = Depends(get_current_user),
):
    if not settings.google_oauth_configured:
        raise HTTPException(503, "Google Calendar no está configurado en este deploy.")
    state = _sign_state(user.id)
    url = build_authorize_url(_redirect_uri(request), state)
    return RedirectResponse(url, status_code=303)


@router.get("/calendar/callback", name="calendar_callback")
def calendar_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if error:
        # El usuario canceló la pantalla de consentimiento u otro error de Google.
        return RedirectResponse("/settings?calendar_error=cancelado", status_code=303)
    if not code or not state:
        raise HTTPException(400, "Faltan parámetros del callback.")

    _verify_state(state, user.id)

    try:
        tokens = exchange_code(code, _redirect_uri(request))
        refresh_token = tokens.get("refresh_token")
        access_token = tokens.get("access_token")
        if not refresh_token or not access_token:
            raise CalendarAuthError("Google no devolvió los tokens esperados.")
        email = get_user_email(access_token)
    except CalendarAuthError as exc:
        logger.warning("OAuth con Google falló para user %s: %s", user.id, exc)
        return RedirectResponse("/settings?calendar_error=fallo", status_code=303)

    # Un usuario, una cuenta: si ya había una, la reemplazamos limpiamente.
    existing = db.query(CalendarAccount).filter_by(user_id=user.id).one_or_none()
    if existing is not None:
        db.delete(existing)
        db.flush()

    account = CalendarAccount(
        user_id=user.id,
        google_email=email,
        refresh_token_enc=encrypt(refresh_token),
    )
    db.add(account)
    db.commit()

    return RedirectResponse("/settings?calendar_ok=1", status_code=303)


@router.post("/calendar/disconnect")
def calendar_disconnect(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    account = db.query(CalendarAccount).filter_by(user_id=user.id).one_or_none()
    if account is not None:
        db.delete(account)
        db.commit()
    return RedirectResponse("/settings", status_code=303)
