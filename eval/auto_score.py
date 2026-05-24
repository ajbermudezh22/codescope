"""Heuristic scorer for all codescope eval runs.

Scans eval/results-*.jsonl and emits eval/auto-scores.csv with per-question
grades for each run, plus a summary printed to stdout.

The heuristic: a question scores `ok` if its expected qualified name appears
in the answer text. `partial` if only the last segment appears. Otherwise `x`.
Truncated answers (containing "turn budget exhausted") count as `x`.

This is heuristic only. Manually review and downgrade as needed —
e.g. an answer that contains the expected symbol but explains it wrong is
still `ok` by this heuristic.

Usage:
    python eval/auto_score.py
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import yaml

QUESTIONS = Path("eval/questions.yaml")
EVAL_DIR = Path("eval")
OUT = Path("eval/auto-scores.csv")


def grade(expected: str, answer: str) -> tuple[str, str]:
    if not answer or "(truncated" in answer:
        return "x", "truncated or empty"
    if expected in answer:
        return "ok", "expected qualified name verbatim"
    last = expected.rsplit(".", 1)[-1].lstrip("#")
    if last and last in answer:
        return "partial", f"only last segment '{last}' appears"
    return "x", "expected symbol not in answer"


def main() -> int:
    yaml.safe_load(QUESTIONS.read_text())  # validates file parses
    result_files = sorted(EVAL_DIR.glob("results-*.jsonl"))
    if not result_files:
        print("No eval/results-*.jsonl files found.")
        return 1

    rows: list[dict] = []
    summaries: dict[str, dict[str, int]] = {}

    for rf in result_files:
        run = rf.stem.removeprefix("results-")
        counts = defaultdict(int)
        for line in rf.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            g, note = grade(r["expected"], r["answer"])
            counts[g] += 1
            rows.append({
                "run": run,
                "id": r["id"],
                "auto_grade": g,
                "tool_calls": len(r.get("tool_calls", [])),
                "note": note,
            })
        summaries[run] = dict(counts)

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run", "id", "auto_grade", "tool_calls", "note"])
        w.writeheader()
        w.writerows(rows)

    print(f"Wrote {OUT}")
    print()
    print(f"{'run':<25} {'ok':>4} {'partial':>8} {'x':>4} {'total':>6}")
    print("-" * 50)
    for run, c in summaries.items():
        ok = c.get("ok", 0)
        partial = c.get("partial", 0)
        x = c.get("x", 0)
        total = ok + partial + x
        print(f"{run:<25} {ok:>4} {partial:>8} {x:>4} {total:>6}")
    print()
    print("Heuristic — manually review and downgrade as needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
