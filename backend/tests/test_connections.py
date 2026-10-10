def status_of(viewer, profile):
    return viewer.get(f"/api/profiles/{profile['id']}").json()["connection_status"]


def test_connections_require_login(client):
    assert client.get("/api/connections").status_code == 401
    assert client.get("/api/connections/requests").status_code == 401
    assert client.post("/api/connections/requests", json={"user_id": 1}).status_code == 401

def test_send_request_shows_pending_on_both_sides(new_user, make_profile):
    alice, bob = new_user(), new_user()
    alice_profile, bob_profile = make_profile(alice, name="Alice"), make_profile(bob, name="Bob")

    sent = alice.post("/api/connections/requests", json={"user_id": bob.user["id"]})
    assert sent.status_code == 201
    assert sent.json()["profile"]["name"] == "Bob"

    assert status_of(alice, bob_profile) == "PENDING_OUTGOING"
    assert status_of(bob, alice_profile) == "PENDING_INCOMING"
    assert bob.get(f"/api/profiles/{alice_profile['id']}").json()["request_id"] == sent.json()["id"]

    assert [r["user_id"] for r in alice.get("/api/connections/requests").json()["outgoing"]] == [bob.user["id"]]
    incoming = bob.get("/api/connections/requests").json()["incoming"]
    assert [r["profile"]["name"] for r in incoming] == ["Alice"]

def test_accepting_connects_both_users(new_user, make_profile, connect):
    alice, bob = new_user(), new_user()
    alice_profile, bob_profile = make_profile(alice, name="Alice"), make_profile(bob, name="Bob")
    connect(alice, bob)

    assert status_of(alice, bob_profile) == "CONNECTED"
    assert status_of(bob, alice_profile) == "CONNECTED"
    assert [c["profile"]["name"] for c in alice.get("/api/connections").json()] == ["Bob"]
    assert [c["profile"]["name"] for c in bob.get("/api/connections").json()] == ["Alice"]
    assert alice.get(f"/api/profiles/{bob_profile['id']}").json()["connections_count"] == 1
    assert bob.get("/api/connections/requests").json() == {"incoming": [], "outgoing": []}

def test_connections_see_limited_profile_details(client, new_user, make_profile, connect):
    owner, friend, stranger = new_user(), new_user(), new_user()
    profile = make_profile(owner, skills=["Rust"], visibility="LIMITED")
    make_profile(friend)
    assert friend.get(f"/api/profiles/{profile['id']}").json()["hidden"] is True  # not yet connected

    connect(friend, owner)
    seen_by_friend = friend.get(f"/api/profiles/{profile['id']}").json()
    assert seen_by_friend["hidden"] is False
    assert seen_by_friend["skills"] == ["Rust"]
    assert seen_by_friend["linkedin_url"] == "https://www.linkedin.com/in/ayesha-khan"

    for other in (stranger, client):
        assert other.get(f"/api/profiles/{profile['id']}").json()["hidden"] is True

def test_connections_can_find_limited_profiles_by_skill(client, new_user, make_profile, connect):
    owner, friend = new_user(), new_user()
    make_profile(owner, name="Shy", skills=["Rust"], visibility="LIMITED")
    connect(owner, friend)
    assert [p["name"] for p in friend.get("/api/profiles", params={"skill": "rust"}).json()] == ["Shy"]
    assert client.get("/api/profiles", params={"skill": "rust"}).json() == []

def test_decline_removes_the_request(new_user, make_profile):
    alice, bob = new_user(), new_user()
    bob_profile = make_profile(bob)
    request_id = alice.post("/api/connections/requests", json={"user_id": bob.user["id"]}).json()["id"]
    assert bob.post(f"/api/connections/requests/{request_id}/decline").status_code == 204
    assert status_of(alice, bob_profile) == "NONE"
    # A declined request can be sent again later.
    assert alice.post("/api/connections/requests", json={"user_id": bob.user["id"]}).status_code == 201

def test_requester_can_cancel(new_user, make_profile):
    alice, bob = new_user(), new_user()
    bob_profile = make_profile(bob)
    request_id = alice.post("/api/connections/requests", json={"user_id": bob.user["id"]}).json()["id"]
    assert alice.delete(f"/api/connections/requests/{request_id}").status_code == 204
    assert status_of(alice, bob_profile) == "NONE"
    assert alice.delete(f"/api/connections/requests/{request_id}").status_code == 404

def test_only_the_right_person_can_accept_decline_or_cancel(new_user):
    alice, bob, eve = new_user(), new_user(), new_user()
    request_id = alice.post("/api/connections/requests", json={"user_id": bob.user["id"]}).json()["id"]
    assert alice.post(f"/api/connections/requests/{request_id}/accept").status_code == 403
    assert eve.post(f"/api/connections/requests/{request_id}/accept").status_code == 403
    assert eve.post(f"/api/connections/requests/{request_id}/decline").status_code == 403
    assert bob.delete(f"/api/connections/requests/{request_id}").status_code == 403
    assert bob.post("/api/connections/requests/99999/accept").status_code == 404

def test_invalid_requests_are_rejected(new_user, connect):
    alice, bob, carol = new_user(), new_user(), new_user()
    assert alice.post("/api/connections/requests", json={"user_id": alice.user["id"]}).status_code == 400
    assert alice.post("/api/connections/requests", json={"user_id": 99999}).status_code == 404

    assert alice.post("/api/connections/requests", json={"user_id": bob.user["id"]}).status_code == 201
    assert alice.post("/api/connections/requests", json={"user_id": bob.user["id"]}).status_code == 409  # duplicate
    reverse = bob.post("/api/connections/requests", json={"user_id": alice.user["id"]})
    assert reverse.status_code == 409 and "accept" in reverse.json()["detail"]

    connect(alice, carol)
    assert carol.post("/api/connections/requests", json={"user_id": alice.user["id"]}).status_code == 409

def test_accepted_request_can_not_be_accepted_again(new_user):
    alice, bob = new_user(), new_user()
    request_id = alice.post("/api/connections/requests", json={"user_id": bob.user["id"]}).json()["id"]
    assert bob.post(f"/api/connections/requests/{request_id}/accept").status_code == 200
    assert bob.post(f"/api/connections/requests/{request_id}/accept").status_code == 404

def test_removing_a_connection_hides_details_again(new_user, make_profile, connect):
    owner, friend = new_user(), new_user()
    profile = make_profile(owner, visibility="LIMITED")
    connect(owner, friend)
    assert friend.delete(f"/api/connections/{owner.user['id']}").status_code == 204
    fetched = friend.get(f"/api/profiles/{profile['id']}").json()
    assert fetched["hidden"] is True
    assert fetched["connection_status"] == "NONE"
    assert friend.delete(f"/api/connections/{owner.user['id']}").status_code == 404

def test_requests_from_users_without_a_profile(new_user, make_profile):
    alice, bob = new_user(), new_user()
    make_profile(bob)
    alice.post("/api/connections/requests", json={"user_id": bob.user["id"]})
    incoming = bob.get("/api/connections/requests").json()["incoming"]
    assert incoming[0]["user_id"] == alice.user["id"]
    assert incoming[0]["profile"] is None
