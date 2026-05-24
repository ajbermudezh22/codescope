import shutil
from pathlib import Path

import pytest

from codescope.indexer.scip_parser import _is_test_path, parse_index
from codescope.indexer.scip_runner import run_scip

TINY_REPO = Path(__file__).parent.parent / "fixtures" / "tiny_repo"


@pytest.fixture(scope="module")
def tiny_index(tmp_path_factory):
    if not shutil.which("scip-python"):
        pytest.skip("scip-python not installed")
    out = tmp_path_factory.mktemp("scip") / "index.scip"
    run_scip(repo_path=TINY_REPO, output=out)
    return out


def test_parse_index_yields_known_symbols(tiny_index):
    symbols, calls = parse_index(tiny_index)
    names = {s.qualified_name for s in symbols}
    assert "tiny.auth.verify_token" in names
    assert "tiny.auth.issue_token" in names
    assert "tiny.api.authorize_request" in names


def test_symbol_record_has_doc_and_signature(tiny_index):
    symbols, _ = parse_index(tiny_index)
    vt = next(s for s in symbols if s.qualified_name == "tiny.auth.verify_token")
    assert vt.kind == "Function"
    assert vt.file.endswith("auth.py")
    assert "Return True if the token is valid" in vt.doc


def test_parse_index_emits_call_from_authorize_to_verify(tiny_index):
    _, calls = parse_index(tiny_index)
    edges = {(c.caller_qualified_name, c.callee_qualified_name) for c in calls}
    assert ("tiny.api.authorize_request", "tiny.auth.verify_token") in edges


def test_is_test_path_detects_common_patterns():
    assert _is_test_path("tests/foo.py")
    assert _is_test_path("src/pkg/tests/bar.py")
    assert _is_test_path("test/foo.py")
    assert _is_test_path("pkg/test_module.py")
    assert _is_test_path("pkg/module_test.py")
    assert _is_test_path("conftest.py")
    assert _is_test_path("./tests/foo.py")
    # Negative cases
    assert not _is_test_path("src/pkg/main.py")
    assert not _is_test_path("app/services/chat.py")
    assert not _is_test_path("")
