from sqlalchemy.orm import Session

from .access import ViewerContext, connections_counts, resume_profile_ids
from .models import Profile
from .schemas import ProfileOut


def split_skills(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]


def serialize_profiles(db: Session, profiles: list[Profile], ctx: ViewerContext) -> list[ProfileOut]:
    """Turn profiles into API output for this viewer, withholding private fields they may not see."""
    owner_ids = {p.user_id for p in profiles if p.user_id is not None}
    counts = connections_counts(db, owner_ids)
    with_resume = resume_profile_ids(db, {p.id for p in profiles})
    out = []
    for p in profiles:
        visible = ctx.can_see_private(p)
        status, request_id = ctx.status(p.user_id)
        out.append(
            ProfileOut(
                id=p.id,
                owner_id=p.user_id,
                name=p.name,
                bio=p.bio,
                skills=split_skills(p.skills) if visible else [],
                linkedin_url=p.linkedin_url if visible else "",
                department=p.department,
                year=p.year,
                availability=p.availability,
                visibility=p.visibility,
                hidden=not visible,
                has_resume=visible and p.id in with_resume,
                is_owner=status == "SELF",
                connection_status=status,
                request_id=request_id,
                connections_count=counts.get(p.user_id, 0),
                created_at=p.created_at,
            )
        )
    return out


def serialize_profile(db: Session, profile: Profile, ctx: ViewerContext) -> ProfileOut:
    return serialize_profiles(db, [profile], ctx)[0]
