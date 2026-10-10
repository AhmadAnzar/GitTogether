from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import User
from app.security import SESSION_COOKIE

from .conftest import PASSWORD


def test_register_logs_you_in(new_user):
    user = new_user("Ayesha@Uni.edu")
    assert user.user["email"] == "ayesha@uni.edu"  # emails are stored lowercase
    assert user.user["profile_id"] is None
    assert user.get("/api/auth/me").json()["email"] == "ayesha@uni.edu"

def test_session_cookie_is_http_only(client):
    response = client.post("/api/auth/register", json={"email": "a@uni.edu", "password": PASSWORD})
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    assert "HttpOnly" in cookie
    assert "samesite=lax" in cookie.lower()

def test_duplicate_email_is_rejected_case_insensitively(client, new_user):
    new_user("dup@uni.edu")
    response = client.post("/api/auth/register", json={"email": "DUP@uni.edu", "password": PASSWORD})
    assert response.status_code == 409

def test_register_validates_email_and_password(client):
    assert client.post("/api/auth/register", json={"email": "not-an-email", "password": PASSWORD}).status_code == 422
    assert client.post("/api/auth/register", json={"email": "a@uni.edu", "password": "short"}).status_code == 422

def test_password_is_stored_hashed(new_user):
    new_user("hash@uni.edu")
    with SessionLocal() as db:
        stored = db.query(User).filter_by(email="hash@uni.edu").one().password_hash
    assert stored != PASSWORD
    assert stored.startswith("$argon2")

def test_login_and_logout(new_user):
    new_user("login@uni.edu")
    with TestClient(app) as browser:
        assert browser.get("/api/auth/me").status_code == 401
        response = browser.post("/api/auth/login", json={"email": "LOGIN@uni.edu", "password": PASSWORD})
        assert response.status_code == 200
        assert browser.get("/api/auth/me").json()["email"] == "login@uni.edu"
        assert browser.post("/api/auth/logout").status_code == 204
        assert browser.get("/api/auth/me").status_code == 401

def test_wrong_password_and_unknown_email_get_the_same_error(client, new_user):
    new_user("real@uni.edu")
    wrong_password = client.post("/api/auth/login", json={"email": "real@uni.edu", "password": "wrong-password"})
    unknown_email = client.post("/api/auth/login", json={"email": "ghost@uni.edu", "password": PASSWORD})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()

def test_tampered_or_garbage_token_is_treated_as_logged_out(client, new_user):
    user = new_user()
    token = user.cookies.get(SESSION_COOKIE)
    client.cookies.set(SESSION_COOKIE, token[:-2] + ("aa" if not token.endswith("aa") else "bb"))
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set(SESSION_COOKIE, "garbage")
    assert client.get("/api/auth/me").status_code == 401

def test_me_reports_profile_id(new_user, make_profile):
    owner = new_user()
    profile = make_profile(owner)
    assert owner.get("/api/auth/me").json()["profile_id"] == profile["id"]
