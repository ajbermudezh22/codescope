"""Typed retrieval API. The only path the agent has into storage."""

from __future__ import annotations

from pathlib import Path

import kuzu
import lancedb

from codescope.indexer.embedder import Embedder
from codescope.store.types import CallSite, SourceSlice, SymbolHit


class Tools:
    def __init__(
        self,
        kuzu_conn: kuzu.Connection,
        lance_table,
        embedder: Embedder,
        repo_root: Path,
    ) -> None:
        self._kuzu = kuzu_conn
        self._lance = lance_table
        self._embedder = embedder
        self._repo_root = repo_root

    @classmethod
    def open(cls, db_dir: Path) -> "Tools":
        db_dir = Path(db_dir)
        kdb = kuzu.Database(str(db_dir / "graph.kuzu"))
        kconn = kuzu.Connection(kdb)
        ldb = lancedb.connect(str(db_dir / "vec.lance"))
        table = ldb.open_table("symbols")
        repo_root = Path.cwd()  # W1-11 will replace this with repo_root.txt read
        return cls(kconn, table, Embedder(), repo_root)

    def find_symbol(
        self, query: str, kind: str | None = None, k: int = 5
    ) -> list[SymbolHit]:
        [qvec] = self._embedder.embed([query])
        fetch = k * 4 if kind else k
        rows = self._lance.search(qvec).limit(fetch).to_list()
        symbol_ids = [r["symbol_id"] for r in rows]
        if not symbol_ids:
            return []
        df = self._kuzu.execute(
            "MATCH (s:Symbol) WHERE s.id IN $ids "
            "RETURN s.id AS id, s.name AS name, s.qualified_name AS qn, "
            "s.kind AS kind, s.file AS file, s.signature AS sig, s.doc AS doc",
            {"ids": symbol_ids},
        ).get_as_df()
        by_id = {row["id"]: row for _, row in df.iterrows()}
        out: list[SymbolHit] = []
        for r in rows:
            meta = by_id.get(r["symbol_id"])
            if meta is None:
                continue
            if kind and meta["kind"] != kind:
                continue
            out.append(
                SymbolHit(
                    symbol_id=r["symbol_id"],
                    name=meta["name"],
                    qualified_name=meta["qn"],
                    kind=meta["kind"],
                    file=meta["file"],
                    signature=meta["sig"] or "",
                    doc_excerpt=(meta["doc"] or "")[:200],
                    score=1.0 - r["_distance"],
                )
            )
            if len(out) >= k:
                break
        return out
