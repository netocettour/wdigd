# Plan de MVP — App de journaling semanal

*Documento de trabajo, v0.4 — julio 2026. Actualizado para reflejar los prototipos de `docs/designs/`, que son la fuente de verdad cuando difieren de este plan (categorías, alineación con prioridades, copy de la sesión semanal).*

## Qué es

Una aplicación personal de journaling que modela un método concreto: cinco capturas diarias en días laborables (WDIGD: *what did I get done*) y una sesión semanal que reúne ese material, lo pone sobre la mesa y acompaña la síntesis y la reflexión hacia la semana siguiente. Nace como herramienta de uso propio, pero se construye desde el día uno con arquitectura multiusuario para poder abrirla a otras personas más adelante.

## Principios de diseño

**La app cuenta y ordena; el usuario juzga y sintetiza.** La aplicación hace el trabajo mecánico —agrupar, contar, mostrar recurrencias, formular preguntas— y deja del lado del usuario todo el trabajo cognitivo valioso: leer los patrones, escribir la síntesis, decidir prioridades. Ninguna función del MVP genera texto reflexivo en nombre del usuario, y ninguna función lo tranquiliza ni interpreta su estado. Este principio filtra cualquier feature futura: si una idea implica que la app concluya por el usuario, queda afuera.

**La captura diaria es sagrada en su simpleza.** Las entradas diarias reales son listas planas de tres a cuatro bullets, sin categorías ni etiquetas. Cualquier campo obligatorio en la captura es fricción inventada que el método actual no tiene. Todo lo que pida clasificar, etiquetar o estructurar se muda a la sesión semanal, donde ese trabajo paga.

## El método que modela la app

**Ritmo diario (lunes a viernes).** Al final del día, el usuario responde una sola pregunta: ¿qué lograste hoy? Salen entre tres y seis bullets de texto libre, típicamente cortos. Categoría (Logro / Avance / Desbloqueo) y alineación con una prioridad de la semana son opcionales: un tap si sale natural, nada bloquea el guardado. La captura completa toma menos de dos minutos.

Las tres categorías codifican una distinción real: *Logro* es cierre —algo terminó o marcó el fin de una etapa—, *Avance* es empuje proactivo sobre un proceso que sigue abierto, y *Desbloqueo* es lo reactivo: incendios, pedidos, colaboraciones que destraban a otros. Las dos primeras son construcción; la tercera es defensa.

En lugar de un tema de texto libre, cada bullet puede *alinearse con una de las prioridades de la semana* (las que el usuario fijó el domingo anterior). Un tap cicla por las prioridades vigentes y vuelve a "sin alinear". Eso es todo el etiquetado que hay: no existen temas propios ni un catálogo de temas.

**Ritmo semanal (una sesión, típicamente domingo).** Cinco bloques en secuencia más un cierre:

1. **Resumen de la semana.** Todos los bullets de la semana, agrupados por la prioridad con la que el usuario los alineó, con día visible. Los que no empujan ninguna prioridad caen en un grupo aparte ("Fuera de las prioridades de la semana"), donde se pueden alinear de a un tap; los que ya están alineados y siguen sin categoría se categorizan acá. No es un resumen generado: es el material ordenado y un primer repaso obligado de lo que pasó.
2. **Observaciones.** Con la semana ordenada, números sin adjetivos: cuántos Logro / Avance / Desbloqueo, cuántos bullets quedaron fuera de las prioridades, ratio construcción/reacción (Logro + Avance contra Desbloqueo), qué prioridad tuvo más presencia, cuántos días se capturó (sobre 7), y qué prioridades llevan varias semanas acumulando "Avance" sin ningún "Logro". La app presenta los datos y se calla.
3. **Highlights de la semana.** Mecánica de promoción: el usuario toca la estrella de un bullet del bloque 1 y lo promueve a highlight, pudiendo reescribir el texto en limpio. No se escriben highlights de cero: siempre nacen de un bullet. El horizonte semanal convierte avances sueltos en highlights con nombre.
4. **Journal semanal.** Texto libre, sin estructura impuesta y sin límite, para el análisis de fondo: cómo se movió el panorama, diagnósticos, escenarios, estado de ánimo. Lleva un subtítulo fijo que enmarca sobre qué escribir (ritmo de trabajo diario, interacciones importantes, enfoque estratégico), pero la app no genera ni sugiere contenido: solo espacio.
5. **Preocupaciones y seguimientos.** Dos listas separadas de texto plano: las *preocupaciones* son señales con carga emocional —miedos, riesgos que pesan— y tienen un prompt fijo de apertura ("¿de qué tenés miedo esta semana?"); los *seguimientos* son ítems operativos a los que hay que estarles atrás. En semanas siguientes, la app muestra si un ítem casi idéntico ya venía apareciendo, sin rotularlo. El cruce con prioridades lo hace el usuario a mano.
6. **Cierre — Prioridades.** Campo de texto libre para la semana entrante, una prioridad por línea. El lunes siguiente aparecen en la pantalla de captura diaria (y son las prioridades con las que se alinean los bullets de esa semana), sin más comentario.

