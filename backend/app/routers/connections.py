"""Connection requests: send -> accept/decline (or cancel) -> connected; either side can remove."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..access import ViewerContext
from ..db import get_db
from ..models import Connection, Profile, User, utcnow
from ..schemas import ConnectionOut, ConnectionRequestCreate, ConnectionRequestOut, ConnectionRequestsOut
from ..security import get_current_user
from ..serializers import serialize_profiles

router = APIRouter(prefix="/api/connections", tags=["connections"])


def between(a: int, b: int):
    """Connection rows between two users, in either direction."""
    return or_(
        and_(Connection.requester_id == a, Connection.addressee_id == b),
        and_(Connection.requester_id == b, Connection.addressee_id == a),
    )


def profiles_by_owner(db: Session, owner_ids: list[int], ctx: ViewerContext) -> dict:
    profiles = list(db.scalars(select(Profile).where(Profile.user_id.in_(owner_ids)))) if owner_ids else []
    return {out.owner_id: out for out in serialize_profiles(db, profiles, ctx)}


def get_request_or_404(db: Session, request_id: int) -> Connection:
    request = db.get(Connection, request_id)
    if request is None or request.status != "PENDING":
        raise HTTPException(status_code=404, detail="Connection request not found")
    return request


@router.get("", response_model=list[ConnectionOut])
def my_connections(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = list(
        db.scalars(
            select(Connection)
            .where(Connection.status == "ACCEPTED", or_(Connection.requester_id == user.id, Connection.addressee_id == user.id))
            .order_by(Connection.responded_at.desc())
        )
    )
    others = [c.addressee_id if c.requester_id == user.id else c.requester_id for c in rows]
    profiles = profiles_by_owner(db, others, ViewerContext(db, user))
    return [
        ConnectionOut(user_id=other, profile=profiles.get(other), connected_at=c.responded_at)
        for other, c in zip(others, rows, strict=True)
    ]


@router.get("/requests", response_model=ConnectionRequestsOut)
def my_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    pending = list(
        db.scalars(
            select(Connection)
            .where(Connection.status == "PENDING", or_(Connection.requester_id == user.id, Connection.addressee_id == user.id))
            .order_by(Connection.created_at.desc())
        )
    )
    others = [c.addressee_id if c.requester_id == user.id else c.requester_id for c in pending]
    profiles = profiles_by_owner(db, others, ViewerContext(db, user))
    incoming, outgoing = [], []
    for other, c in zip(others, pending, strict=True):
        item = ConnectionRequestOut(id=c.id, user_id=other, profile=profiles.get(other), created_at=c.created_at)
        (outgoing if c.requester_id == user.id else incoming).append(item)
    return ConnectionRequestsOut(incoming=incoming, outgoing=outgoing)


@router.post("/requests", response_model=ConnectionRequestOut, status_code=status.HTTP_201_CREATED)
def send_request(payload: ConnectionRequestCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if payload.user_id == user.id:
        raise HTTPException(status_code=400, detail="You can't connect with yourself")
    if db.get(User, payload.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.scalar(select(Connection).where(between(user.id, payload.user_id)))
    if existing is not None:
        if existing.status == "ACCEPTED":
            raise HTTPException(status_code=409, detail="You're already connected")
        if existing.requester_id == user.id:
            raise HTTPException(status_code=409, detail="Request already sent")
        raise HTTPException(status_code=409, detail="They already sent you a request; accept it instead")
    request = Connection(requester_id=user.id, addressee_id=payload.user_id)
    db.add(request)
    db.commit()
    db.refresh(request)
    profile = profiles_by_owner(db, [payload.user_id], ViewerContext(db, user)).get(payload.user_id)
    return ConnectionRequestOut(id=request.id, user_id=payload.user_id, profile=profile, created_at=request.created_at)


@router.post("/requests/{request_id}/accept", response_model=ConnectionOut)
def accept_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    request = get_request_or_404(db, request_id)
    if request.addressee_id != user.id:
        raise HTTPException(status_code=403, detail="Only the person who received the request can accept it")
    request.status = "ACCEPTED"
    request.responded_at = utcnow()
    db.commit()
    other = request.requester_id
    profile = profiles_by_owner(db, [other], ViewerContext(db, user)).get(other)
    return ConnectionOut(user_id=other, profile=profile, connected_at=request.responded_at)


@router.post("/requests/{request_id}/decline", status_code=status.HTTP_204_NO_CONTENT)
def decline_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    request = get_request_or_404(db, request_id)
    if request.addressee_id != user.id:
        raise HTTPException(status_code=403, detail="Only the person who received the request can decline it")
    db.delete(request)
    db.commit()


@router.delete("/requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_request(request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    request = get_request_or_404(db, request_id)
    if request.requester_id != user.id:
        raise HTTPException(status_code=403, detail="Only the person who sent the request can cancel it")
    db.delete(request)
    db.commit()


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_connection(user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    connection = db.scalar(select(Connection).where(Connection.status == "ACCEPTED", between(user.id, user_id)))
    if connection is None:
        raise HTTPException(status_code=404, detail="You're not connected with this user")
    db.delete(connection)
    db.commit()
