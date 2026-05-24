from unittest.mock import MagicMock

from codescope.agent.events import ToolCallEvent, event_to_dict
from codescope.store.types import SymbolHit


def test_event_serializes_to_dict():
    ev = ToolCallEvent(name="find_symbol", args={"query": "x"}, turn=1)
    d = event_to_dict(ev)
    assert d == {"type": "tool_call", "name": "find_symbol", "args": {"query": "x"}, "turn": 1}


class FakeTools:
    def find_symbol(self, query, kind=None, k=5):
        return [SymbolHit(
            symbol_id="x://vt", name="verify_token",
            qualified_name="tiny.auth.verify_token",
            kind="Function", file="tiny/auth.py",
            signature="def verify_token(token: str) -> bool",
            doc_excerpt="Return True if valid.", score=0.9,
        )]
    def callers_of(self, *a, **kw): return []
    def callees_of(self, *a, **kw): return []
    def read_source(self, *a, **kw): raise NotImplementedError


def _fake_llm_two_turn():
    """First call: tool_call to find_symbol. Second call: final answer."""
    first = MagicMock()
    first.choices = [MagicMock()]
    first.choices[0].message.content = None
    tc = MagicMock(id="c1")
    tc.function.name = "find_symbol"
    tc.function.arguments = '{"query":"verify token"}'
    first.choices[0].message.tool_calls = [tc]

    second = MagicMock()
    second.choices = [MagicMock()]
    second.choices[0].message.content = "It is in `tiny.auth.verify_token`."
    second.choices[0].message.tool_calls = None
    return [first, second]


def test_agent_loop_emits_tool_call_and_final_answer(monkeypatch):
    responses = _fake_llm_two_turn()
    call_count = {"n": 0}
    def fake_completion(**kwargs):
        r = responses[call_count["n"]]
        call_count["n"] += 1
        return r
    monkeypatch.setattr("codescope.agent.loop._llm_completion", fake_completion)

    from codescope.agent.loop import run_agent
    events = list(run_agent(question="how to verify?", tools=FakeTools(), model="x"))
    types = [e.type for e in events]
    assert "tool_call" in types
    assert "tool_result" in types
    assert events[-1].type == "final_answer"
    assert "tiny.auth.verify_token" in events[-1].content
