"""Naive-RAG baseline: top-k vector search, one LLM call, no graph, no agent.

Uses the exact same embedder and LanceDB table codescope indexes into, so the
retrieval corpus is identical — the only difference is what happens after
retrieval. Writes the same JSONL schema as run_codescope.py, so auto_score.py
picks the results up unchanged.

Usage:
    python eval/run_naive.py --db .codescope-fastapi --model anthropic/claude-opus-5
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import lancedb
import litellm
import yaml

from codescope.indexer.embedder import Embedder

SYSTEM = (
    "You answer questions about the fastapi codebase using ONLY the provided "
    "context snippets (symbol name + signature + docstring). When the answer is "
    "a symbol, give its fully-qualified dotted name. If the context is "
    "insufficient, say so briefly."
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path(".codescope-fastapi"))
    parser.add_argument("--questions", type=Path, default=Path("eval/questions.yaml"))
    parser.add_argument("--out", type=Path, default=Path("eval/results-naive.jsonl"))
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--k", type=int, default=8)
    args = parser.parse_args()

    questions = yaml.safe_load(args.questions.read_text())
    table = lancedb.connect(str(args.db / "vec.lance")).open_table("symbols")
    embedder = Embedder()

    rows_out = []
    for row in questions:
        if "TODO" in str(row):
            continue
        question = row["q"]
        [qvec] = embedder.embed([question])
        hits = table.search(qvec).limit(args.k).to_list()
        context = "\n\n---\n\n".join(h["text"] for h in hits)
        resp = litellm.completion(
            model=args.model,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
            ],
        )
        answer = resp.choices[0].message.content or ""
        rows_out.append(
            {
                "id": row["id"],
                "q": row["q"],
                "expected": row["expected_symbol"],
                "answer": answer,
                "tool_calls": [],
            }
        )
        print(f"{row['id']}: {len(answer)} chars")

    with args.out.open("w") as f:
        for r in rows_out:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {len(rows_out)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
