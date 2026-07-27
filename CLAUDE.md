# wdigd

App de journaling semanal con dos ritmos: captura diaria (¿qué lograste hoy?) y sesión semanal de reflexión. Leer `docs/plan-mvp-journaling.md` para el contexto completo del producto, el método, el modelo de datos y las reglas de negocio. `README.md` tiene el setup local y el mapa del código.

**Estado:** MVP completo (F1–F5) y en producción en Railway. Lo que sigue son mejoras sueltas sobre una app en uso real, no fases.

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL (SQLite en local)
- Frontend server-rendered: Jinja2 + HTMX, CSS propio sin framework ni build step
- Auth: cookie de sesión firmada (SessionMiddleware) + bcrypt (passlib)
- Deploy: Railway con Postgres administrado
- Config por variables de entorno: `DATABASE_URL`, `SECRET_KEY`, `SECURE_COOKIES`

## Estructura del proyecto

```
app/
  main.py             app FastAPI, sesión, redirect de login (LoginRequired)
  config.py           settings desde variables de entorno
  db.py               engine, sessionmaker, Base, get_db
  deps.py             get_current_user
  security.py         contraseñas
  users.py            búsqueda de usuarios por email
  weeks.py            fechas, semanas ISO, timezone del usuario
  capture.py          lectura de bullets y parseo del campo de captura
  priorities.py       qué prioridades rigen cada semana
  observations.py     bloque 2 de la sesión semanal
  week_material.py    bloques 1-3 de la sesión semanal (fragmento HTMX)
  templating.py       Jinja: globals, filtros, cache-busting
  models/
  routers/            auth, today, entries, week, history, settings
  templates/
    base.html
    components/       # fragmentos HTMX reutilizables
    pages/
  static/
    css/ js/
alembic/
docs/
  designs/            # prototipos visuales (HTML estático) — fuente de verdad
  plan-mvp-journaling.md
  deploy-railway.md
seed.py               # genera varias semanas de datos ficticios
README.md
CLAUDE.md
```

## Convenciones de código

- **Los routers son glue HTTP.** Validan, delegan y devuelven un template. Si una función de router pasa de ~30 líneas o arma estructuras de datos para la vista, eso va a un módulo plano de `app/`.
- **Un solo lugar por concepto.** Las categorías salen de `models/entry.py`, el largo mínimo de contraseña de `security.py`, el formato `2026-W31` de `weeks.format_iso_week`, la timezone default de `models/user.py`. No duplicar constantes ni queries.
- **Los datos del formulario se declaran con `Form(...)`**, no se leen a mano de `request.form()`. Para PATCH parciales, `str | None = Form(None)`: `None` es "el campo no vino", `""` es "vino vacío".
- **Identificadores en inglés, texto de interfaz en castellano.** Las claves de contexto que consumen los templates también en inglés (`priorities`, `rows`, `observations`).
- **Nada de `except Exception`.** Capturar la excepción concreta.
- **JS:** `const`/`let`, funciones con prefijo `wdigd`, listeners delegados en `document`. Los handlers inline en templates son deliberados donde HTMX reemplaza el fragmento o hace falta frenar la propagación antes que htmx (chips de categoría, botón de alinear); está comentado en `app.js`.
- **CSS:** un solo bloque compartido para el marco de los campos, con `:where()` para no pelear especificidad. Sin estilos inline en templates.

## Diseño visual

Los archivos en `docs/designs/` son prototipos visuales (HTML estático de Claude Design) y **son la fuente de verdad del producto**: apariencia (colores, tipografía, layout, espaciado, breakpoints) y también copy, categorías, interacciones y flujo. Se diseñaron después del plan y representan mejor la intención. Cuando el plan y los prototipos difieran, ganan los prototipos. NO copiar el markup: implementar desde cero en templates Jinja2 + HTMX respetando lo que muestran los prototipos.

Diferencias ya resueltas a favor de los prototipos (por si el plan todavía sugiere lo viejo): categorías **Logro / Avance / Desbloqueo** (no logré/avancé/resolví); el "tema" de un bullet es **alineación con una prioridad de la semana**, no un tema de texto libre (no hay tabla `topics`); títulos de la sesión "Resumen de la semana", "Highlights de la semana", "Journal semanal"; días capturados sobre **7**.

El bloque "Preocupaciones y seguimientos" **se sacó del producto** después de usarlo. La tabla `review_items` y su modelo quedan para no perder lo escrito, pero ninguna pantalla los usa: no reintroducirlos.

Diseño mobile-first y responsive. Personalidad visual: más cuaderno que dashboard. Calma, foco, sobriedad. Tipografía protagonista, mucho aire.

## Principios de producto (no negociables)

1. **La app cuenta y ordena; el usuario juzga y sintetiza.** Ninguna función genera texto reflexivo, resume ni interpreta por el usuario.
2. **La captura diaria es sagrada en su simpleza.** Categoría y alineación con prioridades son siempre opcionales. Un bullet sin categorizar se ve completo, no pendiente.
3. **Los números nunca juzgan.** Ratios y datos se muestran en tono neutro. Prohibido rojo de alarma, íconos de advertencia, copy de reto. "Capturaste 4 de 7 días" se muestra igual que "7 de 7".

## Idioma de la interfaz

Voseo rioplatense, directo y sin entusiasmo artificial. Ejemplos: "¿Qué lograste hoy?", "Cerrar la semana", "Todavía no capturaste nada hoy", "alinear con prioridades". Sin signos de exclamación innecesarios. Nota: los prototipos usan algunos anglicismos que ya son parte de la voz ("Highlights", "Journal semanal"); respetarlos.

## Cómo trabajar

El MVP está terminado y en uso. Las fases F1–F5 del plan quedaron cerradas; ahora se trabaja por mejoras chicas y verificables sobre una app en producción. Si algo no está definido en el plan ni en los prototipos, preguntar antes de inventar.

Verificar los cambios corriendo la app (`uvicorn app.main:app --reload` con `python seed.py` de por medio), no sólo leyendo el diff. No hay suite de tests automatizados todavía.

## Fuera de alcance

Sin LLM en ningún punto. Sin notificaciones ni recordatorios. Sin streaks ni gamificación. Sin exportación. Sin apps nativas. Sin integraciones. Sin resumen automático. Sin OAuth. Sin roles ni equipos. Sin SPA ni build de frontend separado. Si durante la implementación aparece la tentación de agregar algo de esta lista, la respuesta es no.

## Comandos útiles

```bash
# Dev server
uvicorn app.main:app --reload

# Migraciones
alembic revision --autogenerate -m "descripcion"
alembic upgrade head

# Seed de datos de prueba
python seed.py
```
