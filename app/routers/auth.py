from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User
from app.security import hash_password, verify_password
from app.templating import templates

router = APIRouter()

MIN_PASSWORD = 8


def _find_by_email(db: Session, email: str) -> User | None:
    return db.execute(
        select(User).where(func.lower(User.email) == email.lower())
    ).scalar_one_or_none()


@router.get("/signup")
def signup_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/today", status_code=303)
    return templates.TemplateResponse(request, "pages/signup.html", {"error": None, "email": ""})


@router.post("/signup")
def signup(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    error = None
    if not email or "@" not in email:
        error = "Ingresá un email válido."
    elif len(password) < MIN_PASSWORD:
        error = f"La contraseña necesita al menos {MIN_PASSWORD} caracteres."
    elif _find_by_email(db, email) is not None:
        error = "Ese email ya está registrado."

    if error:
        return templates.TemplateResponse(
            request, "pages/signup.html", {"error": error, "email": email}, status_code=400
        )

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    request.session["user_id"] = user.id
    return RedirectResponse("/today", status_code=303)


@router.get("/login")
def login_form(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/today", status_code=303)
    return templates.TemplateResponse(request, "pages/login.html", {"error": None, "email": ""})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    user = _find_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "pages/login.html",
            {"error": "Email o contraseña incorrectos.", "email": email},
            status_code=401,
        )
    request.session["user_id"] = user.id
    return RedirectResponse("/today", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
