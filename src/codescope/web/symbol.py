from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException

from codescope.store.tools import Tools


def build_symbol_router(db_dir: Path) -> APIRouter:
    router = APIRouter()
    tools = Tools.open(db_dir)

    @router.get("/api/symbol/{symbol_id:path}")
    def get_symbol(symbol_id: str) -> dict:
        symbol_id = unquote(symbol_id)
        try:
            slice_ = tools.read_source(symbol_id, with_context_lines=0)
        except KeyError as err:
            raise HTTPException(status_code=404, detail="symbol not found") from err
        return asdict(slice_)

    return router
