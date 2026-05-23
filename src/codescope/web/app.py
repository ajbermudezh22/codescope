from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from codescope.web.chat_ws import build_chat_router
from codescope.web.status import compute_status
from codescope.web.symbol import build_symbol_router


def build_app(db_dir: Path) -> FastAPI:
    db_dir = Path(db_dir)
    app = FastAPI(title="codescope")
    app.state.db_dir = str(db_dir)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/status")
    def status() -> dict:
        return asdict(compute_status(db_dir))

    app.include_router(build_symbol_router(db_dir))
    app.include_router(build_chat_router(db_dir))

    return app
