from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.deps import LoginRequired
from app.routers import auth, calendar, entries, history, settings as settings_router, today, week

LOGIN_PATH = "/login"
HOME_PATH = "/today"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 días

app = FastAPI(title="wdigd")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=settings.secure_cookies,
    max_age=SESSION_MAX_AGE,
)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

app.include_router(auth.router)
app.include_router(today.router)
app.include_router(entries.router)
app.include_router(week.router)
app.include_router(history.router)
app.include_router(settings_router.router)
app.include_router(calendar.router)


@app.exception_handler(LoginRequired)
def handle_login_required(request: Request, exc: LoginRequired) -> Response:
    # En un pedido HTMX el redirect lo tiene que hacer el cliente: si respondiéramos
    # 303, fetch lo seguiría solo y el login terminaría incrustado en un fragmento.
    if request.headers.get("hx-request"):
        return Response(status_code=204, headers={"HX-Redirect": LOGIN_PATH})
    return RedirectResponse(LOGIN_PATH, status_code=303)


@app.get("/")
def index(request: Request):
    destination = HOME_PATH if request.session.get("user_id") else LOGIN_PATH
    return RedirectResponse(destination, status_code=303)
