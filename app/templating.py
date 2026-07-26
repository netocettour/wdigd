import re
from markupsafe import Markup
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

_UL_RE = re.compile(r"^[*\-•]\s+")
_OL_RE = re.compile(r"^\d+[.)]\s+")


def _format_narrative(text: str) -> str:
    if not text:
        return ""
    from markupsafe import escape
    lines = text.splitlines()
    parts: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _UL_RE.match(line):
            items = []
            while i < len(lines) and _UL_RE.match(lines[i]):
                items.append(str(escape(_UL_RE.sub("", lines[i]).strip())))
                i += 1
            parts.append("<ul>" + "".join(f"<li>{t}</li>" for t in items) + "</ul>")
        elif _OL_RE.match(line):
            items = []
            while i < len(lines) and _OL_RE.match(lines[i]):
                items.append(str(escape(_OL_RE.sub("", lines[i]).strip())))
                i += 1
            parts.append("<ol>" + "".join(f"<li>{t}</li>" for t in items) + "</ol>")
        else:
            parts.append(str(escape(line)) if line.strip() else "<br>")
            i += 1
    return "\n".join(parts)


templates.env.filters["narrative"] = lambda text: Markup(_format_narrative(text))
