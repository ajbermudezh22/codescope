"""Heuristic scorer for the codescope eval.

Reads eval/questions.yaml + eval/results-codescope.jsonl, writes
eval/auto-scores.csv with one row per question: id, grade (auto), notes.

This is a HEURISTIC. A ok from this script means "the answer text contained
the expected qualified name verbatim". It does NOT mean the explanation was
correct. Manually review and downgrade as needed.

Usage:
    python eval/auto_score.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import yaml

QUESTIONS = Path("eval/questions.yaml")
RESULTS = Path("eval/results-codescope.jsonl")
OUT = Path("eval/auto-scores.csv")


def grade(expected: str, answer: str) -> tuple[str, str]:
    if not answer or answer.strip().startswith("(truncated"):
        return "x", "truncated or empty"
    if expected in answer:
        return "ok", "expected qualified name appears verbatim"
    last = expected.rsplit(".", 1)[-1].lstrip("#")
    if last and last in answer:
        return "partial", f"only last segment '{last}' appears"
    return "x", "expected symbol not in answer"


def main() -> int:
    questions = {q["id"]: q for q in yaml.safe_load(QUESTIONS.read_text())}
    results = [json.loads(line) for line in RESULTS.read_text().splitlines() if line.strip()]

    counts = {"ok": 0, "partial": 0, "x": 0}
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "auto_grade", "note", "tool_calls"])
        for r in results:
            q = questions.get(r["id"], {})
            g, note = grade(r["expected"], r["answer"])
            counts[g] += 1
            w.writerow([r["id"], g, note, len(r.get("tool_calls", []))])

    print(f"Wrote {OUT}")
    print(f"Auto-scores: ok={counts['ok']}, partial={counts['partial']}, x={counts['x']}")
    print("Heuristic — manually review and downgrade as needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