---

# Especificación de implementación

## Stack (fijado)

Backend en **Python 3.12 + FastAPI**, ORM **SQLAlchemy 2.x** con migraciones **Alembic**, base **PostgreSQL** (en desarrollo puede ser SQLite con dialecto compatible, pero apuntar a Postgres desde el arranque). Frontend **server-rendered con Jinja2 + HTMX**; CSS propio y mínimo, sin framework pesado (a lo sumo Pico.css o similar), diseño responsive mobile-first porque la captura ocurre mitad en teléfono. Autenticación con **cookie de sesión firmada** (starlette SessionMiddleware) y contraseñas con **bcrypt** (passlib). Deploy en **Railway** con Postgres administrado; configuración por variables de entorno (`DATABASE_URL`, `SECRET_KEY`). Sin OAuth, sin API pública, sin SPA, sin cola de tareas: una sola pieza desplegable.

## Mapa de rutas

| Ruta | Qué es |
|---|---|
| `GET/POST /signup`, `/login`, `POST /logout` | Auth básica |
| `GET /today` | Pantalla principal: captura del día + prioridades de la semana vigente visibles arriba |
| `POST /entries` | Crear bullet (texto; categoría opcional) |
| `PATCH /entries/{id}`, `DELETE /entries/{id}` | Editar / categorizar / borrar bullet |
| `POST /entries/{id}/align` | Ciclar la alineación del bullet con las prioridades de su semana |
| `GET /week/{iso_week}` | Sesión semanal (los 6 bloques en una página, navegable por anclas) |
| `POST /week/{iso_week}/close`, `POST /week/{iso_week}/reopen` | Cerrar / reabrir la review |
| `POST /achievements`, `PATCH`, `DELETE` | Promoción de highlights (siempre desde un bullet) |
| `POST /review-items`, `DELETE` | Preocupaciones y seguimientos (texto plano) |
| `PATCH /week/{iso_week}` | Guardar journal y prioridades (autosave vía HTMX) |
| `GET /history` | Lista de semanas pasadas; cada una linkea a su `/week/{iso_week}` |
| `GET /settings`, `POST /settings/profile`, `POST /settings/password` | Timezone, email, cambio de contraseña |

Interacciones parciales (agregar bullet, categorizar de a un tap, alinear con una prioridad, promover un highlight) van por HTMX contra estos mismos endpoints, devolviendo fragmentos.

## Modelo de datos

No hay tabla `topics`: la única forma de agrupar un bullet es alinearlo con una prioridad de la semana, que se guarda como texto en el propio bullet.

```
users            id PK · email UNIQUE NOT NULL · password_hash NOT NULL ·
                 timezone NOT NULL DEFAULT 'America/Argentina/Cordoba' · created_at

entries          id PK · user_id FK · entry_date DATE NOT NULL ·
                 text TEXT NOT NULL · category ENUM('logro','avance','desbloqueo') NULL ·
                 priority_label VARCHAR NULL · position INT · created_at · updated_at
                 (priority_label = la prioridad con la que el usuario alineó el bullet)

weekly_reviews   id PK · user_id FK · iso_year INT · iso_week INT ·
                 narrative TEXT DEFAULT '' · priorities TEXT DEFAULT '' ·
                 closed_at TIMESTAMPTZ NULL · UNIQUE(user_id, iso_year, iso_week)

achievements     id PK · weekly_review_id FK · text NOT NULL · position INT

achievement_entries   achievement_id FK · entry_id FK · PK(ambas)
                      (referencia al bullet de origen; un highlight siempre nace de uno)

review_items     id PK · user_id FK · weekly_review_id FK ·
                 kind ENUM('preocupacion','seguimiento') · text NOT NULL · position INT
```

Las prioridades vigentes de una semana salen de la última review cerrada previa a esa semana (`priorities`, una por línea). Las observaciones no se persisten: se calculan al vuelo sobre `entries` de la semana (y de las N semanas previas para detectar "Avance sin Logro" por prioridad).

## Reglas de negocio y casos borde

