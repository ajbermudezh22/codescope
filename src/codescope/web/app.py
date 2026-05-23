from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codescope.web.status import compute_status


def build_app(db_dir: Path) -> FastAPI:
    db_dir = Path(db_dir)
    app = FastAPI(title="codescope")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/status")
    def status() -> dict:
        return asdict(compute_status(db_dir))

    return app
