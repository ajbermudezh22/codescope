from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import kuzu


@dataclass(frozen=True)
class Status:
    indexed: bool
    repo_name: str
    symbol_count: int


def compute_status(db_dir: Path) -> Status:
    db_dir = Path(db_dir)
    graph = db_dir / "graph.kuzu"
    if not graph.exists():
        return Status(indexed=False, repo_name="", symbol_count=0)
    conn = kuzu.Connection(kuzu.Database(str(graph)))
    count = int(conn.execute("MATCH (s:Symbol) RETURN count(s) AS n").get_as_df()["n"][0])
    repo_root_file = db_dir / "repo_root.txt"
    repo_name = (
        Path(repo_root_file.read_text().strip()).name
        if repo_root_file.exists()
        else ""
    )
    return Status(indexed=True, repo_name=repo_name, symbol_count=count)
