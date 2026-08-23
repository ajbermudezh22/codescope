"""LLM-synthesized docstrings for undocumented symbols (opt-in).

Indexing stays zero-LLM by default; `codescope index --synthesize-docs` fills
the docs of undocumented Functions/Classes in the main package so they become
retrievable by vector search. Synthesized ids are recorded in
`synthetic_docs.json` next to the index for transparency.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import litellm

from codescope.indexer.scip_parser import SymbolRecord

KINDS = {"Function", "Class", "Method", "Module"}
SKIP_PREFIXES = ("docs_src/", "tests/", "docs/")
SNIPPET_LINES = 40
BATCH = 20

PROMPT = """For each numbered Python symbol below, write a concise 1-2 sentence docstring
describing what it does (not how). Ground every statement in the code shown.

Respond with ONLY a JSON array: [{{"idx": <number>, "doc": "<docstring>"}}]

{items}"""


def pick_targets(symbols: list[SymbolRecord]) -> list[SymbolRecord]:
    return [
        s for s in symbols
        if not (s.doc and s.doc.strip())
        and s.kind in KINDS
        and not s.file.startswith(SKIP_PREFIXES)
    ]


def _snippet(repo_root: Path, s: SymbolRecord) -> str:
    try:
        lines = (repo_root / s.file).read_text(errors="replace").splitlines()
    except OSError:
        return s.signature or s.qualified_name
    # end_line from SCIP is not a reliable definition end; take a fixed window.
    start = max(s.start_line - 1, 0)
    return "\n".join(lines[start : start + SNIPPET_LINES])


def _run_batch(batch: list[SymbolRecord], repo_root: Path, model: str) -> dict[str, str]:
    items = "\n\n".join(
        f"{i + 1}. {s.qualified_name} ({s.kind})\n```python\n{_snippet(repo_root, s)}\n```"
        for i, s in enumerate(batch)
    )
    resp = litellm.completion(
        model=model,
        messages=[{"role": "user", "content": PROMPT.format(items=items)}],
    )
    text = (resp.choices[0].message.content or "").strip()
    if text.startswith("```"):
        text = text.strip("`\n")
        text = text[text.index("["):]
    out: dict[str, str] = {}
    try:
        arr = json.loads(text)
    except json.JSONDecodeError:
        return out
    for entry in arr:
        idx = entry.get("idx", 0) - 1
        doc = (entry.get("doc") or "").strip()
        if 0 <= idx < len(batch) and doc:
            out[batch[idx].id] = doc
    return out


def synthesize(
    symbols: list[SymbolRecord],
    repo_root: Path,
    model: str = "anthropic/claude-haiku-4-5",
    max_workers: int = 4,
) -> dict[str, str]:
    """Return {symbol_id: synthesized_doc} for undocumented main-package symbols."""
    targets = pick_targets(symbols)
    if not targets:
        return {}
    batches = [targets[i : i + BATCH] for i in range(0, len(targets), BATCH)]
    docs: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for result in pool.map(lambda b: _run_batch(b, repo_root, model), batches):
            docs.update(result)
    return docs
