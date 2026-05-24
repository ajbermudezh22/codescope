# codescope — design spec

**Status:** Draft v1, awaiting author review
**Date:** 2026-05-23
**Author:** Alberto Bermudez Hernandez
**Working name:** `codescope` (descriptive, neutral; can be renamed before public release)

---

## 1. Context

This project is a clean-room reimplementation of the core idea from my master's
thesis at TU Berlin (work conducted in collaboration with Siemens): a system
that lets users chat with a software repository in natural language, backed
by a structural code graph plus retrieval.

The thesis system (v2.1_async) is a fixed two-stage pipeline:

```
question  →  vector search over LLM-generated File summaries
          →  Neo4j graph expansion (APOC subgraphAll, depth 2)
          →  single-shot LLM synthesis
```

The pipeline uses tree-sitter parsing for Py/C/C++, fragile static
name-matching for `CALLS`, LLM-enriched file summaries as the embedded text,
LangChain orchestration, Neo4j for the graph, FAISS for vectors, and
Streamlit for the UI.

That code is in the hands of Siemens and the university. To publish a
showcase version of this work cleanly, this project must be visibly
distinct from the thesis system at every architectural layer — not a
re-skin. The differentiation is concentrated on the **retrieval** and
**graph precision** axes, which is where the thesis's main contribution
lived.

## 2. Goals & non-goals

### Goals

- Ship a public, OSS, portfolio-grade repository in 2–3 weekends.
- Demonstrate a visibly different retrieval architecture from the thesis:
  **agentic tool-use loop** instead of a fixed two-stage chain.
- Demonstrate a precise code graph (SCIP-indexer-resolved symbols and
  references) instead of fragile tree-sitter + name-matching.
- Provide a live agent-trace UI that makes the architecture self-explanatory
  in a 60-second demo.
- Be attribution-clean: a single sentence in the README acknowledging the
  thesis as inspiration, with no shared code, schema names, or naming
  conventions.

### Non-goals (v1.0)

- Multi-language support. **Python only.**
- Incremental re-indexing on file edits.
- Hosted multi-user demo.
- Persisted chat history across sessions.
- Graph visualization UI.
- Community-summary clustering (Microsoft-GraphRAG-style).
- Test↔code linkage.
- Local-LLM-as-default. Default is `gpt-4o-mini` via LiteLLM; local LLMs
  documented but not the headline.

These belong in a future v1.1 ideas file, not the launch.

## 3. Architectural distance from thesis

A side-by-side intended to make the IP story unambiguous:

| Layer | Thesis (v2.1_async) | codescope v1.0 |
|---|---|---|
| Languages | Python + C + C++ | Python only |
| Parser | tree-sitter, custom S-expression queries | `scip-python` (Sourcegraph SCIP indexer) |
| Symbol resolution | static name matching | IDE-precise via SCIP monikers |
| Graph DB | Neo4j (server) | Kuzu (embedded, file-backed) |
| Graph schema | 5 node types (File / Class / Function / Struct / Namespace) + 4 relations (`DEFINES / IMPORTS / INCLUDES / CALLS`), mixed precision | 1 node type (`Symbol`, `kind` is a property) + 1 relation (`CALLS`), fully SCIP-precise. Containment encoded in the SCIP moniker. |
| Embedding text | LLM-generated File summary (requires "enrich" phase) | Symbol's own docstring + signature (no LLM needed at index time) |
| Vector store | FAISS (persisted to disk) | LanceDB (embedded, columnar) |
| Embedding model | OpenAI `text-embedding-3-small` | `bge-small-en-v1.5` via FastEmbed (local) |
| Orchestration | LangChain `RunnableLambda` chain | LiteLLM + a 50-line hand-rolled agent loop |
| Retrieval shape | Fixed two-stage: vector → graph expand → synthesize | **Bounded agent loop:** model picks among 4 tools, up to 6 turns |
| Build phase | `build` (parse) + `enrich` (LLM summaries, resumable, days for large repos) | Single `index` command, no LLM calls, minutes |
| UI | Streamlit | FastAPI + React, with **live agent-trace pane** as the demo centerpiece |
| Demo story | "scales to TensorFlow via resumable enrichment" | "watch the agent reason about your code" |

Every row is intentionally different. There is no shared code.

## 4. Architecture

Four units, two phases (ingest, then serve). The agent only ever reaches
storage through a typed Tools API.

