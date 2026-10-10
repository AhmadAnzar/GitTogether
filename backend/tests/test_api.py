from sqlalchemy.exc import OperationalError

from app.db import get_db
from app.main import app

# ---------- service endpoints ----------

def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}

def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "GitTogether API"

def test_ready_when_database_is_up(client):
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "READY"}

def test_ready_returns_503_when_database_is_down(client):
    class BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "NOT_READY"

def test_metrics_exposed(client):
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text

# ---------- create + validation ----------

def test_create_profile(make_profile):
    profile = make_profile()
    assert profile["id"] > 0
    assert profile["skills"] == ["Python", "FastAPI", "Docker"]
    assert profile["hidden"] is False

def test_skills_are_trimmed_and_deduplicated(make_profile):
    profile = make_profile(skills=" React, react ,Figma,, ")
    assert profile["skills"] == ["React", "Figma"]

def test_name_and_text_fields_are_trimmed(make_profile):
    profile = make_profile(name="  Ayesha  ", department=" CSE ")
    assert profile["name"] == "Ayesha"
    assert profile["department"] == "CSE"

def test_rejects_empty_or_blank_name(client):
    assert client.post("/api/profiles", json={"name": ""}).status_code == 422
    assert client.post("/api/profiles", json={"name": "   "}).status_code == 422

def test_rejects_invalid_linkedin_url(client):
    response = client.post("/api/profiles", json={"name": "Bob", "linkedin_url": "https://evil.example.com/bob"})
    assert response.status_code == 422

def test_rejects_too_many_skills(client):
    response = client.post("/api/profiles", json={"name": "Bob", "skills": [f"skill{i}" for i in range(16)]})
    assert response.status_code == 422

# ---------- list, search, pagination ----------

def test_list_profiles_newest_first(client, make_profile):
    make_profile(name="First")
    make_profile(name="Second")
    names = [p["name"] for p in client.get("/api/profiles").json()]
    assert names == ["Second", "First"]

def test_filter_by_skill_and_availability(client, make_profile):
    make_profile(name="Py Dev", skills=["Python"])
    make_profile(name="Designer", skills=["Figma"], availability="BUSY")
    by_skill = client.get("/api/profiles", params={"skill": "python"}).json()
    assert [p["name"] for p in by_skill] == ["Py Dev"]
    busy = client.get("/api/profiles", params={"availability": "BUSY"}).json()
    assert [p["name"] for p in busy] == ["Designer"]

def test_skill_filter_matches_whole_skills_only(client, make_profile):
    make_profile(name="JS Dev", skills=["JavaScript"])
    make_profile(name="Java Dev", skills=["Spring", "Java", "SQL"])
    make_profile(name="Solo Java", skills=["java"])
    names = {p["name"] for p in client.get("/api/profiles", params={"skill": "Java"}).json()}
    assert names == {"Java Dev", "Solo Java"}

def test_search_wildcards_are_literal(client, make_profile):
    make_profile(name="Ayesha")
    assert client.get("/api/profiles", params={"q": "%"}).json() == []
    assert client.get("/api/profiles", params={"skill": "_"}).json() == []
    assert len(client.get("/api/profiles", params={"q": "yes"}).json()) == 1

def test_pagination(client, make_profile):
    for i in range(5):
        make_profile(name=f"Student {i}")
    page1 = client.get("/api/profiles", params={"limit": 2}).json()
    page2 = client.get("/api/profiles", params={"limit": 2, "offset": 2}).json()
    assert [p["name"] for p in page1] == ["Student 4", "Student 3"]
    assert [p["name"] for p in page2] == ["Student 2", "Student 1"]
    assert client.get("/api/profiles", params={"limit": 101}).status_code == 422

# ---------- read, update, delete ----------

def test_get_profile_and_404(client, make_profile):
    profile = make_profile()
    assert client.get(f"/api/profiles/{profile['id']}").json()["name"] == "Ayesha Khan"
    assert client.get("/api/profiles/99999").status_code == 404

def test_update_profile(client, make_profile):
    profile = make_profile()
    response = client.put(f"/api/profiles/{profile['id']}", json={"availability": "BUSY", "skills": ["Go"]})
    assert response.status_code == 200
    assert response.json()["availability"] == "BUSY"
    assert response.json()["skills"] == ["Go"]
    assert response.json()["name"] == "Ayesha Khan"  # untouched fields are kept

def test_update_ignores_null_for_required_fields(client, make_profile):
    profile = make_profile()
    response = client.put(f"/api/profiles/{profile['id']}", json={"name": None, "availability": None, "year": None})
    assert response.status_code == 200
    assert response.json()["name"] == "Ayesha Khan"
    assert response.json()["availability"] == "OPEN_TO_TEAM"
    assert response.json()["year"] is None  # year is optional, so null clears it

def test_update_missing_profile_returns_404(client):
    assert client.put("/api/profiles/99999", json={"name": "Ghost"}).status_code == 404

def test_delete_profile(client, make_profile):
    profile = make_profile()
    assert client.delete(f"/api/profiles/{profile['id']}").status_code == 204
    assert client.get(f"/api/profiles/{profile['id']}").status_code == 404
    assert client.delete(f"/api/profiles/{profile['id']}").status_code == 404

# ---------- privacy ----------

def test_limited_profile_hides_skills_and_linkedin(client, make_profile):
    profile = make_profile(visibility="LIMITED")
    assert profile["hidden"] is True
    assert profile["skills"] == []
    assert profile["linkedin_url"] == ""
    fetched = client.get(f"/api/profiles/{profile['id']}").json()
    assert fetched["skills"] == [] and fetched["linkedin_url"] == ""

def test_limited_skills_are_not_searchable(client, make_profile):
    make_profile(name="Shy Student", skills=["Rust"], visibility="LIMITED")
    assert client.get("/api/profiles", params={"skill": "rust"}).json() == []

def test_switching_to_public_reveals_stored_skills(client, make_profile):
    profile = make_profile(skills=["Rust"], visibility="LIMITED")
    response = client.put(f"/api/profiles/{profile['id']}", json={"visibility": "PUBLIC"})
    assert response.json()["skills"] == ["Rust"]

# ---------- stats ----------

def test_stats(client, make_profile):
    make_profile(skills=["Python", "Docker"])
    make_profile(skills=["python"], availability="BUSY")
    make_profile(skills=["Rust"], availability="NOT_LOOKING", visibility="LIMITED")
    stats = client.get("/api/profiles/stats").json()
    assert stats["total"] == 3
    assert stats["openToTeam"] == 1 and stats["busy"] == 1 and stats["notLooking"] == 1
    assert stats["limited"] == 1
    assert stats["topSkills"][0] == {"skill": "python", "count": 2}
    assert all(s["skill"] != "rust" for s in stats["topSkills"])
