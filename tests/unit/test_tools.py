import shutil
from pathlib import Path

import pytest

from codescope.indexer.pipeline import index_repo
from codescope.store.tools import Tools

TINY_REPO = Path(__file__).parent.parent / "fixtures" / "tiny_repo"


@pytest.fixture(scope="module")
def indexed_tiny(tmp_path_factory):
    if not shutil.which("scip-python"):
        pytest.skip("scip-python not installed")
    db_dir = tmp_path_factory.mktemp("idx") / ".codescope"
    index_repo(repo_path=TINY_REPO, db_dir=db_dir)
    return db_dir


def test_find_symbol_returns_relevant_hits(indexed_tiny):
    tools = Tools.open(indexed_tiny)
    hits = tools.find_symbol("validate a token", k=3)
    qns = [h.qualified_name for h in hits]
    assert "tiny.auth.verify_token" in qns
    assert hits[0].qualified_name == "tiny.auth.verify_token"
    assert hits[0].kind == "Function"


def test_find_symbol_respects_kind_filter(indexed_tiny):
    tools = Tools.open(indexed_tiny)
    # tiny_repo contains only Function symbols (no classes), so filter by Function
    hits = tools.find_symbol("function", kind="Function", k=10)
    for h in hits:
        assert h.kind == "Function"
