"""Parse a SCIP protobuf index into Symbol and Call records.

Real scip-python 0.6.6 monikers look like:

    scip-python python tiny 0.0.1 `tiny.auth`/verify_token().
    scip-python python tiny 0.0.1 `tiny.api`/authorize_request().(token)
    scip-python python tiny 0.0.1 tiny/__init__:

We convert the descriptor (the last space-separated token) to a dotted
qualified name like ``tiny.auth.verify_token`` by:

1. Stripping backtick-quoted module prefixes (`` `tiny.auth` ``→ ``tiny.auth``)
2. Replacing the ``/`` separator between module and name with ``.``
3. Removing suffixes: ``().``, ``(.).``, ``#``, ``:`` and any trailing ``.``

NOTE: The reference plan described a ``tiny/auth.py/verify_token().`` style
descriptor, but scip-python 0.6.6 actually emits the dotted form with
backticks.  The parser below handles the real format.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from codescope.indexer import scip_pb2


@dataclass(frozen=True)
class SymbolRecord:
    id: str
    name: str
    qualified_name: str
    kind: str
    file: str
    start_line: int
    end_line: int
    doc: str
    signature: str


@dataclass(frozen=True)
class CallRecord:
    caller_id: str
    callee_id: str
    caller_qualified_name: str
    callee_qualified_name: str
    file: str
    line: int


# Map trailing moniker suffix → kind.  Order matters: check longer suffixes first.
_KIND_SUFFIXES: list[tuple[str, str]] = [
    ("(.).", "Method"),
    ("().", "Function"),
    (":()", "Function"),  # alternate style
    ("#", "Class"),
    (":", "Module"),
    ("/", "Module"),
]


def _kind_from_moniker(moniker: str) -> str:
    for suffix, kind in _KIND_SUFFIXES:
        if moniker.endswith(suffix):
            return kind
    # Parameters like `verify_token().(token)` – treat as Variable
    return "Variable"


def _qualified_name_from_moniker(moniker: str) -> str:
    """Convert a SCIP moniker to a dotted qualified name.

    Handles both descriptor styles emitted by scip-python 0.6.6:

    * Backtick-module style: ``scip-python python tiny 0.0.1 `tiny.auth`/verify_token().``
      → ``tiny.auth.verify_token``
    * Legacy path style (plan docs):  ``scip-python python . tiny/auth.py/verify_token().``
      → ``tiny.auth.verify_token``
    """
    # Split on spaces; descriptor is everything after the 4th token
    parts = moniker.split(" ", 4)
    descriptor = parts[4] if len(parts) >= 5 else moniker

    # Strip backtick-quoted module prefix: `` `foo.bar` `` → ``foo.bar``
    descriptor = re.sub(r"`([^`]+)`/", r"\1.", descriptor)

    # Strip .py extension segments (legacy style)
    descriptor = descriptor.replace(".py/", ".")
    descriptor = descriptor.replace("/", ".")

    # Remove known trailing suffixes in order (longest first)
    for suffix, _ in _KIND_SUFFIXES:
        if descriptor.endswith(suffix):
            descriptor = descriptor[: -len(suffix)]
            break

    # Remove parenthesised parameter fragments: `(token)` or `.(token)`
    descriptor = re.sub(r"\.?\([^)]*\)$", "", descriptor)

    # Strip leading/trailing dots
    descriptor = descriptor.strip(".")

    return descriptor


def parse_index(scip_path: Path) -> tuple[list[SymbolRecord], list[CallRecord]]:
    """Parse a ``.scip`` file and return ``(symbols, calls)``."""
    index = scip_pb2.Index()
    index.ParseFromString(Path(scip_path).read_bytes())

    info_by_symbol: dict[str, scip_pb2.SymbolInformation] = {}
    for doc in index.documents:
        for s in doc.symbols:
            info_by_symbol[s.symbol] = s

    symbols: list[SymbolRecord] = []
    calls: list[CallRecord] = []
    seen_symbol_ids: set[str] = set()

    for doc in index.documents:
        file_path = doc.relative_path
        # Collect (occurrence, symbol_id) pairs for definitions in this file
        defs_in_file: list[tuple[scip_pb2.Occurrence, str]] = []

        # First pass: collect definitions
        for occ in doc.occurrences:
            is_def = bool(occ.symbol_roles & scip_pb2.SymbolRole.Value("Definition"))
            if not is_def:
                continue
            if occ.symbol in seen_symbol_ids:
                defs_in_file.append((occ, occ.symbol))
                continue

            info = info_by_symbol.get(occ.symbol)
            doc_text = ""
            signature = ""
            if info:
                # documentation[0] is usually the signature, [1] is the docstring
                docs = list(info.documentation)
                # Signature is the first doc entry when it looks like a code block
                if docs and docs[0].startswith("```"):
                    signature = docs[0]
                    doc_text = "\n".join(docs[1:])
                else:
                    doc_text = "\n".join(docs)
                if info.signature_documentation.text:
                    signature = info.signature_documentation.text

            start = occ.range[0] if len(occ.range) >= 1 else 0
            end = occ.range[2] if len(occ.range) >= 3 else start
            qn = _qualified_name_from_moniker(occ.symbol)
            kind = _kind_from_moniker(occ.symbol)

            symbols.append(
                SymbolRecord(
                    id=occ.symbol,
                    name=qn.rsplit(".", 1)[-1] if "." in qn else qn,
                    qualified_name=qn,
                    kind=kind,
                    file=file_path,
                    start_line=start,
                    end_line=end,
                    doc=doc_text,
                    signature=signature,
                )
            )
            seen_symbol_ids.add(occ.symbol)
            defs_in_file.append((occ, occ.symbol))

        # Second pass: collect call references
        for occ in doc.occurrences:
            is_def = bool(occ.symbol_roles & scip_pb2.SymbolRole.Value("Definition"))
            if is_def:
                continue
            # Skip local symbols (not cross-file references)
            if occ.symbol.startswith("local "):
                continue
            ref_line = occ.range[0] if len(occ.range) >= 1 else 0
            enclosing = _enclosing_def(defs_in_file, ref_line)
            if not enclosing or enclosing == occ.symbol:
                continue
            calls.append(
                CallRecord(
                    caller_id=enclosing,
                    callee_id=occ.symbol,
                    caller_qualified_name=_qualified_name_from_moniker(enclosing),
                    callee_qualified_name=_qualified_name_from_moniker(occ.symbol),
                    file=file_path,
                    line=ref_line,
                )
            )

    return symbols, calls


def _enclosing_def(
    defs: list[tuple[scip_pb2.Occurrence, str]], line: int
) -> str | None:
    """Return the symbol id of the closest preceding definition on or before ``line``."""
    best: tuple[int, str] | None = None
    for occ, sid in defs:
        d_line = occ.range[0] if len(occ.range) >= 1 else 0
        if d_line <= line and (best is None or d_line > best[0]):
            best = (d_line, sid)
    return best[1] if best else None
