"""Orchestrate scip-python → parse → Kuzu + LanceDB."""

from __future__ import annotations

import shutil
from pathlib import Path

from codescope.indexer.embedder import Embedder
from codescope.indexer.kuzu_writer import KuzuWriter
from codescope.indexer.lance_writer import LanceWriter
from codescope.indexer.scip_parser import parse_index
from codescope.indexer.scip_runner import run_scip


def index_repo(repo_path: Path, db_dir: Path, force: bool = False) -> None:
    repo_path = Path(repo_path).resolve()
    db_dir = Path(db_dir).resolve()

    if db_dir.exists():
        if not force:
            raise FileExistsError(
                f"{db_dir} already exists. Pass force=True to overwrite."
            )
        shutil.rmtree(db_dir)
    db_dir.mkdir(parents=True)

    scip_file = db_dir / "index.scip"
    print(f"[1/4] Running scip-python on {repo_path}…")
    run_scip(repo_path=repo_path, output=scip_file)

    print("[2/4] Parsing SCIP index…")
    symbols, calls = parse_index(scip_file)
    print(f"      {len(symbols)} symbols, {len(calls)} call edges")

    print("[3/4] Writing Kuzu graph…")
    kw = KuzuWriter(db_dir / "graph.kuzu")
    kw.create_schema()
    kw.write_symbols(symbols)
    kw.write_calls(calls)
    kw.close()

    print("[4/4] Writing LanceDB embeddings…")
    lw = LanceWriter(db_dir / "vec.lance", embedder=Embedder())
    lw.write(symbols)

    print(f"Done. Index at {db_dir}")
