from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Profile, User
from ..schemas import Credentials, UserOut
from ..security import (
    clear_session_cookie,
    get_current_user,
    hash_password,
    set_session_cookie,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def to_user_out(db: Session, user: User) -> UserOut:
    profile_id = db.scalar(select(Profile.id).where(Profile.user_id == user.id))
    return UserOut(id=user.id, email=user.email, profile_id=profile_id)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: Credentials, response: Response, db: Session = Depends(get_db)):
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    db.refresh(user)
    set_session_cookie(response, user.id)
    return to_user_out(db, user)


@router.post("/login", response_model=UserOut)
def login(payload: Credentials, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    # Same message whether the email or the password is wrong, so emails can't be probed.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong email or password")
    set_session_cookie(response, user.id)
    return to_user_out(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    clear_session_cookie(response)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return to_user_out(db, user)
