"""Passwords, session tokens and the `current user` dependencies."""
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Depends, HTTPException, Response, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User

SESSION_COOKIE = "gt_session"
JWT_ALGORITHM = "HS256"

# Argon2id with pwdlib's recommended parameters. Hashes include their own salt and parameters.
password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_session_token(user_id: int) -> str:
    now = datetime.now(UTC)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(minutes=settings.jwt_expire_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def set_session_cookie(response: Response, user_id: int) -> None:
    # httpOnly: page scripts can't read it (limits XSS damage). SameSite=Lax: other sites can't make
    # the browser send it on POST/PUT/DELETE, which blocks cross-site request forgery.
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user_id),
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=settings.cookie_secure)


def get_current_user_optional(
    gt_session: str | None = Cookie(default=None), db: Session = Depends(get_db)
) -> User | None:
    """The logged-in user, or None for anonymous visitors (and for expired or tampered tokens)."""
    if not gt_session:
        return None
    try:
        payload = jwt.decode(gt_session, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None
    return db.get(User, user_id)


def get_current_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Log in first")
    return user
