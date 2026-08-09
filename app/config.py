"""Configuración por variables de entorno. Ver docs/deploy-railway.md."""

import logging
import os

logger = logging.getLogger(__name__)

DEV_SECRET_KEY = "dev-secret-cambiame-en-produccion"
DEFAULT_DATABASE_URL = "sqlite:///./wdigd.db"

_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    return default if raw is None else raw.strip().lower() in _TRUE_VALUES


def _normalize_database_url(url: str) -> str:
    # Railway entrega postgres://; SQLAlchemy 2.x exige postgresql://
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


class Settings:
    """Se lee una sola vez, al importar el módulo."""

    def __init__(self) -> None:
        self.secret_key: str = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)
        self.database_url: str = _normalize_database_url(
            os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
        )
        # Cookie de sesión sólo por HTTPS: prender en producción.
        self.secure_cookies: bool = _env_flag("SECURE_COOKIES")

        # Google Calendar OAuth. Vacío = feature deshabilitado (la UI de conectar
        # no se muestra). Ver docs/google-cloud-setup.md.
        self.google_client_id: str = os.environ.get("GOOGLE_CLIENT_ID", "")
        self.google_client_secret: str = os.environ.get("GOOGLE_CLIENT_SECRET", "")
        # Opcional: si no se define, el router lo arma con request.url_for.
        self.google_redirect_uri: str = os.environ.get("GOOGLE_REDIRECT_URI", "")

        if self.secret_key == DEV_SECRET_KEY:
            logger.warning(
                "SECRET_KEY sin definir: se usa la clave de desarrollo. No deployar así."
            )

    @property
    def google_oauth_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


settings = Settings()