```
┌──────────────────────────────────────────────────────────┐
│  INGEST (one-shot CLI: `codescope index <repo>`)         │
│                                                          │
│  scip-python ──► SCIP file ──► Indexer ──► Kuzu (graph)  │
│                                       └──► LanceDB (vec) │
└──────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────┐
│  SERVE (FastAPI: `codescope chat`)                       │
│                                                          │
│  ┌──────────────┐    JSON over WS    ┌────────────────┐  │
│  │  Web UI      │ ◄──────────────► │  FastAPI       │  │
│  │ (chat +      │                  │  + Agent loop  │  │
│  │  live trace) │                  └──────┬─────────┘  │
│  └──────────────┘                         │             │
│                                           ▼             │
│                                  ┌────────────────┐     │
│                                  │  Tools layer   │     │
│                                  │  (4 functions) │     │
│                                  └──────┬─────────┘     │
│                                         │               │
│                              ┌──────────┴──────────┐    │
│                              ▼                     ▼    │
│                          Kuzu                  LanceDB  │
└──────────────────────────────────────────────────────────┘
```

### 4.1 Units

| Unit | Purpose | Depends on | Touches LLMs? |
|---|---|---|---|
| `indexer/` | Parse repo → write Kuzu + LanceDB | `scip-python`, `kuzu`, `lancedb`, `fastembed` | No |
| `store/` | Kuzu + LanceDB schema; expose typed Tools API | `kuzu`, `lancedb` | No |
| `agent/` | LLM loop; tool dispatch; turn cap | `store/`, `litellm` | Yes |
| `web/` | FastAPI server, React SPA, WebSocket | `agent/` | No (delegates) |

**Layering invariant:** `web` → `agent` → `store` → DBs. `indexer` is
independent and write-only. Skipping layers (e.g., `web` calling Kuzu
directly) is a code review red flag.

## 5. Ingest pipeline

### 5.1 Command

```bash
codescope index <repo_path> [--db .codescope/] [--force]
```

Idempotent: `--force` blows away the existing DB and rebuilds; default
errors if a DB already exists for that repo.

### 5.2 Stages

```
repo_path
   │
   ▼
[1] Run `scip-python index . --output index.scip`
   │    (single subprocess call; depends on scip-python being on PATH)
   ▼
[2] Parse index.scip (protobuf)
   │    → stream of (symbol_moniker, kind, range, doc, refs)
   ▼
   ├──► [3a] Kuzu writer  (batched ~1000 inserts)
   │       writes Symbol nodes + CALLS / DEFINED_IN / IMPORTS edges
   │
   └──► [3b] LanceDB writer
           writes embeddings only for symbols where doc is non-empty
```

No LLM calls. No async enrichment. Re-running is deterministic.

### 5.3 Kuzu schema

```cypher
CREATE NODE TABLE Symbol(
  id            STRING,    -- SCIP moniker, e.g. "scip-python python . mypkg/auth.py/verify_token()."
  name          STRING,    -- short display name
  qualified_name STRING,   -- e.g. "mypkg.auth.verify_token" (used for citations)
  kind          STRING,    -- 'Function' | 'Class' | 'Method' | 'Module' | 'Variable'
  file          STRING,
  start_line    INT64,
  end_line      INT64,
  doc           STRING,
  signature     STRING,
  PRIMARY KEY (id)
);

CREATE REL TABLE CALLS (FROM Symbol TO Symbol);
```

**One relation in v1.0.** `CALLS` is SCIP-precise and is the only one the
4 Tools actually query (via `callers_of` / `callees_of`). Containment
(class→method, module→function) is encoded in the SCIP moniker `id` itself
and surfaced via the `qualified_name` property — no separate relation
needed. `IMPORTS` and any other relation move to v1.1 if and when a tool
exists that uses them. Schema discipline: write nothing the read path
doesn't consume.

### 5.4 LanceDB collection

```
Table: symbols
  symbol_id   STRING   -- foreign key into Kuzu Symbol.id
  text        STRING   -- "name + signature + doc[:500]"
  vector      FLOAT[384]  -- bge-small-en-v1.5
```

Only documented symbols are embedded. Undocumented internals are still
reachable via graph hops from documented entry points — that's the whole
point of having a precise graph.

### 5.5 Failure modes

