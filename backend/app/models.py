from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Profile(Base):
    """A student's listing on GitTogether."""
    __tablename__ = "profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    bio: Mapped[str] = mapped_column(Text, default="")
    # Stored as a comma-separated string ("Python, React"); the API exposes it as a list.
    skills: Mapped[str] = mapped_column(Text, default="")
    linkedin_url: Mapped[str] = mapped_column(String(300), default="")
    department: Mapped[str] = mapped_column(String(80), default="")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    availability: Mapped[str] = mapped_column(String(20), default="OPEN_TO_TEAM")
    visibility: Mapped[str] = mapped_column(String(10), default="PUBLIC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
