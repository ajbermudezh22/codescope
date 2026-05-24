# codescope

Chat with a Python codebase. SCIP-precise symbol graphs + a bounded agentic retrieval loop. The UI streams every tool call the agent makes, so you can watch it reason.

> Demo GIF coming soon.

## Why this exists

Most "chat with your code" tools dump a vector-searched grab bag of file chunks into a prompt and hope. The result is plausible-sounding answers that hallucinate symbols. codescope takes the opposite bet:

- The graph is **IDE-precise** — built from a [SCIP](https://github.com/sourcegraph/scip) index (`scip-python`), so call edges are real method-dispatch references, not name matches.
- The retrieval is **a bounded agent**, not a fixed two-stage chain. The model picks among four typed tools per turn (`find_symbol`, `callers_of`, `callees_of`, `read_source`) and converges in ≤ 6 turns. Every decision is visible in the trace pane.

## Install

```bash
# 1. Python deps (Python ≥3.11 required)
pip install -e ".[dev]"

# 2. SCIP indexer (Node.js tool, Sourcegraph)
npm install -g @sourcegraph/scip-python

# 3. A model API key — defaults to OpenAI
export OPENAI_API_KEY=sk-...
```

Tested on Python 3.12 and Node 25 on macOS.

## Use

```bash
# Index any local Python repo. No LLM calls; takes ~30s on fastapi-sized projects.
codescope index /path/to/your/repo

# Re-index after changes (wipes and rebuilds)
codescope index /path/to/your/repo --force

# Launch the chat server (defaults to 127.0.0.1:8000)
codescope chat
```

Then open the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
# Open the URL printed to stdout.
```

For a production bundle, `npm run build` writes a static site to `frontend/dist/`.

## Architecture

```mermaid
flowchart LR
  subgraph Ingest["Ingest (one shot, no LLM)"]
    A[scip-python] --> B[Indexer]
    B --> C[(Kuzu graph)]
    B --> D[(LanceDB vectors)]
  end
  subgraph Serve["Serve (FastAPI)"]
    UI[Web UI] <-->|WebSocket| FAPI[FastAPI]
    FAPI --> AG[Bounded agent loop]
    AG --> T[Tools API]
    T --> C
    T --> D
  end
```

Three layers, each with one job. The agent never touches the databases directly — it only sees the four-method `Tools` API. The indexer is write-only and independent of everything else.

### What's in the graph

A single `Symbol` node type and a single `CALLS` relation. SCIP gives us the rest (kind, qualified name, signature, docstring) as node properties. Smaller schema = fewer ways the agent can get lost.

### What's in the agent loop

Four tools, hard-capped at 6 turns. The system prompt steers the model toward "start with `find_symbol`, then traverse, then `read_source` only when needed." Provider-agnostic via LiteLLM, defaults to `gpt-4o-mini`.

## Eval

20-question precision spot-check on the [fastapi](https://github.com/fastapi/fastapi) codebase (6,461 symbols, 12,655 call edges). Hand-written questions verified against the indexed graph. See [`eval/score.md`](eval/score.md) for the full per-question breakdown and [`eval/questions.yaml`](eval/questions.yaml) for the question set.

| run | model | MAX_TURNS | prompt | ✅ | partial | ✗ |
|-----|-------|-----------|--------|----|---------|----|
| v1 | gpt-4o-mini | 6 | original | 8 | 1 | 11 |
| v2 | gpt-5-nano | 10 | + verify-before-cite | 8 | 0 | 12 |

The headline didn't move between v1 and v2, but the failure mode shifted entirely. v1 produced 4 confidently-wrong nearby symbols (e.g. citing `Security` when the question was about `Depends`); v2 produced zero. The verify-before-cite rule plus gpt-5-nano's better instruction-following made the agent refuse to commit to a symbol it hadn't actually inspected. Every v2 failure (12 of 12) is a turn-budget truncation — the agent was mid-investigation, not wrong. For a real developer tool, "still investigating" is a much better failure mode than "confidently wrong."

The fix is mechanical: the careful agent needs a bigger budget. v3 will run with `MAX_TURNS=20` (one-line change) and should recover most of the truncations.

To re-run:

```bash
source .venv/bin/activate
OPENAI_API_KEY=sk-... python eval/run_codescope.py --model gpt-5-nano --out eval/results-gpt5-nano-v3.jsonl
python eval/auto_score.py
```

## Origin and attribution

Built on lessons from my Master's thesis at TU Berlin (in collaboration with Siemens). codescope is an independent reimplementation around an agentic retrieval architecture — it shares no code, schema, or naming conventions with the thesis system. The full architectural delta is in [the spec](docs/design/specs/2026-05-23-codescope-design.md#3-architectural-distance-from-thesis).

In one line: the thesis was a fixed two-stage chain (vector search → APOC graph expansion → synthesis) over a tree-sitter graph with LLM-enriched file summaries. codescope is a bounded agent loop over an SCIP graph, no enrichment phase, four typed tools, live tool trace.

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Indexer | `scip-python` | IDE-grade symbol resolution; no name-matching heuristics |
| Graph DB | Kuzu (embedded) | No server, fast, openCypher subset |
| Vector DB | LanceDB (embedded) | No server, columnar, simple Python API |
| Embeddings | `bge-small-en-v1.5` via FastEmbed | Local, CPU, 384-dim |
| LLM client | LiteLLM | Provider-agnostic; works with OpenAI, Gemini, Ollama |
| Backend | FastAPI + WebSockets | Streaming-first |
| Frontend | Vite + React + TS + Tailwind | Small bundle, fast iteration |

## Status

v1.0 — local-only, single Python repo, no incremental re-index, no hosted demo. See [the spec](docs/design/specs/2026-05-23-codescope-design.md#2-goals--non-goals) for the explicit non-goals.

## License

MIT.
