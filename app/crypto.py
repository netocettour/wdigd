"""Encriptación simétrica para secretos que viven en la DB.

Uso actual: `refresh_token` de OAuth de Google. La clave sale de `SECRET_KEY`
via HKDF, así que rotar `SECRET_KEY` invalida los tokens encriptados y los
usuarios tienen que reconectar. Ya invalidaba las sesiones — es consistente.
"""

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.config import settings

_HKDF_INFO = b"wdigd:secretbox:v1"


def _derive_key() -> bytes:
    # HKDF-SHA256 → 32 bytes → base64url para el formato que espera Fernet.
    raw = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=_HKDF_INFO,
    ).derive(settings.secret_key.encode("utf-8"))
    return base64.urlsafe_b64encode(raw)


_fernet = Fernet(_derive_key())


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str) -> str:
    """Devuelve el texto original. Lanza `InvalidToken` si SECRET_KEY cambió
    o si el ciphertext fue manipulado."""
    return _fernet.decrypt(token.encode("ascii")).decode("utf-8")


__all__ = ["encrypt", "decrypt", "InvalidToken"]
