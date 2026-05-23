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


def test_callers_of_returns_known_caller(indexed_tiny):
    tools = Tools.open(indexed_tiny)
    [hit] = [h for h in tools.find_symbol("verify token", k=5)
             if h.qualified_name == "tiny.auth.verify_token"]
    callers = tools.callers_of(hit.symbol_id, depth=1)
    qns = [c.caller_qualified_name for c in callers]
    assert "tiny.api.authorize_request" in qns


def test_callees_of_returns_known_callee(indexed_tiny):
    tools = Tools.open(indexed_tiny)
    [hit] = [h for h in tools.find_symbol("authorize", k=5)
             if h.qualified_name == "tiny.api.authorize_request"]
    callees = tools.callees_of(hit.symbol_id, depth=1)
    qns = [c.callee_qualified_name for c in callees]
    assert "tiny.auth.verify_token" in qns


def test_read_source_returns_file_slice(indexed_tiny):
    tools = Tools.open(indexed_tiny)
    [hit] = [h for h in tools.find_symbol("verify token", k=5)
             if h.qualified_name == "tiny.auth.verify_token"]
    slice_ = tools.read_source(hit.symbol_id, with_context_lines=0)
    assert "def verify_token" in slice_.source
    assert "Return True if the token is valid" in slice_.source
    assert slice_.qualified_name == "tiny.auth.verify_token"
