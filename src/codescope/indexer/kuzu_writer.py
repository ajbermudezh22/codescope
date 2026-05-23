"""Write SymbolRecord + CallRecord batches into a Kuzu embedded graph DB."""

from __future__ import annotations

from pathlib import Path

import kuzu

from codescope.indexer.scip_parser import CallRecord, SymbolRecord

_BATCH = 1000

_SCHEMA = [
    """
    CREATE NODE TABLE Symbol(
      id              STRING,
      name            STRING,
      qualified_name  STRING,
      kind            STRING,
      file            STRING,
      start_line      INT64,
      end_line        INT64,
      doc             STRING,
      signature       STRING,
      PRIMARY KEY (id)
    )
    """,
    "CREATE REL TABLE CALLS (FROM Symbol TO Symbol)",
]


class KuzuWriter:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = kuzu.Database(str(self.db_path))
        self._conn = kuzu.Connection(self._db)

    def create_schema(self) -> None:
        for stmt in _SCHEMA:
            self._conn.execute(stmt)

    def write_symbols(self, symbols: list[SymbolRecord]) -> None:
        for i in range(0, len(symbols), _BATCH):
            batch = symbols[i : i + _BATCH]
            self._conn.execute(
                """
                UNWIND $rows AS row
                CREATE (s:Symbol {
                  id: row.id,
                  name: row.name,
                  qualified_name: row.qualified_name,
                  kind: row.kind,
                  file: row.file,
                  start_line: row.start_line,
                  end_line: row.end_line,
                  doc: row.doc,
                  signature: row.signature
                })
                """,
                {"rows": [s.__dict__ for s in batch]},
            )

    def write_calls(self, calls: list[CallRecord]) -> None:
        unique = {(c.caller_id, c.callee_id) for c in calls}
        rows = [{"src": a, "dst": b} for a, b in unique]
        for i in range(0, len(rows), _BATCH):
            batch = rows[i : i + _BATCH]
            self._conn.execute(
                """
                UNWIND $rows AS row
                MATCH (a:Symbol {id: row.src}), (b:Symbol {id: row.dst})
                CREATE (a)-[:CALLS]->(b)
                """,
                {"rows": batch},
            )

    def close(self) -> None:
        self._conn = None
        self._db = None
