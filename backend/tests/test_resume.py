from app.config import settings

PDF = b"%PDF-1.7\n1 0 obj << /Type /Catalog >> endobj\ntrailer << /Root 1 0 R >>\n%%EOF\n"


def upload(owner, profile_id, content=PDF, filename="My CV.pdf"):
    return owner.put(f"/api/profiles/{profile_id}/resume", files={"file": (filename, content, "application/pdf")})


def test_owner_uploads_and_anyone_downloads_public_resume(client, new_user, make_profile):
    owner = new_user()
    profile = make_profile(owner)
    response = upload(owner, profile["id"])
    assert response.status_code == 200
    assert response.json()["filename"] == "My CV.pdf"
    assert response.json()["size_bytes"] == len(PDF)

    assert client.get(f"/api/profiles/{profile['id']}").json()["has_resume"] is True
    download = client.get(f"/api/profiles/{profile['id']}/resume")
    assert download.status_code == 200
    assert download.content == PDF
    assert download.headers["content-type"] == "application/pdf"
    assert 'filename="My CV.pdf"' in download.headers["content-disposition"]

def test_uploading_again_replaces_the_resume(client, new_user, make_profile):
    owner = new_user()
    profile = make_profile(owner)
    upload(owner, profile["id"])
    newer = PDF + b"% updated\n"
    upload(owner, profile["id"], content=newer)
    assert client.get(f"/api/profiles/{profile['id']}/resume").content == newer

def test_rejects_files_that_are_not_pdfs(new_user, make_profile):
    owner = new_user()
    profile = make_profile(owner)
    # A renamed image is still not a PDF: the check reads the file's bytes, not its name.
    response = upload(owner, profile["id"], content=b"\x89PNG\r\n\x1a\nfake", filename="cv.pdf")
    assert response.status_code == 415

def test_rejects_files_over_the_size_limit(monkeypatch, new_user, make_profile):
    monkeypatch.setattr(settings, "max_resume_bytes", 64)
    owner = new_user()
    profile = make_profile(owner)
    assert upload(owner, profile["id"], content=PDF + b"x" * 64).status_code == 413

def test_only_the_owner_can_upload_or_delete(client, new_user, make_profile):
    owner = new_user()
    profile = make_profile(owner)
    assert upload(client, profile["id"]).status_code == 401
    assert upload(new_user(), profile["id"]).status_code == 403
    upload(owner, profile["id"])
    assert new_user().delete(f"/api/profiles/{profile['id']}/resume").status_code == 403

def test_limited_resume_is_only_for_owner_and_connections(client, new_user, make_profile, connect):
    owner, friend, stranger = new_user(), new_user(), new_user()
    profile = make_profile(owner, visibility="LIMITED")
    upload(owner, profile["id"])

    for outsider in (client, stranger):
        assert outsider.get(f"/api/profiles/{profile['id']}").json()["has_resume"] is False
        assert outsider.get(f"/api/profiles/{profile['id']}/resume").status_code == 404

    connect(owner, friend)
    assert friend.get(f"/api/profiles/{profile['id']}").json()["has_resume"] is True
    assert friend.get(f"/api/profiles/{profile['id']}/resume").status_code == 200
    assert owner.get(f"/api/profiles/{profile['id']}/resume").status_code == 200

def test_owner_can_remove_resume(client, new_user, make_profile):
    owner = new_user()
    profile = make_profile(owner)
    upload(owner, profile["id"])
    assert owner.delete(f"/api/profiles/{profile['id']}/resume").status_code == 204
    assert client.get(f"/api/profiles/{profile['id']}/resume").status_code == 404
    assert client.get(f"/api/profiles/{profile['id']}").json()["has_resume"] is False
    assert owner.delete(f"/api/profiles/{profile['id']}/resume").status_code == 404

def test_deleting_a_profile_deletes_its_resume(client, new_user, make_profile):
    owner = new_user()
    profile = make_profile(owner)
    upload(owner, profile["id"])
    owner.delete(f"/api/profiles/{profile['id']}")
    assert client.get(f"/api/profiles/{profile['id']}/resume").status_code == 404

def test_upload_strips_directories_from_the_filename(new_user, make_profile):
    owner = new_user()
    profile = make_profile(owner)
    response = upload(owner, profile["id"], filename="../../etc/passwd.exe")
    assert response.json()["filename"] == "passwd.exe.pdf"

def test_safe_filename():
    from app.routers.profiles import safe_filename

    assert safe_filename('../../etc/"evil".exe') == "evil.exe.pdf"
    assert safe_filename(r"C:\Users\me\cv.PDF") == "cv.PDF"
    assert safe_filename("My CV.pdf") == "My CV.pdf"
    assert safe_filename("..") == "resume.pdf"
    assert safe_filename(None) == "resume.pdf"
