"""Static checks on Alembic migrations (the real upgrade runs against Postgres in Docker/CI images)."""
import re
from pathlib import Path

VERSIONS = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def revisions():
    for path in sorted(VERSIONS.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        revision = re.search(r'^revision = "([^"]+)"', text, re.M).group(1)
        down = re.search(r'^down_revision = (?:"([^"]+)"|None)', text, re.M).group(1)
        yield path.name, revision, down


def test_revision_ids_fit_alembic_version_column():
    # alembic_version.version_num is VARCHAR(32); a longer id fails only when the upgrade runs.
    for name, revision, _ in revisions():
        assert len(revision) <= 32, f"{name}: revision id {revision!r} is {len(revision)} chars"


def test_migrations_form_a_single_chain():
    found = list(revisions())
    ids = {revision for _, revision, _ in found}
    roots = [name for name, _, down in found if down is None]
    assert len(roots) == 1, f"expected one initial migration, got {roots}"
    for name, _, down in found:
        assert down is None or down in ids, f"{name}: down_revision {down!r} does not exist"
