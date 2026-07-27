"""Dependencias compartidas por los routers."""

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User


class LoginRequired(Exception):
    """No hay sesión válida. main.py lo traduce al redirect que corresponda."""


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get("user_id")
    if user_id is None:
        raise LoginRequired
    user = db.get(User, user_id)
    if user is None:
        # Sesión firmada de un usuario que ya no existe.
        request.session.clear()
        raise LoginRequired
    return user
