"""Who may see what: one place for the privacy rule used by profiles, search and resumes.

Rule: a LIMITED profile's skills, LinkedIn and resume are visible only to its owner and to the
owner's accepted connections. PUBLIC profiles show everything to everyone.
"""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .models import Connection, Profile, Resume, User


class ViewerContext:
    """The viewer's connections and pending requests, loaded once per request."""

    def __init__(self, db: Session, viewer: User | None):
        self.viewer_id = viewer.id if viewer else None
        self.connected: set[int] = set()
        self.outgoing: dict[int, int] = {}  # other user id -> pending request id (viewer sent it)
        self.incoming: dict[int, int] = {}  # other user id -> pending request id (viewer received it)
        if viewer is None:
            return
        rows = db.scalars(
            select(Connection).where(or_(Connection.requester_id == viewer.id, Connection.addressee_id == viewer.id))
        )
        for c in rows:
            other = c.addressee_id if c.requester_id == viewer.id else c.requester_id
            if c.status == "ACCEPTED":
                self.connected.add(other)
            elif c.requester_id == viewer.id:
                self.outgoing[other] = c.id
            else:
                self.incoming[other] = c.id

    @property
    def private_access_owner_ids(self) -> set[int]:
        """Owners whose LIMITED details this viewer may see: themselves and their connections."""
        return self.connected | ({self.viewer_id} if self.viewer_id else set())

    def can_see_private(self, profile: Profile) -> bool:
        return profile.visibility == "PUBLIC" or profile.user_id in self.private_access_owner_ids

    def status(self, owner_id: int | None) -> tuple[str, int | None]:
        if owner_id is None or self.viewer_id is None:
            return "NONE", None
        if owner_id == self.viewer_id:
            return "SELF", None
        if owner_id in self.connected:
            return "CONNECTED", None
        if owner_id in self.outgoing:
            return "PENDING_OUTGOING", self.outgoing[owner_id]
        if owner_id in self.incoming:
            return "PENDING_INCOMING", self.incoming[owner_id]
        return "NONE", None


def connections_counts(db: Session, user_ids: set[int]) -> dict[int, int]:
    """Accepted-connection count per user, for a batch of users (two grouped queries, no N+1)."""
    if not user_ids:
        return {}
    counts: dict[int, int] = dict.fromkeys(user_ids, 0)
    accepted = Connection.status == "ACCEPTED"
    for column in (Connection.requester_id, Connection.addressee_id):
        rows = db.execute(select(column, func.count()).where(accepted, column.in_(user_ids)).group_by(column))
        for user_id, n in rows:
            counts[user_id] += n
    return counts


def resume_profile_ids(db: Session, profile_ids: set[int]) -> set[int]:
    if not profile_ids:
        return set()
    return set(db.scalars(select(Resume.profile_id).where(Resume.profile_id.in_(profile_ids))))
