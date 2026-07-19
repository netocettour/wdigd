# wdigd

App de journaling semanal con dos ritmos: captura diaria (¿qué lograste hoy?) y sesión semanal de reflexión. Leer `docs/plan-mvp-journaling.md` para el contexto completo del producto, el método, el modelo de datos y las reglas de negocio.

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, PostgreSQL
- Frontend server-rendered: Jinja2 + HTMX, CSS propio sin framework (a lo sumo Pico.css como reset)
- Auth: cookie de sesión firmada (SessionMiddleware) + bcrypt (passlib)
- Deploy: Railway con Postgres administrado
- Config por variables de entorno: `DATABASE_URL`, `SECRET_KEY`

## Estructura del proyecto

```
app/
  main.py
  config.py
  models/
  routers/
  templates/
    base.html
    components/       # fragmentos HTMX reutilizables
    pages/
  static/
    css/
alembic/
docs/
  designs/            # prototipos visuales (HTML estático) — fuente de verdad
  plan-mvp-journaling.md
  deploy-railway.md
seed.py               # genera varias semanas de datos ficticios
CLAUDE.md
```

## Diseño visual

Los archivos en `docs/designs/` son prototipos visuales (HTML estático de Claude Design) y **son la fuente de verdad del producto**: apariencia (colores, tipografía, layout, espaciado, breakpoints) y también copy, categorías, interacciones y flujo. Se diseñaron después del plan y representan mejor la intención. Cuando el plan y los prototipos difieran, ganan los prototipos. NO copiar el markup: implementar desde cero en templates Jinja2 + HTMX respetando lo que muestran los prototipos.

Diferencias ya resueltas a favor de los prototipos (por si el plan todavía sugiere lo viejo): categorías **Logro / Avance / Desbloqueo** (no logré/avancé/resolví); el "tema" de un bullet es **alineación con una prioridad de la semana**, no un tema de texto libre (no hay tabla `topics`); títulos de la sesión "Resumen de la semana", "Highlights de la semana", "Journal semanal"; días capturados sobre **7**; recurrencia de review items por coincidencia de texto.

Diseño mobile-first y responsive. Personalidad visual: más cuaderno que dashboard. Calma, foco, sobriedad. Tipografía protagonista, mucho aire.

## Principios de producto (no negociables)

1. **La app cuenta y ordena; el usuario juzga y sintetiza.** Ninguna función genera texto reflexivo, resume ni interpreta por el usuario.
2. **La captura diaria es sagrada en su simpleza.** Categoría y alineación con prioridades son siempre opcionales. Un bullet sin categorizar se ve completo, no pendiente.
3. **Los números nunca juzgan.** Ratios y datos se muestran en tono neutro. Prohibido rojo de alarma, íconos de advertencia, copy de reto. "Capturaste 4 de 7 días" se muestra igual que "7 de 7".

## Idioma de la interfaz

Voseo rioplatense, directo y sin entusiasmo artificial. Ejemplos: "¿Qué lograste hoy?", "Cerrar la semana", "Todavía no capturaste nada hoy", "alinear con prioridades". Sin signos de exclamación innecesarios. Nota: los prototipos usan algunos anglicismos que ya son parte de la voz ("Highlights", "Journal semanal"); respetarlos.

## Fases de construcción

Hay 5 fases (F1–F5) definidas en `plan-mvp-journaling.md`, cada una con criterio de "listo". Trabajar fase por fase. No avanzar a la siguiente sin que se confirme explícitamente. Si algo no está definido en el plan, preguntar antes de inventar.

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
