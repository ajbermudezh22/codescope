# Eval results: codescope on fastapi

**Model:** gpt-4o-mini
**Date:** 2026-05-24
**Graph size:** 6,461 symbols / 12,655 CALLS edges
**MAX_TURNS:** 6

## Headline

| ✅ correct | partial | ✗ wrong | total |
|-----------|---------|---------|-------|
| 8         | 1       | 11      | 20    |

40% correct, 5% partial, 55% wrong on gpt-4o-mini with MAX_TURNS=6.

## Per-question results

| id | difficulty | grade | one-line note |
|----|-----------|-------|--------------|
| q01 | easy | ✗ | gave up; 5 find_symbol queries didn't land it |
| q02 | easy | ✗ | gave up; 3 find_symbol queries |
| q03 | easy | ✅ | clean cite of `OAuth2PasswordBearer` |
| q04 | easy | ✅ | clean cite of `HTTPException` with signature |
| q05 | easy | ✅ | clean cite of `jsonable_encoder` with signature |
| q06 | easy | ✅ | brief but correct cite of `UploadFile` |
| q07 | easy | ✗ | cited `Security` instead of `Depends` (wrong-but-nearby) |
| q08 | easy | ✅ | clean cite of `BackgroundTasks` |
| q09 | medium | ✅ | clean cite of `request_response` |
| q10 | medium | ✗ | gave up; APIRoute#get_route_handler exists |
| q11 | medium | ✗ | cited `Depends` instead of `get_dependant` |
| q12 | medium | ✗ | turn budget exhausted (truncated answer) |
| q13 | medium | ✗ | gave up; `include_router` exists |
| q14 | medium | ✅ | correctly cited + noted no callers |
| q15 | medium | ✅ | clean cite of `HTTPBearer` |
| q16 | medium | ✗ | confidently wrong: `APIRouter#trace` instead of `get_fields_from_routes` |
| q17 | hard | ✗ | turn budget exhausted |
| q18 | hard | partial | cited `run_in_threadpool` (right concept); see notes |
| q19 | hard | ✗ | `_wrap_gen_lifespan_context` instead of `_merge_lifespan_context` |
| q20 | hard | ✗ | turn budget exhausted |

## Failure patterns

Three distinct failure modes:

1. **Gave up too early (4 questions):** q01, q02, q10, q13.
   The agent runs 3–5 `find_symbol` queries with similar phrasing and quits when none directly match. Every one of these symbols exists in the graph.

2. **Confidently wrong nearby symbol (4 questions):** q07, q11, q16, q19.
   The agent picks a real symbol from the right area but not the one asked about. The system prompt instructs "do not invent symbols" but doesn't require *verifying* the symbol matches the question.

3. **Turn budget exhausted (3 questions):** q12, q17, q20.
   All hard multi-hop questions. The agent was mid-investigation when MAX_TURNS=6 hit. Truncated answer returned.

## Wins

The 8 ✅ are all clean, well-cited, traceable through the agent's tool calls. Easy questions where the docstring of the right symbol semantically matched the user's phrasing: this is exactly where the architecture is supposed to work, and it does.

## Concrete improvements (not yet applied)

These three changes would plausibly take the score from 8 to 14–16:

1. **Bump `MAX_TURNS` 6 → 10** in `src/codescope/agent/loop.py`. Recovers 3 truncated answers. One-line change.
2. **Add a "verify before citing" instruction** to `src/codescope/agent/prompt.py`. Targets the 4 nearby-wrong failures. Specifically: "Before citing a symbol as the answer, use `read_source` to confirm its body matches what the user asked. If it doesn't, search again with different phrasing."
3. **Use a stronger model** (`--model gpt-4o` or `claude-sonnet-4-5`). All 20 questions ran on `gpt-4o-mini`. Stronger models do disambiguation visibly better.

## Eval-side notes

- **q18 has a weak prompt.** The question describes `run_in_threadpool` (which wraps a callable), but the expected symbol was `contextmanager_in_threadpool` (which wraps an async context manager). The agent's `run_in_threadpool` answer is technically more aligned to the question text than the expected. Marked partial.

## How to re-run

```bash
source .venv/bin/activate
OPENAI_API_KEY=sk-... python eval/run_codescope.py
python eval/auto_score.py  # heuristic auto-score; results to eval/auto-scores.csv
# Manually downgrade any auto-✅ where the answer is technically right but explains poorly
```