| Failure | Behavior |
|---|---|
| `scip-python` not on PATH | Print exact install command; exit 1. |
| Repo doesn't type-check | SCIP still emits partial index. Log skipped files to `.codescope/index.log`; continue. |
| DB already exists, no `--force` | Print path + suggestion; exit 1. |
| Out of memory on huge repos | Out of scope for v1.0; document the limit in README. |

## 6. Storage layer & Tools API

The contract between agent and storage. The agent **only** sees these four
functions. This is also the public API for anyone embedding `codescope` as
a library.

```python
class Tools:
    def __init__(self, kuzu_db, lance_db): ...

    def find_symbol(
        self,
        query: str,
        kind: str | None = None,
        k: int = 5,
    ) -> list[SymbolHit]:
        """Semantic search over documented symbols.

        Returns: [{symbol_id, name, kind, file, signature, doc_excerpt, score}]
        Use this FIRST to find entry points by intent.
        """

    def callers_of(
        self,
        symbol_id: str,
        depth: int = 1,
    ) -> list[CallSite]:
        """Reverse walk of CALLS. depth=2 returns callers-of-callers."""

    def callees_of(
        self,
        symbol_id: str,
        depth: int = 1,
    ) -> list[CallSite]:
        """Forward walk of CALLS."""

    def read_source(
        self,
        symbol_id: str,
        with_context_lines: int = 0,
    ) -> SourceSlice:
        """Full source for the symbol's range, optionally padded."""
```

Types are plain dataclasses. No tools beyond these four in v1.0. Tool
proliferation is the #1 risk for an agent loop — every extra tool is a
choice the model can get wrong.

## 7. Agent loop

```
def run(question: str) -> AsyncIterator[TraceEvent]:
    messages = [system_msg(), user_msg(question)]
    for turn in range(MAX_TURNS):  # MAX_TURNS = 6
        resp = llm.chat(messages, tools=TOOL_SCHEMA)
        if resp.tool_calls:
            for call in resp.tool_calls:
                yield TraceEvent(type="tool_call", name=call.name, args=call.args)
                result = tools.dispatch(call)
                messages.append(tool_result_msg(call, result))
                yield TraceEvent(type="tool_result", name=call.name, summary=summarize(result))
            continue
        yield TraceEvent(type="final_answer", content=resp.content)
        return
    yield TraceEvent(type="final_answer", content=resp.content + "\n\n(truncated: turn budget exhausted)")
```

### 7.1 System prompt (draft, will iterate during weekend 3)

> You are a code-understanding assistant for a Python repository. You have
> four tools: `find_symbol`, `callers_of`, `callees_of`, `read_source`.
>
> Strategy: start with `find_symbol` to locate relevant entry points, then
> use the graph tools to understand structure, then `read_source` only when
> you need exact code. Prefer a few precise tool calls over many broad ones.
> When you have enough context to answer, stop calling tools and respond
> directly.
>
> Cite symbols by their qualified name (e.g., `mypkg.auth.verify_token`).

### 7.2 LLM provider

LiteLLM client. Default model: `gpt-4o-mini`. CLI flag `--model` accepts
any LiteLLM model string (`gemini/gemini-2.0-flash`, `ollama/llama3.1`, etc.).
Provider keys read from env vars per LiteLLM convention.

## 8. UI

### 8.1 Stack

- **Backend:** FastAPI, uvicorn, WebSocket for streaming.
- **Frontend:** React (Vite, TypeScript). Single page. Tailwind for styling.

Explicitly *not* Streamlit — too visually thesis-shaped, and the streaming
trace needs a layout Streamlit fights.

### 8.2 Layout

```
┌────────────────────────────────────────────────────────────────┐
│  codescope — chat with <repo_name>                  [● indexed]│
├──────────────────────────────┬─────────────────────────────────┤
│   CHAT (left, 55%)           │   AGENT TRACE (right, 45%)      │
│                              │                                 │
│   user: how is auth done?    │   ▸ find_symbol("auth")         │
│                              │     → 5 hits, top:              │
│   assistant: The auth flow…  │       mypkg.auth.verify_token   │
│                              │                                 │
│                              │   ▸ callers_of(verify_token)    │
│                              │     → 3 callers                 │
│                              │                                 │
│                              │   ▸ read_source(verify_token)   │
│                              │     → 42 lines                  │
│                              │                                 │
│                              │   ✓ final answer (4 tool calls) │
├──────────────────────────────┴─────────────────────────────────┤
│  [type a question…]                                       [↵]  │
└────────────────────────────────────────────────────────────────┘
```

