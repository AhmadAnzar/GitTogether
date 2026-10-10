import re
from collections import Counter

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from ..access import ViewerContext
from ..config import settings
from ..db import get_db
from ..models import Profile, Resume, User, utcnow
from ..schemas import Availability, ProfileCreate, ProfileOut, ProfileUpdate, ResumeOut, SkillCount, StatsOut
from ..security import get_current_user, get_current_user_optional
from ..serializers import serialize_profile, serialize_profiles, split_skills

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

NULLABLE_ON_UPDATE = {"year", "skills", "linkedin_url"}
PDF_MAGIC = b"%PDF-"


def escape_like(value: str) -> str:
    """Make user input literal inside a LIKE pattern (so '%' or '_' don't act as wildcards)."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def has_skill(skill: str):
    """Whole-skill match against the stored "A, B, C" string: 'java' must not match 'JavaScript'."""
    s = escape_like(skill.strip())
    column = Profile.skills
    return or_(
        column.ilike(s, escape="\\"),
        column.ilike(f"{s}, %", escape="\\"),
        column.ilike(f"%, {s}", escape="\\"),
        column.ilike(f"%, {s}, %", escape="\\"),
    )


def get_or_404(db: Session, profile_id: int) -> Profile:
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


def get_owned_or_403(db: Session, profile_id: int, user: User) -> Profile:
    profile = get_or_404(db, profile_id)
    if profile.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only change your own profile")
    return profile


def viewer_context(
    db: Session = Depends(get_db), viewer: User | None = Depends(get_current_user_optional)
) -> ViewerContext:
    return ViewerContext(db, viewer)


# ---------- profiles ----------

@router.get("", response_model=list[ProfileOut])
def list_profiles(
    skill: str | None = Query(default=None, max_length=40),
    q: str | None = Query(default=None, max_length=80),
    availability: Availability | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    ctx: ViewerContext = Depends(viewer_context),
):
    query = select(Profile).order_by(Profile.id.desc())
    if availability:
        query = query.where(Profile.availability == availability)
    if skill and skill.strip():
        # Only skills this viewer may see are searchable, otherwise a search would reveal hidden skills.
        may_see = or_(Profile.visibility == "PUBLIC", Profile.user_id.in_(ctx.private_access_owner_ids))
        query = query.where(may_see, has_skill(skill))
    if q and q.strip():
        term = f"%{escape_like(q.strip())}%"
        query = query.where(or_(Profile.name.ilike(term, escape="\\"), Profile.department.ilike(term, escape="\\")))
    profiles = list(db.scalars(query.limit(limit).offset(offset)))
    return serialize_profiles(db, profiles, ctx)


@router.get("/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    rows = db.execute(select(Profile.availability, func.count(Profile.id)).group_by(Profile.availability)).all()
    counts = {availability: count for availability, count in rows}
    limited = db.scalar(select(func.count(Profile.id)).where(Profile.visibility == "LIMITED"))
    skill_counter = Counter()
    for raw in db.scalars(select(Profile.skills).where(Profile.visibility == "PUBLIC")):
        skill_counter.update(s.lower() for s in split_skills(raw))
    return StatsOut(
        total=sum(counts.values()),
        openToTeam=counts.get("OPEN_TO_TEAM", 0),
        busy=counts.get("BUSY", 0),
        notLooking=counts.get("NOT_LOOKING", 0),
        limited=limited,
        topSkills=[SkillCount(skill=s, count=c) for s, c in skill_counter.most_common(8)],
    )


@router.get("/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: int, db: Session = Depends(get_db), ctx: ViewerContext = Depends(viewer_context)):
    return serialize_profile(db, get_or_404(db, profile_id), ctx)


@router.post("", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if db.scalar(select(Profile.id).where(Profile.user_id == user.id)) is not None:
        raise HTTPException(status_code=409, detail="You already have a profile; edit it instead")
    data = payload.model_dump()
    data["skills"] = ", ".join(data["skills"])
    profile = Profile(**data, user_id=user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return serialize_profile(db, profile, ViewerContext(db, user))


@router.put("/{profile_id}", response_model=ProfileOut)
def update_profile(
    profile_id: int,
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = get_owned_or_403(db, profile_id, user)
    for key, value in payload.model_dump(exclude_unset=True).items():
        if value is None and key not in NULLABLE_ON_UPDATE:
            continue  # an explicit null for a required column means "leave unchanged"
        if key == "skills":
            value = ", ".join(value or [])
        if key == "linkedin_url" and value is None:
            value = ""
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return serialize_profile(db, profile, ViewerContext(db, user))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = get_owned_or_403(db, profile_id, user)
    db.execute(delete(Resume).where(Resume.profile_id == profile.id))  # explicit: SQLite ignores FK cascades
    db.delete(profile)
    db.commit()


# ---------- resume ----------

def safe_filename(name: str | None) -> str:
    """Keep only the base name (no / or \\ paths), plain characters, and no leading/trailing dots."""
    base = re.split(r"[\\/]", name or "")[-1]
    stem = re.sub(r"[^A-Za-z0-9._ -]", "", base).strip(" .") or "resume"
    if not stem.lower().endswith(".pdf"):
        stem += ".pdf"
    return stem[-120:]


@router.put("/{profile_id}/resume", response_model=ResumeOut)
async def upload_resume(
    profile_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    profile = get_owned_or_403(db, profile_id, user)
    content = await file.read(settings.max_resume_bytes + 1)
    if len(content) > settings.max_resume_bytes:
        raise HTTPException(status_code=413, detail="Resume must be 5 MB or smaller")
    # Check the actual bytes, not the filename or the browser-supplied content type.
    if not content.startswith(PDF_MAGIC):
        raise HTTPException(status_code=415, detail="Resume must be a PDF file")
    resume = db.get(Resume, profile.id) or Resume(profile_id=profile.id)
    resume.filename = safe_filename(file.filename)
    resume.content = content
    resume.size_bytes = len(content)
    resume.uploaded_at = utcnow()
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return ResumeOut(filename=resume.filename, size_bytes=resume.size_bytes, uploaded_at=resume.uploaded_at)


@router.get("/{profile_id}/resume")
def download_resume(profile_id: int, db: Session = Depends(get_db), ctx: ViewerContext = Depends(viewer_context)):
    profile = get_or_404(db, profile_id)
    resume = db.get(Resume, profile.id)
    # 404 (not 403) when the viewer may not see it, so a hidden resume's existence isn't revealed.
    if resume is None or not ctx.can_see_private(profile):
        raise HTTPException(status_code=404, detail="Resume not found")
    return Response(
        content=resume.content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{resume.filename}"',
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{profile_id}/resume", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(profile_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    profile = get_owned_or_403(db, profile_id, user)
    resume = db.get(Resume, profile.id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    db.delete(resume)
    db.commit()
