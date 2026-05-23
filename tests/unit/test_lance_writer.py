import lancedb

from codescope.indexer.embedder import Embedder
from codescope.indexer.lance_writer import LanceWriter
from codescope.indexer.scip_parser import SymbolRecord


def _docs() -> list[SymbolRecord]:
    return [
        SymbolRecord(
            id="x://verify_token",
            name="verify_token",
            qualified_name="tiny.auth.verify_token",
            kind="Function",
            file="tiny/auth.py",
            start_line=4,
            end_line=10,
            doc="Return True if the token is valid.",
            signature="def verify_token(token: str) -> bool",
        ),
        SymbolRecord(
            id="x://undocumented",
            name="helper",
            qualified_name="tiny.internal.helper",
            kind="Function",
            file="tiny/internal.py",
            start_line=1,
            end_line=3,
            doc="",
            signature="def helper()",
        ),
    ]


def test_lance_writer_embeds_only_documented_symbols(tmp_path):
    embedder = Embedder()
    writer = LanceWriter(tmp_path / "vec.lance", embedder=embedder)
    writer.write(_docs())

    db = lancedb.connect(str(tmp_path / "vec.lance"))
    table = db.open_table("symbols")
    rows = table.to_pandas()
    assert len(rows) == 1
    assert rows["symbol_id"][0] == "x://verify_token"
    assert len(rows["vector"][0]) == 384
