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
        repo_root_file = db_dir / "repo_root.txt"
        repo_root = (
            Path(repo_root_file.read_text().strip())
            if repo_root_file.exists()
            else Path.cwd()
        )
        return cls(kconn, table, Embedder(), repo_root)

    def find_symbol(
        self, query: str, kind: str | None = None, k: int = 5
    ) -> list[SymbolHit]:
        import math

        [qvec] = self._embedder.embed([query])
        # Over-fetch so the re-ranker has room to reshuffle.
        fetch = max(k * 3, 15)
        rows = self._lance.search(qvec).limit(fetch).to_list()
        symbol_ids = [r["symbol_id"] for r in rows]
        if not symbol_ids:
            return []

        # Pull Kuzu metadata for all candidates in one query.
        df = self._kuzu.execute(
            "MATCH (s:Symbol) WHERE s.id IN $ids "
            "RETURN s.id AS id, s.name AS name, s.qualified_name AS qn, "
            "s.kind AS kind, s.file AS file, s.signature AS sig, s.doc AS doc",
            {"ids": symbol_ids},
        ).get_as_df()
        by_id = {row["id"]: row for _, row in df.iterrows()}

        # Batch caller-count query: in-degree on CALLS for all candidates.
        callers_df = self._kuzu.execute(
            "MATCH (caller:Symbol)-[:CALLS]->(s:Symbol) "
            "WHERE s.id IN $ids "
            "RETURN s.id AS id, count(caller) AS n",
            {"ids": symbol_ids},
        ).get_as_df()
        callers_by_id: dict[str, int] = {
            row["id"]: int(row["n"]) for _, row in callers_df.iterrows()
        }

        # Re-score: vector similarity blended with log1p of caller count.
        # Weight 0.15 means a symbol with ~e^7 callers (~1096) would be on par
        # with a perfect vector match. Practically the centrality term breaks
        # ties between near-equal embeddings; even a single caller (log1p(1)≈0.69)
        # adds ~0.10 to the score, enough to consistently lift called symbols
        # over uncalled ones with similar embeddings.
        scored: list[tuple[float, dict, dict]] = []
        for r in rows:
            meta = by_id.get(r["symbol_id"])
            if meta is None:
                continue
            if kind and meta["kind"] != kind:
                continue
            vector_score = 1.0 - r["_distance"]
            callers = callers_by_id.get(r["symbol_id"], 0)
            blended = vector_score + 0.15 * math.log1p(callers)
            scored.append((blended, r, meta))

        scored.sort(key=lambda t: t[0], reverse=True)
        out: list[SymbolHit] = []
        for blended, r, meta in scored[:k]:
            out.append(
                SymbolHit(
                    symbol_id=r["symbol_id"],
                    name=meta["name"],
                    qualified_name=meta["qn"],
                    kind=meta["kind"],
                    file=meta["file"],
                    signature=meta["sig"] or "",
                    doc_excerpt=(meta["doc"] or "")[:200],
                    score=blended,
                )
            )
        return out

    # --- callers / callees ----------------------------------------------

    def callers_of(self, symbol_id: str, depth: int = 1) -> list[CallSite]:
        depth = max(1, min(depth, 3))
        df = self._kuzu.execute(
            f"""
            MATCH (caller:Symbol)-[:CALLS*1..{depth}]->(callee:Symbol)
            WHERE callee.id = $id
            RETURN DISTINCT caller.id AS caller_id,
                            caller.qualified_name AS caller_qn,
                            caller.file AS file
            """,
            {"id": symbol_id},
        ).get_as_df()
        return [
            CallSite(
                caller_id=row["caller_id"],
                caller_qualified_name=row["caller_qn"],
                callee_id=symbol_id,
                callee_qualified_name="",
                file=row["file"],
                line=0,
            )
            for _, row in df.iterrows()
        ]

    def callees_of(self, symbol_id: str, depth: int = 1) -> list[CallSite]:
        depth = max(1, min(depth, 3))
        df = self._kuzu.execute(
            f"""
            MATCH (caller:Symbol)-[:CALLS*1..{depth}]->(callee:Symbol)
            WHERE caller.id = $id
            RETURN DISTINCT callee.id AS callee_id,
                            callee.qualified_name AS callee_qn,
                            callee.file AS file
            """,
            {"id": symbol_id},
        ).get_as_df()
        return [
            CallSite(
                caller_id=symbol_id,
                caller_qualified_name="",
                callee_id=row["callee_id"],
                callee_qualified_name=row["callee_qn"],
                file=row["file"],
                line=0,
            )
            for _, row in df.iterrows()
        ]

    # --- read_source -----------------------------------------------------

    def read_source(self, symbol_id: str, with_context_lines: int = 0) -> SourceSlice:
        df = self._kuzu.execute(
            "MATCH (s:Symbol) WHERE s.id = $id "
            "RETURN s.qualified_name AS qn, s.file AS file, "
            "s.start_line AS start_ln, s.end_line AS end_ln",
            {"id": symbol_id},
        ).get_as_df()
        if len(df) == 0:
            raise KeyError(f"Symbol not found: {symbol_id}")
        row = df.iloc[0]
        file_path = self._repo_root / row["file"]
        text = file_path.read_text()
        lines = text.splitlines()
        start = max(0, int(row["start_ln"]) - with_context_lines)
        end = min(len(lines), int(row["end_ln"]) + 1 + with_context_lines)
        source = "\n".join(lines[start:end])
        return SourceSlice(
            symbol_id=symbol_id,
            qualified_name=row["qn"],
            file=row["file"],
            start_line=start,
            end_line=end,
            source=source,
        )
