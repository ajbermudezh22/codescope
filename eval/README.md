# Eval

A 20-question precision spot-check on a public Python repo (`fastapi` by default).

## Setup (one-time, ~5 min)

```bash
# From the repo root, clone the target benchmark repo
mkdir -p eval/repos
git clone --depth=1 https://github.com/tiangolo/fastapi eval/repos/fastapi

# Index it (no LLM calls, ~30s)
codescope index eval/repos/fastapi --db .codescope-fastapi --force

# Review and fill in the questions
$EDITOR eval/questions.yaml
```

Every entry in `questions.yaml` has a `q:` and an `expected_symbol:` (the qualified
name of the symbol that should appear in a correct answer). The starter set has
20 placeholders — replace each `TODO: ...` with a real question about fastapi
and the expected symbol.

## Run

```bash
export OPENAI_API_KEY=sk-...
python eval/run_codescope.py
```

Writes `eval/results-codescope.jsonl`. Score manually by copying the answers
into `eval/score.md` and marking each as ✅ / partial / ✗.

## Compare to thesis baseline (optional)

The thesis v2.1_async chain can be run against the same questions for a
side-by-side. That setup is documented separately — see the parent thesis
repo at `/Users/alberto/projects/Personal Projects/master_thesis/`.
