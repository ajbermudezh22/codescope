import shutil
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from codescope.agent.events import FinalAnswerEvent, ToolCallEvent, ToolResultEvent
from codescope.indexer.pipeline import index_repo
from codescope.web.app import build_app

TINY_REPO = Path(__file__).parent.parent / "fixtures" / "tiny_repo"


@pytest.fixture(scope="module")
def app(tmp_path_factory):
    if not shutil.which("scip-python"):
        pytest.skip("scip-python not installed")
    db = tmp_path_factory.mktemp("web") / ".codescope"
    index_repo(repo_path=TINY_REPO, db_dir=db)
    return build_app(db)


def test_status_endpoint(app):
    client = TestClient(app)
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["indexed"] is True
    assert body["symbol_count"] >= 3


def test_symbol_endpoint(app):
    from urllib.parse import quote

    from codescope.store.tools import Tools

    client = TestClient(app)
    db_dir = Path(app.state.db_dir)
    hits = Tools.open(db_dir).find_symbol("verify token", k=1)
    assert hits, "expected at least one hit"
    sid = hits[0].symbol_id

    r = client.get(f"/api/symbol/{quote(sid, safe='')}")
    assert r.status_code == 200
    body = r.json()
    assert body["qualified_name"] == "tiny.auth.verify_token"
    assert "def verify_token" in body["source"]


def _fake_run_agent(question, tools, model):
    yield ToolCallEvent(name="find_symbol", args={"query": "x"}, turn=1)
    yield ToolResultEvent(name="find_symbol", summary="1 hit", full_result_json="[]", turn=1)
    yield FinalAnswerEvent(content="Stubbed.", truncated=False)


def test_chat_ws_streams_events(app):
    client = TestClient(app)
    with (
        patch("codescope.web.chat_ws.run_agent", side_effect=_fake_run_agent),
        client.websocket_connect("/api/chat") as ws,
    ):
        ws.send_json({"question": "how?"})
        messages = []
        while True:
            msg = ws.receive_json()
            messages.append(msg)
            if msg["type"] == "final_answer":
                break
    types = [m["type"] for m in messages]
    assert types == ["tool_call", "tool_result", "final_answer"]
    assert messages[-1]["content"] == "Stubbed."
