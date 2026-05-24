import kuzu

from codescope.indexer.kuzu_writer import KuzuWriter
from codescope.indexer.scip_parser import CallRecord, SymbolRecord


def _sample_symbols() -> list[SymbolRecord]:
    return [
        SymbolRecord(
            id="scip://.../verify_token().",
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
            id="scip://.../authorize_request().",
            name="authorize_request",
            qualified_name="tiny.api.authorize_request",
            kind="Function",
            file="tiny/api.py",
            start_line=6,
            end_line=10,
            doc="Authorize an incoming request.",
            signature="def authorize_request(token: str) -> dict",
        ),
    ]


def _sample_calls() -> list[CallRecord]:
    return [
        CallRecord(
            caller_id="scip://.../authorize_request().",
            callee_id="scip://.../verify_token().",
            caller_qualified_name="tiny.api.authorize_request",
            callee_qualified_name="tiny.auth.verify_token",
            file="tiny/api.py",
            line=8,
        )
    ]


def test_kuzu_writer_persists_symbols_and_call_edges(tmp_path):
    db_path = tmp_path / "graph.kuzu"
    writer = KuzuWriter(db_path)
    writer.create_schema()
    writer.write_symbols(_sample_symbols())
    writer.write_calls(_sample_calls())
    writer.close()

    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    result = conn.execute("MATCH (s:Symbol) RETURN count(s) AS n").get_as_df()
    assert result["n"][0] == 2

    result = conn.execute(
        "MATCH (a:Symbol)-[:CALLS]->(b:Symbol) "
        "RETURN a.qualified_name AS caller, b.qualified_name AS callee"
    ).get_as_df()
    assert len(result) == 1
    assert result["caller"][0] == "tiny.api.authorize_request"
    assert result["callee"][0] == "tiny.auth.verify_token"
