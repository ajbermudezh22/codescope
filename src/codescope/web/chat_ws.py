"""WebSocket endpoint that streams agent trace events.

The agent loop (`run_agent`) is a synchronous generator. We iterate it in the
async handler — for a single-user local dev tool that's fine, the dominant
latency is the LLM call itself. If we ever need true concurrency, wrap with
asyncio.to_thread per yielded event.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from codescope.agent.events import event_to_dict
from codescope.agent.loop import run_agent
from codescope.store.tools import Tools


def build_chat_router(db_dir: Path, model: str = "gpt-4o-mini") -> APIRouter:
    router = APIRouter()
    tools = Tools.open(db_dir)

    @router.websocket("/api/chat")
    async def chat(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                payload = await ws.receive_json()
                question = payload.get("question", "")
                if not question:
                    await ws.send_json({"type": "error", "message": "missing 'question'"})
                    continue
                for ev in run_agent(question=question, tools=tools, model=model):
                    await ws.send_json(event_to_dict(ev))
                    if ev.type == "final_answer":
                        break
        except WebSocketDisconnect:
            return

    return router