- **Semana:** lunes a domingo, definida por la timezone del usuario. La `weekly_review` se crea lazy la primera vez que el usuario visita `/week/{iso_week}`.
- **La review nunca se bloquea.** "Cerrar" setea `closed_at` y cambia la vista a modo lectura, pero un botón "reabrir" la vuelve editable (limpia `closed_at`). Sin permisos ni estados complejos: es una herramienta personal, el usuario manda.
- **Los entries son editables siempre**, incluso de semanas cerradas. Las observaciones se recalculan al vuelo, así que no hay nada que invalidar.
- **Días sin captura:** la sesión semanal lo señala como dato neutro ("Capturaste 6 de 7 días"), sin color de alarma ni copy de reto.
- **Semana sin review:** el historial la muestra como "sin sesión", consultable igual (se ven los bullets).
- **Prioridades vigentes:** en `/today` se muestran las prioridades de la review de la semana *anterior* (la última cerrada, si la inmediata anterior no se cerró). Son las mismas prioridades con las que se alinean los bullets de esa semana.
- **Alineación con prioridades:** un bullet se alinea con una de las prioridades vigentes de su semana; se guarda la etiqueta de texto. Un tap cicla por las prioridades y vuelve a "sin alinear". Sin catálogo de temas ni pantalla de administración.
- **Detección de recurrencia** de preocupaciones/seguimientos: por coincidencia de texto casi idéntico (normalizado) con ítems del mismo tipo en reviews anteriores. Nada semántico, sin LLM.
- **Zona horaria:** el "día" de un entry es el día local del usuario al momento de crear (calculado server-side con su timezone); editable por si captura pasada la medianoche.

## Orden de construcción

Cinco fases, cada una termina en algo usable:

**F1 — Esqueleto y auth.** Proyecto FastAPI con estructura de carpetas (`app/routers`, `app/models`, `app/templates`), Alembic inicializado, signup/login/logout, layout base responsive. *Listo cuando:* puedo crear una cuenta, loguearme y ver una pantalla vacía protegida.

**F2 — Captura diaria.** `/today` completo: agregar/editar/borrar bullets, categoría opcional de un tap, alineación con prioridades de un tap, vista de los últimos días. *Listo cuando:* puedo capturar mi WDIGD real de hoy en menos de dos minutos desde el teléfono.

**F3 — Sesión semanal.** `/week/{iso_week}` con los bloques 1, 3, 4, 5 y 6: resumen agrupado por prioridad con categorización y alineación pendientes, promoción de highlights, journal y prioridades con autosave, preocupaciones/seguimientos, cierre y reapertura. *Listo cuando:* puedo hacer una sesión de domingo completa de punta a punta.

**F4 — Observaciones e historial.** Bloque 2 (conteos, ratio construcción/reacción, prioridad con más presencia, "Avance sin Logro" multi-semana), indicador de días capturados, recurrencia de review items, `/history`. *Listo cuando:* la sesión semanal muestra números correctos verificados contra datos de prueba.

**F5 — Deploy.** Railway + Postgres, variables de entorno, migraciones en release, smoke test desde el teléfono. *Listo cuando:* uso la app real una semana entera.

Para desarrollo, un `seed.py` que genere varias semanas de datos ficticios (bullets variados alineados con prioridades, dos reviews cerradas, una a medias, una semana sin review) para poder trabajar F3 y F4 sin capturar a mano.

## Fuera de alcance (recordatorio para no sobre-construir)

Sin LLM en ningún punto. Sin notificaciones ni recordatorios. Sin streaks ni gamificación. Sin exportación. Sin apps nativas. Sin integraciones. Sin resumen automático. Sin OAuth. Sin roles ni equipos. Si durante la implementación aparece la tentación de agregar algo de esta lista, la respuesta es no.

## Decisiones provisorias (revisables, pero no bloquean el prototipo)

- **Nombre:** placeholder `wdigd`. El repo, el proyecto de Railway y el título de la app usan ese nombre hasta decidir el definitivo.
- **Idioma de la interfaz:** voseo rioplatense en el MVP —es la voz natural del método y el primer usuario es uno solo—. Si la app se abre, se revisa junto con el onboarding; los strings van centralizados en los templates para que el cambio sea barato.
- **Taxonomía Logro/Avance/Desbloqueo:** hipótesis a validar en uso real. Si tras unas semanas categorizar en la sesión semanal se siente burocrático, se elimina sin culpa —el método sobrevivió años sin ella—.

## Después del MVP (no ahora)

En orden tentativo de valor: sugerencia de alineación de bullets con prioridades vía LLM (con confirmación del usuario), detección semántica de preocupaciones y seguimientos recurrentes, recordatorio configurable de captura y de sesión semanal, exportación en Markdown, y modo de onboarding que explique el método a usuarios nuevos —la pieza clave si la app se abre, porque la app es el método, y sin entender el método la interfaz no significa nada.
