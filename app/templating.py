"""Configuración de Jinja: globals, filtros y cache-busting de los estáticos."""

import re
from pathlib import Path

from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape

from app.models import CATEGORY_LABELS, CATEGORY_VALUES
from app.security import MIN_PASSWORD_LENGTH

_APP_DIR = Path(__file__).parent
_STATIC_DIR = _APP_DIR / "static"

templates = Jinja2Templates(directory=str(_APP_DIR / "templates"))


def asset_version(rel_path: str) -> str:
    """Sello de versión (mtime) para cache-busting de estáticos."""
    try:
        return str(int((_STATIC_DIR / rel_path).stat().st_mtime))
    except OSError:
        return "0"


# — Filtro `narrative`: texto plano del journal a HTML —

_UL_ITEM = re.compile(r"^[*\-•]\s+")
_OL_ITEM = re.compile(r"^\d+[.)]\s+")


def _list_block(lines: list[str], start: int, item_re: re.Pattern, tag: str) -> tuple[str, int]:
    """Toma las líneas consecutivas que son ítems y las devuelve como <ul>/<ol>."""
    items = []
    i = start
    while i < len(lines) and item_re.match(lines[i]):
        items.append(escape(item_re.sub("", lines[i]).strip()))
        i += 1
    return f"<{tag}>" + "".join(f"<li>{item}</li>" for item in items) + f"</{tag}>", i


def narrative(text: str) -> Markup:
    """Respeta las listas que el usuario escribió y escapa todo lo demás."""
    lines = (text or "").splitlines()
    parts: list[str] = []
    i = 0
    while i < len(lines):
        if _UL_ITEM.match(lines[i]):
            block, i = _list_block(lines, i, _UL_ITEM, "ul")
            parts.append(block)
        elif _OL_ITEM.match(lines[i]):
            block, i = _list_block(lines, i, _OL_ITEM, "ol")
            parts.append(block)
        else:
            parts.append(str(escape(lines[i])) if lines[i].strip() else "<br>")
            i += 1
    return Markup("\n".join(parts))


templates.env.globals.update(
    asset_version=asset_version,
    # (clave almacenada, etiqueta visible) — orden y nombres tomados de los prototipos
    CATEGORIES=[(value, CATEGORY_LABELS[value]) for value in CATEGORY_VALUES],
    MIN_PASSWORD_LENGTH=MIN_PASSWORD_LENGTH,
)
templates.env.filters["narrative"] = narrative
