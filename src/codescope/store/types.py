"""Public dataclasses returned by the Tools API."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SymbolHit:
    symbol_id: str
    name: str
    qualified_name: str
    kind: str
    file: str
    signature: str
    doc_excerpt: str
    score: float


@dataclass(frozen=True)
class CallSite:
    caller_id: str
    caller_qualified_name: str
    callee_id: str
    callee_qualified_name: str
    file: str
    line: int


@dataclass(frozen=True)
class SourceSlice:
    symbol_id: str
    qualified_name: str
    file: str
    start_line: int
    end_line: int
    source: str
