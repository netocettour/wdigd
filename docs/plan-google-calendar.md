# Plan: integración con Google Calendar en `/today`

## Objetivo

Que el usuario, al capturar sus bullets del día, tenga visible el calendario de
Google como referencia — ver qué reuniones tuvo y qué tenía calendarizado, para
recordar sobre qué escribir. **Solo lectura, sin interacción con los bullets.**

Este feature abre dos puertas que el plan MVP tenía cerradas ("sin OAuth", "sin
integraciones"). Se confirmó el cambio de alcance antes de arrancar.

## Principios que se respetan

- **La app cuenta y ordena; el usuario juzga.** El calendario se muestra, no
  sugiere qué escribir. Nada de "convertir evento en bullet".
- **La captura sigue siendo sagrada.** El calendario es contexto lateral, no
  bloquea ni condiciona el flujo de captura.
- **Los números no juzgan.** Si un día no hay eventos, se muestra neutro
  ("Sin eventos hoy"), no como carencia.

## Modelo de datos

Dos tablas nuevas:

**`calendar_accounts`** — la cuenta OAuth conectada.

| campo             | tipo                    | notas                                        |
|-------------------|-------------------------|----------------------------------------------|
| id                | int PK                  |                                              |
| user_id           | FK users.id             | unique — un usuario, una cuenta de Google    |
| google_email      | str                     | para mostrar en /settings                    |
| refresh_token_enc | str                     | encriptado con Fernet(SECRET_KEY-derived)    |
| created_at        | datetime                |                                              |

**`calendar_sources`** — cada calendario individual de esa cuenta.

| campo              | tipo             | notas                                       |
|--------------------|------------------|---------------------------------------------|
| id                 | int PK           |                                             |
| account_id         | FK accounts.id   | cascade delete                              |
| google_calendar_id | str              | el id que devuelve Google (`primary`, etc.) |
| summary            | str              | nombre visible                              |
| background_color   | str              | hex, para el badge de color en la vista     |
| selected           | bool             | default true para el primario, false resto  |
| created_at         | datetime         |                                             |

No cacheamos eventos en DB. En cada carga de `/today` pedimos a Google los
eventos del día del usuario. Simplifica: sin worker de sync, sin cron, sin
tabla de eventos. Trade-off: si Google está caído, no hay calendario ese día
(mostramos estado neutro, no error rojo).

## Flujo OAuth

Nuevo router `app/routers/calendar.py`:

- `GET /calendar/connect` → construye URL de authorize con scopes
  `https://www.googleapis.com/auth/calendar.readonly` + `openid email`,
  `access_type=offline`, `prompt=consent` (para asegurar refresh_token en cada
  conexión), state firmado con `SECRET_KEY`. Redirect 302 a Google.
- `GET /calendar/callback` → recibe `code` y `state`, verifica state, cambia
  code por tokens, guarda `refresh_token` encriptado, pide lista de
  `calendarList`, crea `calendar_sources` (primary → selected=true), redirect
  a `/settings`.
- `POST /calendar/disconnect` → borra el `calendar_account` (cascade). No
  llamamos a Google para revocar (opcional, se puede agregar después).
- `POST /calendar/sources/{id}/toggle` → tildea/destildea un calendario.
  HTMX endpoint, devuelve el fragmento del checkbox.

Módulo plano `app/calendar_google.py`:
- `build_authorize_url(state) -> str`
- `exchange_code(code) -> tokens`
- `refresh_access_token(refresh_token) -> access_token`
- `list_calendars(access_token) -> list[Calendar]`
- `list_events_for_day(access_token, calendar_ids, day, tz) -> list[Event]`

Preferimos `httpx` directo antes que `google-api-python-client`: son 4-5 endpoints
HTTP simples, no vale traer una librería de 20MB.

Timeout de 5s en cada llamada. Si expira o falla, la vista muestra estado neutro
"No pudimos traer tu calendario ahora".

## Encriptación de refresh tokens

Módulo `app/crypto.py`:
- Key derivada de `SECRET_KEY` con HKDF, uso `cryptography.fernet.Fernet`.
- `encrypt(str) -> str`, `decrypt(str) -> str`.

Motivación: si la DB se lee (backup filtrado, dump), el refresh_token da acceso
a leer el calendario del usuario. Con Fernet queda inutilizable sin `SECRET_KEY`.
Costo: negligible.

**Cuidado operativo:** rotar `SECRET_KEY` en prod invalida todos los
refresh_tokens (los usuarios tienen que reconectar Google). Ya invalidaba las
sesiones — es consistente. Documentar en `deploy-railway.md`.

## Config nueva

Env vars en `app/config.py`:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI` — opcional; si no está, se construye desde `request.url_for("calendar_callback")`. Para prod (Railway) conviene fijarla explícita.

Google Cloud Console (fuera del código):
- Proyecto "wdigd"
- OAuth consent screen: External, "Testing" mode inicialmente (hasta 100
  usuarios sin verification, con banner "app no verificada")
- Credentials: OAuth Client ID tipo "Web application"
- Authorized redirect URIs: `http://localhost:8000/calendar/callback` y el de prod
- Scopes solicitados: `calendar.readonly`, `openid`, `email`

## Vista en `/today`

Fragmento nuevo `templates/components/calendar_day.html`, se incluye en
`pages/today.html`.

**Ubicación (Opción B, decisión tomada):** al pie de `/today`, después de los
bullets del día y antes de `Antes esta semana`. Mismo tratamiento tipográfico
que `Antes esta semana` — eyebrow en mayúsculas ("Tu día"), lista alineada, sin
card, sin borde, sin control. Se disuelve en el ritmo de la página en vez de
introducir un elemento visual nuevo.

**Layout:** columna única, mismo ancho de siempre, idéntico en mobile y desktop.
No hay timeline, no hay dos columnas, no hay layout responsive nuevo. La
consistencia con el resto de la app es más importante que la densidad visual.

**Estados posibles:**
1. **No conectado** → el bloque `Tu día` no aparece en absoluto. La entrada
   para conectar vive solo en `/settings`. Un usuario sin Google Calendar no
   ve ninguna diferencia respecto de hoy.
2. **Conectado, sin eventos hoy** → "Sin eventos hoy" en tono neutro, mismo
   eyebrow arriba. Nunca es carencia, es dato.
3. **Conectado, con eventos** → lista: hora + barrita de color (3px, lateral) +
   título. Un renglón por evento.
4. **Conectado, error de fetch o timeout** → "No pudimos traer tu calendario
   ahora" con el mismo eyebrow. El resto de `/today` funciona igual.

**Contenido por evento:** hora de inicio (HH:MM en tz del usuario), barrita
lateral del color del calendario, título. Nada más. Sin duración, sin
descripción, sin asistentes — la lista tiene que ser scaneable en una pasada.

**Colores:** usar `background_color` del calendario (viene de Google) para la
barrita lateral. Sin fondo saturado — respetamos la paleta calma de la app, el
color es marca, no manchón. Al abrir la lista de calendarios en `/settings` se
ve el swatch al lado de cada uno.

**All-day events:** dentro del mismo bloque, arriba de los eventos con hora,
sin timestamp — solo barrita de color + título. Si hay ≥3 all-day se agrupan
como chips en una fila; si hay 1-2 van como renglones normales sin hora.

## Settings

Nueva sección en `/settings`, después de las prioridades:

**Google Calendar**
- Si no conectado: descripción corta + botón "Conectar Google Calendar" que
  hace `GET /calendar/connect`.
- Si conectado: `email conectado` en gris, lista de calendarios con checkboxes
  (HTMX toggle instantáneo), botón "Desconectar" al final.

## Carga asíncrona (decisión tomada)

`/today` **no debe** llamar a Google en el request principal. Hoy la página
rinde en ~50 ms (una query a Postgres); una llamada a la API de Google agrega
200-500 ms en un día bueno y 1-2 s en un día malo, triplicando la latencia
percibida de la pantalla más usada de la app. Es un costo inaceptable en la
puerta de entrada.

**Patrón:** el fragmento del calendario se pide en un segundo request vía HTMX,
después de que la página ya se pintó.

- En `today.html`, en la posición donde va el bloque (al pie, antes de
  `Antes esta semana`), se renderiza un placeholder vacío:
  ```html
  <div hx-get="/today/calendar" hx-trigger="load" hx-swap="outerHTML"></div>
  ```
- Nuevo endpoint `GET /today/calendar` en `app/routers/today.py`. Hace la
  llamada a Google (con refresh de token si hace falta), renderiza
  `components/calendar_day.html` y devuelve el fragmento. Es el único punto de
  código que espera a Google.
- **Sin skeleton visible.** El bloque simplemente no existe hasta que llega —
  aparece sin animación. Es al pie de la página; en la mayoría de los casos el
  usuario ni lo ve cargar.
- **Timeout de 5 s** en la llamada a Google. Si expira, el fragmento devuelve
  el estado de error.
- **Solo se llama si el usuario está conectado.** Si `calendar_account` es
  `None`, `today.html` no incluye el placeholder — cero requests extra.

Trade-off aceptado: el calendario aparece con un pequeño delay respecto del
resto de la página. Como está al pie y es contexto, no ancla — no molesta.

Ya existe `user.timezone` (default `America/Argentina/Buenos_Aires`). Lo usamos
para:
- Calcular el rango del día que se pide a Google
  (`timeMin`/`timeMax` en RFC3339 con offset de la tz del usuario)
- Renderizar horas de eventos en la tz del usuario

Google Calendar API acepta `singleEvents=true` para expandir recurrentes en
instancias — usamos eso.

## Migraciones

Un `alembic revision --autogenerate -m "google calendar accounts and sources"`
después de crear los modelos.

## Dependencias nuevas

En `requirements.txt`:
- `httpx` (probablemente ya está transitivo, agregar explícito)
- `cryptography` (Fernet)

## Orden de implementación (PRs chicos y reviewables)

**PR 1 — Fundación OAuth (invisible al usuario)**
- Config + env vars, doc de setup en Google Cloud
- `app/crypto.py` con Fernet
- Modelos + migración
- `app/calendar_google.py` con OAuth flow básico (authorize URL, exchange, refresh)
- `app/routers/calendar.py`: `/connect`, `/callback`, `/disconnect`
- UI mínima en `/settings`: botón conectar + estado + botón desconectar

**PR 2 — Selección de calendarios**
- Fetch de lista y creación de `calendar_sources` en el callback
- UI de checkboxes en `/settings` con HTMX toggle
- Endpoint `POST /calendar/sources/{id}/toggle`

**PR 3 — Vista en `/today` con carga async**
- `list_events_for_day` en `app/calendar_google.py`
- Nuevo endpoint `GET /today/calendar` que hace la llamada y devuelve el fragmento
- Fragmento `components/calendar_day.html` con lista + estados (sin eventos, error)
- `today.html`: placeholder HTMX al pie, solo si el usuario está conectado
- Manejo de timeout (5 s) y errores como estado neutro

Con PR 3 la ficha queda completa. Al ser layout de columna única sin timeline
ni responsive extra, no hay un PR 4 — la simplicidad de la Opción B lo evita.

## Fuera de alcance de esta ficha

- Crear/editar eventos desde la app.
- Convertir evento en bullet (click → prellenar campo).
- Otros proveedores (Outlook, Apple Calendar). Si aparece, se piensa aparte.
- Notificaciones o recordatorios basados en eventos.
- Vista del calendario en `/week` o `/history`.
- Sync bidireccional o cacheado de eventos.
- Verification process de Google (se hace si algún día pasa de uso personal).

## Riesgos y notas

- **Google verification:** en modo "Testing" hasta 100 usuarios sin problema,
  con banner "app no verificada" al conectar. Si se abre a más gente hay que
  hacer el proceso (semanas de ida y vuelta con Google).
- **Rate limits:** 1M queries/día del calendar API. No vamos a llegar.
- **Refresh token pérdida:** si Google invalida el refresh_token (usuario
  cambió password, revocó desde su cuenta, 6 meses sin uso), tratar como
  desconexión y mostrar mensaje de reconectar.
- **Tokens en logs:** cuidado de no loguear `refresh_token` ni `access_token`
  ni siquiera en debug.
