"""Shared pytest setup: tests run against a throwaway SQLite file, never the real Postgres."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"  # must be set before the app is imported

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401  (registers models with Base)
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables once per test session and drop them afterwards."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(autouse=True)
def clean_profiles():
    """Each test starts with an empty profiles table."""
    with engine.begin() as conn:
        conn.execute(models.Profile.__table__.delete())

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def make_profile(client):
    """Create a profile through the API; keyword arguments override the defaults."""
    def _make(**overrides):
        payload = {
            "name": "Ayesha Khan",
            "bio": "Backend dev looking for a hackathon team",
            "skills": ["Python", "FastAPI", "Docker"],
            "linkedin_url": "https://www.linkedin.com/in/ayesha-khan",
            "department": "CSE",
            "year": 3,
            "availability": "OPEN_TO_TEAM",
            "visibility": "PUBLIC",
        }
        payload.update(overrides)
        response = client.post("/api/profiles", json=payload)
        assert response.status_code == 201, response.text
        return response.json()
    return _make
