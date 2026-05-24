# Eval results: codescope on fastapi

**Benchmark:** fastapi codebase indexed with codescope (6,461 symbols, 12,655 CALLS edges)
**Questions:** 20, hand-written and verified against the indexed graph (see `eval/questions.yaml`)

## Runs

| run | model | MAX_TURNS | prompt | ✅ | partial | ✗ |
|-----|-------|-----------|--------|----|---------|----|
| v1 | gpt-4o-mini | 6 | original | 8 | 1 | 11 |
| v2 | gpt-5-nano | 10 | + verify-before-cite | 8 | 0 | 12 |
| v3 | gpt-5-nano | 20 | + verify-before-cite | _pending_ | | |

The headline number didn't move between v1 and v2 — but the failure mode shifted entirely.

## Failure modes

| failure mode | v1 | v2 |
|---|---|---|
| Confidently cited a wrong-but-nearby symbol | 4 | **0** |
| Gave up after 3-5 search attempts | 4 | **0** |
| Truncated (turn budget exhausted) | 3 | **12** |

The verify-before-cite rule combined with gpt-5-nano's better instruction-following eliminated every "confidently wrong" answer. q07 flipped from ✗→✅ because the agent now refuses to cite `Security` without verifying it's actually what the user asked about. q15 used 5 `read_source` calls — it was doing the verification properly, just ran out of budget mid-investigation.

This is a much better failure profile for a real tool: "still investigating" is honest, "wrong answer with confidence" is actively misleading. The fix is to give the more-careful agent a bigger budget — hence v3 with MAX_TURNS=20.

## Per-question results

| id | difficulty | v1 (4o-mini, MAX=6) | v2 (gpt-5-nano, MAX=10) |
|----|-----------|---------------------|--------------------------|
| q01 | easy   | ✗ gave up           | ✗ truncated              |
| q02 | easy   | ✗ gave up           | ✗ truncated              |
| q03 | easy   | ✅                  | ✅                       |
| q04 | easy   | ✅                  | ✅                       |
| q05 | easy   | ✅                  | ✅                       |
| q06 | easy   | ✅                  | ✅                       |
| q07 | easy   | ✗ wrong-nearby      | ✅ **fixed**             |
| q08 | easy   | ✅                  | ✅                       |
| q09 | medium | ✅                  | ✅                       |
| q10 | medium | ✗ gave up           | ✗ truncated              |
| q11 | medium | ✗ wrong-nearby      | ✗ truncated              |
| q12 | medium | ✗ truncated         | ✗ truncated              |
| q13 | medium | ✗ gave up           | ✗ truncated              |
| q14 | medium | ✅                  | ✅                       |
| q15 | medium | ✅                  | ✗ truncated              |
| q16 | medium | ✗ wrong-nearby      | ✗ truncated              |
| q17 | hard   | ✗ truncated         | ✗ truncated              |
| q18 | hard   | partial             | ✗ truncated              |
| q19 | hard   | ✗ wrong-nearby      | ✗ truncated              |
| q20 | hard   | ✗ truncated         | ✗ truncated              |

q15 is the most interesting regression: v1 got it right with a single `find_symbol`. v2 with verify-before-cite spent 10 turns including 5 `read_source` calls verifying each candidate, never reached a final answer. The instruction worked too aggressively — easily fixed by MAX_TURNS=20.

## What changed between v1 and v2

- **Model:** `gpt-4o-mini` → `gpt-5-nano`
- **MAX_TURNS:** 6 → 10 (in `src/codescope/agent/loop.py`)
- **System prompt:** added "verify before citing" rule and "make 3-4 search attempts before giving up" guidance (in `src/codescope/agent/prompt.py`)

## How to re-run

```bash
source .venv/bin/activate
OPENAI_API_KEY=sk-... python eval/run_codescope.py --model gpt-5-nano --out eval/results-gpt5-nano-v3.jsonl
python eval/auto_score.py
```
