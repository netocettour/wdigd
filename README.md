# wdigd

App personal de journaling semanal con dos ritmos: una captura diaria de tres
líneas (*what did I get done*) y una sesión semanal que junta ese material, lo
ordena y acompaña la síntesis hacia la semana siguiente.

La app cuenta y ordena; el usuario juzga y sintetiza. No hay LLM, ni resúmenes
automáticos, ni streaks, ni notificaciones.

- Método, modelo de datos y reglas: [docs/plan-mvp-journaling.md](docs/plan-mvp-journaling.md)
- Prototipos visuales (fuente de verdad del diseño): [docs/designs/](docs/designs/)
- Deploy: [docs/deploy-railway.md](docs/deploy-railway.md)
- Convenciones para trabajar en el repo: [CLAUDE.md](CLAUDE.md)

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL (SQLite en local).
Frontend server-rendered con Jinja2 + HTMX y CSS propio, sin build step.

## Correr en local

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Sin `DATABASE_URL` usa SQLite en `./wdigd.db`. Sin `SECRET_KEY` arranca con una
clave de desarrollo y avisa por log.

Datos de prueba (cuatro semanas, dos reviews cerradas, una a medias):

```bash
python seed.py
```

Deja el usuario `demo@wdigd.local` con contraseña `demo1234`. No usarlo en
producción.

## Variables de entorno

| Variable | Default | Para qué |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./wdigd.db` | Base. Se normaliza `postgres://` → `postgresql://`. |
| `SECRET_KEY` | clave de desarrollo | Firma la cookie de sesión. Obligatoria en producción. |
| `SECURE_COOKIES` | `false` | `true` en producción: cookie de sesión sólo por HTTPS. |

## Mapa del código

```
app/
  main.py            app FastAPI, middleware de sesión, redirect de login
  config.py          settings desde variables de entorno
  db.py              engine, sessionmaker, Base, dependencia get_db
  deps.py            get_current_user y la excepción LoginRequired
  security.py        hash y verificación de contraseñas
  users.py           búsqueda de usuarios por email
  weeks.py           fechas, semanas ISO y timezone del usuario
  capture.py         lectura de bullets y parseo del campo de captura
  priorities.py      qué prioridades rigen cada semana
  observations.py    bloque 2 de la sesión semanal, calculado al vuelo
  week_material.py   bloques 1-3 de la sesión semanal (fragmento HTMX)
  templating.py      Jinja: globals, filtros, cache-busting
  models/            User, Entry, WeeklyReview, Achievement, DailyNote
  routers/           auth, today, entries, week, history, settings
  templates/         base, pages/, components/
  static/            css/main.css, js/app.js
alembic/             migraciones
seed.py              datos ficticios para desarrollo
```

Los routers son glue HTTP: validan, delegan en los módulos de dominio y
devuelven un template. La lógica que se comparte entre pantallas vive en los
módulos planos de `app/`.

## Migraciones

```bash
alembic revision --autogenerate -m "descripcion"
alembic upgrade head
```
