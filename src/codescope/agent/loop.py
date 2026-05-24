"""Bounded agent loop. Yields TraceEvent values as it goes."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Iterator, Protocol

import litellm

from codescope.agent.events import (
    FinalAnswerEvent,
    ToolCallEvent,
    ToolResultEvent,
    TraceEvent,
)
from codescope.agent.prompt import SYSTEM_PROMPT
from codescope.agent.tool_schema import TOOL_SCHEMA

MAX_TURNS = 20


class ToolsProtocol(Protocol):
    def find_symbol(self, query: str, kind: str | None = None, k: int = 5): ...
    def callers_of(self, symbol_id: str, depth: int = 1): ...
    def callees_of(self, symbol_id: str, depth: int = 1): ...
    def read_source(self, symbol_id: str, with_context_lines: int = 0): ...


def _llm_completion(**kwargs):
    """Indirection so tests can monkeypatch."""
    return litellm.completion(**kwargs)


def _dispatch(tools: ToolsProtocol, name: str, args: dict[str, Any]):
    if name == "find_symbol":
        return [asdict(h) for h in tools.find_symbol(**args)]
    if name == "callers_of":
        return [asdict(c) for c in tools.callers_of(**args)]
    if name == "callees_of":
        return [asdict(c) for c in tools.callees_of(**args)]
    if name == "read_source":
        return asdict(tools.read_source(**args))
    raise ValueError(f"Unknown tool: {name}")


def _summarize(name: str, result) -> str:
    if name in {"find_symbol", "callers_of", "callees_of"}:
        n = len(result)
        if n == 0:
            return "no results"
        if name == "find_symbol":
            top = result[0]
            return f"{n} hits, top: {top['qualified_name']}"
        return f"{n} results"
    if name == "read_source":
        lines = result["source"].count("\n") + 1
        return f"{lines} lines from {result['file']}"
    return ""


def run_agent(
    question: str,
    tools: ToolsProtocol,
    model: str = "gpt-4o-mini",
) -> Iterator[TraceEvent]:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    final_message_content = ""

    for turn in range(1, MAX_TURNS + 1):
        resp = _llm_completion(model=model, messages=messages, tools=TOOL_SCHEMA)
        msg = resp.choices[0].message
        final_message_content = msg.content or ""

        if msg.tool_calls:
            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                yield ToolCallEvent(name=tc.function.name, args=args, turn=turn)
                try:
                    result = _dispatch(tools, tc.function.name, args)
                    summary = _summarize(tc.function.name, result)
                except Exception as e:
                    result = {"error": str(e)}
                    summary = f"error: {e}"
                yield ToolResultEvent(
                    name=tc.function.name,
                    summary=summary,
                    full_result_json=json.dumps(result, default=str)[:50_000],
                    turn=turn,
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str)[:50_000],
                })
            continue

        yield FinalAnswerEvent(content=final_message_content, truncated=False)
        return

    yield FinalAnswerEvent(
        content=final_message_content + "\n\n(truncated: turn budget exhausted)",
        truncated=True,
    )
