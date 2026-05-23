"""Write per-symbol embeddings to a LanceDB table."""

from __future__ import annotations

from pathlib import Path

import lancedb

from codescope.indexer.embedder import Embedder
from codescope.indexer.scip_parser import SymbolRecord


def _embedding_text(s: SymbolRecord) -> str:
    """Concatenate name + signature + doc into one searchable blob."""
    parts = [s.qualified_name]
    if s.signature:
        parts.append(s.signature)
    if s.doc:
        parts.append(s.doc[:500])
    return "\n".join(parts)


class LanceWriter:
    def __init__(self, db_path: Path, embedder: Embedder) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(str(self.db_path))
        self._embedder = embedder

    def write(self, symbols: list[SymbolRecord]) -> None:
        documented = [s for s in symbols if s.doc and s.doc.strip()]
        if not documented:
            return
        texts = [_embedding_text(s) for s in documented]
        vectors = self._embedder.embed(texts)
        records = [
            {"symbol_id": s.id, "text": t, "vector": v}
            for s, t, v in zip(documented, texts, vectors)
        ]
        # Let LanceDB infer the schema from the first batch — avoids pyarrow
        # fixed-size-list incantation differences across versions.
        if "symbols" in self._db.list_tables():
            self._db.open_table("symbols").add(records)
        else:
            self._db.create_table("symbols", data=records)
