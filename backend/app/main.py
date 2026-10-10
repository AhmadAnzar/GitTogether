from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .routers import auth, connections, profiles

# Tables are created by Alembic migrations (see the backend Dockerfile), never by the app itself.
# No CORS middleware: the browser reaches the API on the same origin through Nginx / the Ingress,
# which also means the session cookie is never sent to (or accepted from) another site.
app = FastAPI(title=settings.app_name, version="1.1.0")
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(connections.router)


@app.get("/")
def root():
    return {"service": settings.app_name, "version": app.version, "docs": "/docs"}


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
