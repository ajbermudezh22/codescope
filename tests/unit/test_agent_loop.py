from codescope.agent.events import ToolCallEvent, event_to_dict


def test_event_serializes_to_dict():
    ev = ToolCallEvent(name="find_symbol", args={"query": "x"}, turn=1)
    d = event_to_dict(ev)
    assert d == {"type": "tool_call", "name": "find_symbol", "args": {"query": "x"}, "turn": 1}
