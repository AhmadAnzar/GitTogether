from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    """A login account. Each user owns at most one profile."""
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)  # stored lowercase
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Profile(Base):
    """A student's listing on GitTogether."""
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Nullable only for profiles created before accounts existed; those can no longer be edited.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    bio: Mapped[str] = mapped_column(Text, default="")
    # Stored as a comma-separated string ("Python, React"); the API exposes it as a list.
    skills: Mapped[str] = mapped_column(Text, default="")
    linkedin_url: Mapped[str] = mapped_column(String(300), default="")
    department: Mapped[str] = mapped_column(String(80), default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    availability: Mapped[str] = mapped_column(String(20), default="OPEN_TO_TEAM")
    visibility: Mapped[str] = mapped_column(String(10), default="PUBLIC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Connection(Base):
    """A connection between two users: PENDING until the addressee accepts, then ACCEPTED (mutual).

    Declined or cancelled requests are deleted, so a pair has at most one row in either direction.
    """
    __tablename__ = "connections"
    __table_args__ = (UniqueConstraint("requester_id", "addressee_id", name="uq_connections_pair"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    addressee_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(10), default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Resume(Base):
    """A profile's resume PDF. Kept in its own table so listing profiles never loads file bytes."""
    __tablename__ = "resumes"
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
