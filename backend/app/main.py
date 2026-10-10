from collections import Counter

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import Profile
from .schemas import Availability, ProfileCreate, ProfileOut, ProfileUpdate, SkillCount, StatsOut

# Tables are created by Alembic migrations (see the backend Dockerfile), never by the app itself.
# No CORS middleware: the browser reaches the API on the same origin through Nginx / the Ingress.
app = FastAPI(title=settings.app_name, version="1.0.0")
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

NULLABLE_ON_UPDATE = {"year", "skills", "linkedin_url"}

def split_skills(raw: str) -> list[str]:
    return [s.strip() for s in raw.split(",") if s.strip()]

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

def to_out(profile: Profile) -> ProfileOut:
    """Serialize a profile, withholding skills and LinkedIn for LIMITED profiles."""
    hidden = profile.visibility == "LIMITED"
    return ProfileOut(
        id=profile.id,
        name=profile.name,
        bio=profile.bio,
        skills=[] if hidden else split_skills(profile.skills),
        linkedin_url="" if hidden else profile.linkedin_url,
        department=profile.department,
        year=profile.year,
        availability=profile.availability,
        visibility=profile.visibility,
        hidden=hidden,
        created_at=profile.created_at,
    )

def get_or_404(db: Session, profile_id: int) -> Profile:
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.get("/")
def root():
    return {"service": settings.app_name, "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
def health():
    """Liveness: the process is up. Deliberately does not touch the database."""
    return {"status": "UP"}

@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness: can we serve traffic? 503 tells Kubernetes to stop routing to this pod."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "NOT_READY", "reason": "database unavailable"})
    return {"status": "READY"}

@app.get("/api/profiles", response_model=list[ProfileOut])
def list_profiles(
    skill: str | None = Query(default=None, max_length=40),
    q: str | None = Query(default=None, max_length=80),
    availability: Availability | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = select(Profile).order_by(Profile.id.desc())
    if availability:
        query = query.where(Profile.availability == availability)
    if skill and skill.strip():
        # Only PUBLIC skills are searchable, otherwise a search would reveal hidden skills.
        query = query.where(Profile.visibility == "PUBLIC", has_skill(skill))
    if q and q.strip():
        term = f"%{escape_like(q.strip())}%"
        query = query.where(or_(Profile.name.ilike(term, escape="\\"), Profile.department.ilike(term, escape="\\")))
    return [to_out(p) for p in db.scalars(query.limit(limit).offset(offset))]

@app.get("/api/profiles/stats", response_model=StatsOut)
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

@app.get("/api/profiles/{profile_id}", response_model=ProfileOut)
def get_profile(profile_id: int, db: Session = Depends(get_db)):
    return to_out(get_or_404(db, profile_id))

@app.post("/api/profiles", response_model=ProfileOut, status_code=status.HTTP_201_CREATED)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["skills"] = ", ".join(data["skills"])
    profile = Profile(**data)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return to_out(profile)

@app.put("/api/profiles/{profile_id}", response_model=ProfileOut)
def update_profile(profile_id: int, payload: ProfileUpdate, db: Session = Depends(get_db)):
    profile = get_or_404(db, profile_id)
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
    return to_out(profile)

@app.delete("/api/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_profile(profile_id: int, db: Session = Depends(get_db)):
    db.delete(get_or_404(db, profile_id))
    db.commit()
