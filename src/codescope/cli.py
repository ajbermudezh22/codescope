"""codescope CLI: index, chat."""

from __future__ import annotations

from pathlib import Path

import typer

from codescope.indexer.pipeline import index_repo

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def index(
    repo: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),
    db: Path = typer.Option(Path(".codescope"), help="Where to write the index."),
    force: bool = typer.Option(False, help="Overwrite existing index."),
) -> None:
    """Index a Python repository."""
    index_repo(repo_path=repo, db_dir=db, force=force)


@app.command()
def chat(
    db: Path = typer.Option(Path(".codescope"), help="Path to indexed DB."),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8000),
) -> None:
    """Launch the chat server. (Wired up in W2.)"""
    import uvicorn

    from codescope.web.app import build_app

    uvicorn.run(build_app(db), host=host, port=port)


if __name__ == "__main__":
    app()
