"""Orchestrate scip-python → parse → Kuzu + LanceDB."""

from __future__ import annotations

import dataclasses
import json
import shutil
from pathlib import Path

from codescope.indexer.embedder import Embedder
from codescope.indexer.kuzu_writer import KuzuWriter
from codescope.indexer.lance_writer import LanceWriter
from codescope.indexer.scip_parser import parse_index
from codescope.indexer.scip_runner import run_scip


def index_repo(
    repo_path: Path,
    db_dir: Path,
    force: bool = False,
    synthesize_docs: bool = False,
    synth_model: str = "anthropic/claude-haiku-4-5",
) -> None:
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

    if synthesize_docs:
        from codescope.indexer.doc_synth import synthesize

        print("      Synthesizing docs for undocumented symbols…")
        synth = synthesize(symbols, repo_root=repo_path, model=synth_model)
        symbols = [
            dataclasses.replace(s, doc=synth[s.id]) if s.id in synth else s
            for s in symbols
        ]
        (db_dir / "synthetic_docs.json").write_text(json.dumps(sorted(synth)))
        print(f"      {len(synth)} docs synthesized")

    print("[3/4] Writing Kuzu graph…")
    kw = KuzuWriter(db_dir / "graph.kuzu")
    kw.create_schema()
    kw.write_symbols(symbols)
    kw.write_calls(calls)
    kw.close()

    print("[4/4] Writing LanceDB embeddings…")
    lw = LanceWriter(db_dir / "vec.lance", embedder=Embedder())
    lw.write(symbols)

    (db_dir / "repo_root.txt").write_text(str(repo_path))
    print(f"Done. Index at {db_dir}")
