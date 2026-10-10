"""Shared pytest setup: tests run against a throwaway SQLite file, never the real Postgres."""
import itertools
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"  # must be set before the app is imported
os.environ["JWT_SECRET"] = "test-only-" + "x" * 32  # PyJWT wants >= 32 bytes for HS256

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401  (registers models with Base)
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402

PASSWORD = "correct-horse-battery"
_emails = itertools.count(1)


@pytest.fixture(scope="session", autouse=True)
def create_test_tables():
    """Create all tables once per test session and drop them afterwards."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_tables():
    """Each test starts with empty tables (children first, so foreign keys never dangle)."""
    with engine.begin() as conn:
        for table in (models.Resume, models.Connection, models.Profile, models.User):
            conn.execute(table.__table__.delete())


@pytest.fixture
def client():
    """An anonymous (logged-out) visitor."""
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def new_user():
    """Factory: register a fresh account and return a TestClient logged in as it.

    Each TestClient keeps its own cookies, so every returned client is a separate browser.
    The registered user is available as `client.user` ({"id", "email", "profile_id"}).
    """
    clients = []

    def _new(email: str | None = None, password: str = PASSWORD) -> TestClient:
        c = TestClient(app)
        response = c.post(
            "/api/auth/register",
            json={"email": email or f"student{next(_emails)}@uni.edu", "password": password},
        )
        assert response.status_code == 201, response.text
        c.user = response.json()
        clients.append(c)
        return c

    yield _new
    for c in clients:
        c.close()


@pytest.fixture
def make_profile(new_user):
    """Factory: create a profile owned by `owner` (a new user if omitted); kwargs override defaults."""
    def _make(owner: TestClient | None = None, **overrides) -> dict:
        owner = owner or new_user()
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
        response = owner.post("/api/profiles", json=payload)
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture
def connect():
    """Helper: make two logged-in users connected (a sends, b accepts)."""
    def _connect(a: TestClient, b: TestClient) -> None:
        request = a.post("/api/connections/requests", json={"user_id": b.user["id"]})
        assert request.status_code == 201, request.text
        accepted = b.post(f"/api/connections/requests/{request.json()['id']}/accept")
        assert accepted.status_code == 200, accepted.text

    return _connect
