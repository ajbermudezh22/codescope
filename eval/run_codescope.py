"""Run every question through codescope; dump JSONL of (question, answer, tool_calls).

Usage:
    OPENAI_API_KEY=sk-... python eval/run_codescope.py [--db .codescope-fastapi]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from codescope.agent.loop import run_agent
from codescope.store.tools import Tools


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=Path(".codescope-fastapi"))
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("eval/questions.yaml"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("eval/results-codescope.jsonl"),
    )
    parser.add_argument("--model", type=str, default="gpt-4o-mini")
    args = parser.parse_args()

    questions = yaml.safe_load(args.questions.read_text())
    tools = Tools.open(args.db)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w") as f:
        for q in questions:
            if "TODO" in str(q.get("q", "")) or "TODO" in str(q.get("expected_symbol", "")):
                print(f"[skip] {q['id']}: placeholder not filled in")
                continue

            print(f"[run]  {q['id']}: {q['q']}")
            events = list(
                run_agent(question=q["q"], tools=tools, model=args.model)
            )
            final = next(
                (e for e in events if e.type == "final_answer"), None
            )
            tool_calls = [e.name for e in events if e.type == "tool_call"]

            f.write(
                json.dumps(
                    {
                        "id": q["id"],
                        "q": q["q"],
                        "expected": q["expected_symbol"],
                        "answer": final.content if final else "",
                        "tool_calls": tool_calls,
                    }
                )
                + "\n"
            )

    print(f"\nDone. Results: {args.out}")
    print("Now score manually in eval/score.md (✅ / partial / ✗ per row).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
