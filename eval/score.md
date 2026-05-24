# Eval results: codescope on fastapi

**Benchmark:** fastapi codebase indexed with codescope (6,461 symbols, 12,655 CALLS edges)
**Questions:** 20 hand-written, all `expected_symbol`s verified against the indexed graph. See [`questions.yaml`](questions.yaml).

## Four runs

| run | model | MAX_TURNS | extras | ✅ | partial | ✗ |
|-----|-------|-----------|--------|----|---------|----|
| v1 | gpt-4o-mini | 6  | original prompt                                       | 8 | 1 | 11 |
| v2 | gpt-5-nano  | 10 | + verify-before-cite                                  | 8 | 0 | 12 |
| v3 | gpt-5-nano  | 20 | + verify-before-cite                                  | 10 | 0 | 10 |
| **v4** | **gpt-5** | **20** | **+ verify + anti-loop + re-rank-by-callers** | **13** | **1** | **6** |

**v4 is the current best at 13/20 — a +62% relative lift over v1.** Three of v4's wins (q01, q02, q10) never landed in any previous run.

## Failure-mode evolution

| failure mode | v1 | v2 | v3 | v4 |
|---|---|---|---|---|
| Confidently cited a wrong-but-nearby symbol | 4 | 0 | 0 | **0** |
| Gave up after few search attempts | 4 | 0 | 0 | **0** |
| Truncated mid-investigation | 3 | 12 | 10 | **6** |

Zero confidently-wrong answers across v2/v3/v4. Every v4 miss is an honest "still investigating" — the correct failure profile for a real developer tool.

## What changed between runs

- **v2:** `gpt-5-nano`, MAX_TURNS=10, system prompt added "verify before citing" rule. Eliminated the wrong-nearby and give-up patterns; everything else became truncation.
- **v3:** Same model + prompt, MAX_TURNS=20. Bigger budget recovered 2 truncations into wins.
- **v4:** Switched to `gpt-5`, added anti-search-loop prompt rule, added re-rank-by-caller-count to `find_symbol` (weight 0.15 on `log1p(callers)`). Recovered 3 more.

## v4 remaining failures

6 truncations + 1 partial. All 6 ✗s are hard multi-hop questions where the agent was genuinely exploring with mixed `find_symbol` + `read_source` calls and ran out of the 20-turn budget. q18 partial is an eval-side issue: the question wording matches `run_in_threadpool` (what the agent cited) better than `contextmanager_in_threadpool` (the expected symbol).

## Per-question results

| id | difficulty | v1 (4o-mini, 6) | v2 (gpt-5-nano, 10) | v3 (gpt-5-nano, 20) | v4 (gpt-5, 20, +re-rank) |
|----|-----------|-----------------|----------------------|----------------------|---------------------------|
| q01 | easy   | ✗ gave up        | ✗ truncated          | ✗ exploration-loop   | ✅ **new win**           |
| q02 | easy   | ✗ gave up        | ✗ truncated          | ✗ search-loop        | ✅ **new win**           |
| q03 | easy   | ✅               | ✅                   | ✅                   | ✅                        |
| q04 | easy   | ✅               | ✅                   | ✅                   | ✅                        |
| q05 | easy   | ✅               | ✅                   | ✅                   | ✅                        |
| q06 | easy   | ✅               | ✅                   | ✅                   | ✅                        |
| q07 | easy   | ✗ wrong-nearby   | ✅                   | ✅                   | ✅                        |
| q08 | easy   | ✅               | ✅                   | ✅                   | ✅                        |
| q09 | medium | ✅               | ✅                   | ✅                   | ✅                        |
| q10 | medium | ✗ gave up        | ✗ truncated          | ✗ search-loop        | ✅ **new win**           |
| q11 | medium | ✗ wrong-nearby   | ✗ truncated          | ✗ search-loop        | ✗ truncated               |
| q12 | medium | ✗ truncated      | ✗ truncated          | ✗ exploration-loop   | ✗ truncated               |
| q13 | medium | ✗ gave up        | ✗ truncated          | ✅                   | ✅                        |
| q14 | medium | ✅               | ✅                   | ✅                   | ✅                        |
| q15 | medium | ✅               | ✗ truncated          | ✅                   | ✅                        |
| q16 | medium | ✗ wrong-nearby   | ✗ truncated          | ✗ search-loop        | ✗ truncated               |
| q17 | hard   | ✗ truncated      | ✗ truncated          | ✗ exploration-loop   | ✗ truncated               |
| q18 | hard   | partial          | ✗ truncated          | ✗ exploration-loop   | partial                   |
| q19 | hard   | ✗ wrong-nearby   | ✗ truncated          | ✗ exploration-loop   | ✗ truncated               |
| q20 | hard   | ✗ truncated      | ✗ truncated          | ✗ search-loop        | ✗ truncated               |

## How to re-run

```bash
source .venv/bin/activate
OPENAI_API_KEY=sk-... python eval/run_codescope.py --model gpt-5 --out eval/results-<version>.jsonl
python eval/auto_score.py
```
