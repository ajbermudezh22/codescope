import shutil
from pathlib import Path

import pytest

from codescope.indexer.scip_runner import ScipNotInstalledError, run_scip

TINY_REPO = Path(__file__).parent.parent / "fixtures" / "tiny_repo"


def test_run_scip_against_tiny_repo_creates_index_file(tmp_path):
    if not shutil.which("scip-python"):
        pytest.skip("scip-python not installed")
    output = tmp_path / "index.scip"
    run_scip(repo_path=TINY_REPO, output=output)
    assert output.exists()
    assert output.stat().st_size > 0


def test_run_scip_raises_when_binary_missing(monkeypatch, tmp_path):
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(ScipNotInstalledError):
        run_scip(repo_path=tmp_path, output=tmp_path / "x.scip")
