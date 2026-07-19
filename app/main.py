from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import auth, entries, history, settings as settings_router, today, week

app = FastAPI(title="wdigd")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    max_age=60 * 60 * 24 * 30,
)

app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

app.include_router(auth.router)
app.include_router(today.router)
app.include_router(entries.router)
app.include_router(week.router)
app.include_router(history.router)
app.include_router(settings_router.router)


@app.get("/")
def index(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/today", status_code=303)
    return RedirectResponse("/login", status_code=303)
