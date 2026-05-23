"""Trace events streamed from the agent loop to the UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ToolCallEvent:
    type: Literal["tool_call"] = "tool_call"
    name: str = ""
    args: dict[str, Any] = field(default_factory=dict)
    turn: int = 0


@dataclass(frozen=True)
class ToolResultEvent:
    type: Literal["tool_result"] = "tool_result"
    name: str = ""
    summary: str = ""
    full_result_json: str = ""
    turn: int = 0


@dataclass(frozen=True)
class FinalAnswerEvent:
    type: Literal["final_answer"] = "final_answer"
    content: str = ""
    truncated: bool = False


TraceEvent = ToolCallEvent | ToolResultEvent | FinalAnswerEvent


def event_to_dict(ev: TraceEvent) -> dict[str, Any]:
    return asdict(ev)
