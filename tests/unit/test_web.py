import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from codescope.indexer.pipeline import index_repo
from codescope.web.app import build_app

TINY_REPO = Path(__file__).parent.parent / "fixtures" / "tiny_repo"


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    if not shutil.which("scip-python"):
        pytest.skip("scip-python not installed")
    db = tmp_path_factory.mktemp("web") / ".codescope"
    index_repo(repo_path=TINY_REPO, db_dir=db)
    return build_app(db)


def test_status_endpoint(app):
    client = TestClient(app)
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["indexed"] is True
    assert body["symbol_count"] >= 3


def test_symbol_endpoint(app):
    from urllib.parse import quote

    from codescope.store.tools import Tools

    client = TestClient(app)
    db_dir = Path(app.state.db_dir)
    hits = Tools.open(db_dir).find_symbol("verify token", k=1)
    assert hits, "expected at least one hit"
    sid = hits[0].symbol_id

    r = client.get(f"/api/symbol/{quote(sid, safe='')}")
    assert r.status_code == 200
    body = r.json()
    assert body["qualified_name"] == "tiny.auth.verify_token"
    assert "def verify_token" in body["source"]
