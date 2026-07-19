# Deploy en Railway

Pasos para el primer deploy (F5). Requiere cuenta en Railway y el repo en GitHub
(o `railway up` desde la CLI).

1. Crear un proyecto nuevo en Railway y agregar el servicio **PostgreSQL**.
2. Agregar el servicio de la app desde el repo. `railway.toml` ya define:
   - `preDeployCommand = "alembic upgrade head"` (migraciones en cada release)
   - `startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"`
3. Variables de entorno del servicio de la app:
   - `DATABASE_URL` → referencia a la variable del Postgres del proyecto
     (`${{Postgres.DATABASE_URL}}`). La app normaliza el prefijo `postgres://`.
   - `SECRET_KEY` → un valor largo y aleatorio (`python -c "import secrets; print(secrets.token_hex(32))"`).
4. Deploy. Verificar en los logs que corrió `alembic upgrade head` antes del start.
5. Smoke test desde el teléfono: signup, login, capturar un bullet en `/today`,
   abrir `/week`, cerrar y reabrir la semana, `/history`.

Notas:
- Sin `SECRET_KEY` la app usa un valor de desarrollo: no deployar así.
- No usar `seed.py` en producción (crea un usuario demo con contraseña conocida).
