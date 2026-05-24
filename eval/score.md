# Eval results: codescope on fastapi

**Benchmark:** fastapi codebase indexed with codescope (6,461 symbols, 12,655 CALLS edges)
**Questions:** 20 hand-written, all `expected_symbol`s verified to exist in the indexed graph. See [`eval/questions.yaml`](questions.yaml).

## Three runs

| run | model | MAX_TURNS | prompt | ✅ | partial | ✗ |
|-----|-------|-----------|--------|----|---------|----|
| v1 | gpt-4o-mini | 6  | original             | 8 | 1 | 11 |
| v2 | gpt-5-nano  | 10 | + verify-before-cite | 8 | 0 | 12 |
| v3 | gpt-5-nano  | 20 | + verify-before-cite | **10** | 0 | 10 |

v3 is the current best. +25% relative improvement over v1, with a categorically better failure profile (zero confidently-wrong answers).

## Failure-mode evolution

| failure mode | v1 | v2 | v3 |
|---|---|---|---|
| Confidently cited a wrong-but-nearby symbol | 4 | 0 | **0** |
| Gave up after 3-5 search attempts | 4 | 0 | **0** |
| Truncated mid-investigation | 3 | 12 | **10** |

The verify-before-cite rule + gpt-5-nano's stronger instruction-following eliminated the worst failure category (wrong-with-confidence). Bumping MAX_TURNS from 6 to 20 recovered enough budget to convert 2 of those truncations into wins. The remaining 10 truncations split into two distinct patterns described below.

## v3 remaining failures: two patterns

### Search-loop (5 questions: q02, q10, q11, q16, q20)

Agent runs 15-20 `find_symbol` calls with zero `read_source` calls. Keeps refining the query phrasing without ever verifying any candidate hit. The system prompt's "verify before cite" rule is followed too literally — the agent never picks a candidate to verify, so it never makes progress.

The fix is a prompt tweak: "if `find_symbol` returns similar hits across two consecutive queries, stop searching — pick the best candidate and `read_source` on it." Not in v3, easy to add.

### Exploration-loop (5 questions: q01, q12, q17, q18, q19)

Agent mixes `find_symbol` and `read_source` calls, genuinely exploring the graph. Runs out of turns mid-investigation. These are the genuinely hardest questions in the set (multi-hop reasoning, less obvious starting points). At 20 turns the agent is making progress but the verification chain is longer than the budget allows.

The fix is more compute — either MAX_TURNS=30+ or a stronger model.

## Per-question results

| id | difficulty | v1 (4o-mini, 6) | v2 (gpt-5-nano, 10) | v3 (gpt-5-nano, 20) |
|----|-----------|-----------------|----------------------|----------------------|
| q01 | easy   | ✗ gave up        | ✗ truncated          | ✗ exploration-loop   |
| q02 | easy   | ✗ gave up        | ✗ truncated          | ✗ search-loop        |
| q03 | easy   | ✅               | ✅                   | ✅                   |
| q04 | easy   | ✅               | ✅                   | ✅                   |
| q05 | easy   | ✅               | ✅                   | ✅                   |
| q06 | easy   | ✅               | ✅                   | ✅ (0 tool calls — priors) |
| q07 | easy   | ✗ wrong-nearby   | ✅                   | ✅                   |
| q08 | easy   | ✅               | ✅                   | ✅                   |
| q09 | medium | ✅               | ✅                   | ✅                   |
| q10 | medium | ✗ gave up        | ✗ truncated          | ✗ search-loop        |
| q11 | medium | ✗ wrong-nearby   | ✗ truncated          | ✗ search-loop        |
| q12 | medium | ✗ truncated      | ✗ truncated          | ✗ exploration-loop   |
| q13 | medium | ✗ gave up        | ✗ truncated          | ✅ **new win**       |
| q14 | medium | ✅               | ✅                   | ✅                   |
| q15 | medium | ✅               | ✗ truncated          | ✅                   |
| q16 | medium | ✗ wrong-nearby   | ✗ truncated          | ✗ search-loop        |
| q17 | hard   | ✗ truncated      | ✗ truncated          | ✗ exploration-loop   |
| q18 | hard   | partial          | ✗ truncated          | ✗ exploration-loop   |
| q19 | hard   | ✗ wrong-nearby   | ✗ truncated          | ✗ exploration-loop   |
| q20 | hard   | ✗ truncated      | ✗ truncated          | ✗ search-loop        |

## Concrete next improvements (not landed)

1. **Anti-search-loop prompt rule:** "If find_symbol returns similar hits across two consecutive queries, stop searching and read_source on the best candidate." Targets the 5 search-loop failures. One-line change.
2. **Bump MAX_TURNS further (20 → 30):** Targets the 5 exploration-loop failures. May recover 2-3.
3. **Use a stronger model (gpt-4o or claude-sonnet):** Plausibly recovers most exploration-loops and improves search efficiency. ~10x cost.

Plausible ceiling for these three combined: 15-17 / 20.

## How to re-run

```bash
source .venv/bin/activate
OPENAI_API_KEY=sk-... python eval/run_codescope.py --model gpt-5-nano --out eval/results-<version>.jsonl
python eval/auto_score.py
```
