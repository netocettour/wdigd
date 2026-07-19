from pathlib import Path

from fastapi.templating import Jinja2Templates

_STATIC = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def asset_version(rel_path: str) -> str:
    """Sello de versión (mtime) para cache-busting de estáticos."""
    try:
        return str(int((_STATIC / rel_path).stat().st_mtime))
    except OSError:
        return "0"


templates.env.globals["asset_version"] = asset_version

# (clave almacenada, etiqueta visible) — orden y nombres tomados de los prototipos
templates.env.globals["CATEGORIES"] = [
    ("logro", "Logro"),
    ("avance", "Avance"),
    ("desbloqueo", "Desbloqueo"),
]
