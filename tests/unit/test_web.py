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
