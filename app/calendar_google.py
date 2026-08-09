"""Cliente mínimo para el OAuth 2.0 y la API de Google Calendar.

Funciones puras (no tocan DB). Los routers son responsables de persistir lo
que devuelven y de manejar los errores hacia la vista.
"""

from typing import Any
from urllib.parse import urlencode

import httpx

from app.config import settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "openid",
    "email",
]

HTTP_TIMEOUT = 5.0


class CalendarAuthError(Exception):
    """Falla del flujo OAuth (código inválido, refresh revocado, red caída).
    El router traduce esto a "reconectá" en la vista."""


def build_authorize_url(redirect_uri: str, state: str) -> str:
    """URL a la que redirigir al usuario para pedirle permiso a Google."""
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        # offline + prompt=consent asegura refresh_token en cada conexión.
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "include_granted_scopes": "true",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str, redirect_uri: str) -> dict[str, Any]:
    """Cambia el `code` del callback por tokens. Devuelve el JSON de Google
    (access_token, refresh_token, expires_in, id_token, scope, token_type)."""
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    return _post_token(data)


def refresh_access_token(refresh_token: str) -> str:
    """Pide un access_token nuevo a partir del refresh_token guardado."""
    data = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    payload = _post_token(data)
    token = payload.get("access_token")
    if not token:
        raise CalendarAuthError("La respuesta de Google no incluyó access_token.")
    return token


def get_user_email(access_token: str) -> str:
    """Trae el email de la cuenta que acaba de autorizar. Se usa una sola vez,
    en el callback, para etiquetar la conexión en /settings."""
    try:
        response = httpx.get(
            USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=HTTP_TIMEOUT,
        )
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise CalendarAuthError("Google no respondió a tiempo.") from exc
    except httpx.HTTPStatusError as exc:
        raise CalendarAuthError(
            f"Google devolvió {exc.response.status_code} al pedir el email."
        ) from exc
    except httpx.RequestError as exc:
        raise CalendarAuthError("No pudimos hablar con Google.") from exc
    email = response.json().get("email")
    if not email:
        raise CalendarAuthError("La respuesta de Google no incluyó email.")
    return email


def _post_token(data: dict[str, str]) -> dict[str, Any]:
    try:
        response = httpx.post(TOKEN_URL, data=data, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise CalendarAuthError("Google no respondió a tiempo.") from exc
    except httpx.HTTPStatusError as exc:
        # Google devuelve JSON con "error"/"error_description" en 4xx.
        detail = _error_detail(exc.response)
        raise CalendarAuthError(
            f"Google rechazó la petición ({exc.response.status_code}): {detail}"
        ) from exc
    except httpx.RequestError as exc:
        raise CalendarAuthError("No pudimos hablar con Google.") from exc
    return response.json()


def _error_detail(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:120]
    return body.get("error_description") or body.get("error") or "sin detalle"
