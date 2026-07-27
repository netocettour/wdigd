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

        if self.secret_key == DEV_SECRET_KEY:
            logger.warning(
                "SECRET_KEY sin definir: se usa la clave de desarrollo. No deployar así."
            )


settings = Settings()