### 8.3 Interactions

- Trace cards mount as their events arrive on the WebSocket.
- Click a trace card → expands to full args + full result JSON.
- Click a symbol name anywhere → side drawer that calls `/api/symbol/{id}`
  directly (does not spawn a new agent turn). Cut-if-time-runs-short.
- Bottom-right counter: tool-call count, total latency, cumulative tokens.

### 8.4 API surface

```
GET  /api/status              -> {indexed, repo_name, symbol_count}
WS   /api/chat                -> client sends {question}; server streams TraceEvent[]
GET  /api/symbol/{id}         -> SymbolHit (for click-to-expand)
```

Three endpoints. No others in v1.0.

## 9. Evaluation

Cheap on purpose. Two artifacts:

1. **20-question precision spot-check on `fastapi`.** Hand-written questions
   with known-good answers. Run V3 *and* the thesis's v2.1 on the same repo.
   Score each as ✅ / partial / ✗. Publish the table in the README.
2. **Trace inspection on 5 questions.** Hand-verify that the SCIP graph hops
   are correct (not just plausible). Demonstrates the precision claim.

Out of scope for v1.0: RAGAS, LLM-as-judge, automated benchmark suites.
Those are research-paper artifacts; this is a portfolio repo.

## 10. Timeline

```
Weekend 1 — INGEST + STORE                     (~10–14h)
  Sat AM   scaffold repo, CI, ruff/pytest, README skeleton
  Sat PM   indexer: scip-python → Kuzu writer (Symbol + 3 rels)
  Sun AM   LanceDB writer, bge-small embeddings of documented symbols
  Sun PM   Tools class with the 4 methods, unit tests against fastapi
           ✓ Milestone: `codescope index ./fastapi` works, Tools return real results

Weekend 2 — AGENT + WEB                        (~10–14h)
  Sat AM   LiteLLM agent loop, tool dispatch, MAX_TURNS, system prompt
  Sat PM   FastAPI: /status, /chat (WS), /symbol/{id}
  Sun AM   React frontend: chat + trace pane, WS wiring, card streaming
  Sun PM   Click-to-expand cards, latency/token counter, basic styling
           ✓ Milestone: ask a question end-to-end, watch trace stream

Weekend 3 — POLISH + EVAL + DEMO               (~8–12h)
  Sat AM   Eval: 20-question spot-check on fastapi (V3 vs. v2.1)
  Sat PM   Bug bash from eval findings, prompt tuning
  Sun AM   README, demo GIF, eval table, architecture diagram
  Sun PM   Tag v1.0, push public, write a 500-word blog post
           ✓ Milestone: shipped
```

**Built-in slack:** Weekend 1 typically spills into Weekend 2. If so,
Weekend 3 absorbs: eval shrinks to 10 questions, blog post moves to
"later this week." The two non-negotiables: working end-to-end demo, and
the live trace pane.

## 11. Risks

| Risk | Mitigation |
|---|---|
| `scip-python` install pain | Pin a version, test install path on a clean venv on day 1, document in README. |
| Agent loops on simple questions | Tune prompt; add "you already have enough context" hint when the model re-queries the same symbol twice. |
| Tool-calling reliability on small/local models | Ship `gpt-4o-mini` as default; document local-LLM as best-effort. |
| Project looks like a thesis re-skin | Section 3 table is the diff. README leads with the agent-trace demo, not the graph. |
| Scope creep into v1.1 ideas | Re-read this spec at the start of each weekend; resist. |

## 12. IP & attribution

- Repository is published under MIT.
- README contains exactly one attribution sentence:
  > Built on lessons from my master's thesis at TU Berlin in collaboration
  > with Siemens; this is an independent reimplementation around an agentic
  > retrieval architecture, sharing no code, schema, or naming conventions
  > with the original system.
- No file, schema name, function name, or doc lifted from the thesis. The
  table in §3 is the audit trail.
- No proprietary Siemens datasets, benchmarks, or internal links referenced.
  All evaluation runs against public OSS repos (`fastapi`).

## 13. Open questions for author review

1. Is `codescope` the right project name, or do you want something else
   before the spec hits git history?
2. Public on day 1, or build privately and flip to public when v1.0 ships?
   (Affects whether to enable issues/discussions immediately.)
3. Comfortable with the explicit thesis attribution sentence in §12, or
   prefer a softer phrasing?
