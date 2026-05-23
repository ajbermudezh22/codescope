import shutil
from pathlib import Path

import kuzu
import lancedb
import pytest

from codescope.indexer.pipeline import index_repo

TINY_REPO = Path(__file__).parent.parent / "fixtures" / "tiny_repo"


def test_index_repo_creates_kuzu_and_lance(tmp_path):
    if not shutil.which("scip-python"):
        pytest.skip("scip-python not installed")
    db_dir = tmp_path / ".codescope"
    index_repo(repo_path=TINY_REPO, db_dir=db_dir)

    assert (db_dir / "graph.kuzu").exists()
    assert (db_dir / "vec.lance").exists()

    conn = kuzu.Connection(kuzu.Database(str(db_dir / "graph.kuzu")))
    sym_count = conn.execute("MATCH (s:Symbol) RETURN count(s) AS n").get_as_df()["n"][0]
    assert sym_count >= 3

    vdb = lancedb.connect(str(db_dir / "vec.lance"))
    assert "symbols" in vdb.table_names() or "symbols" in vdb.list_tables()
