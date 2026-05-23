const BASE = "http://127.0.0.1:8000";

export type Status = {
  indexed: boolean;
  repo_name: string;
  symbol_count: number;
};

export type ToolCallEvent = {
  type: "tool_call";
  name: string;
  args: Record<string, unknown>;
  turn: number;
};
export type ToolResultEvent = {
  type: "tool_result";
  name: string;
  summary: string;
  full_result_json: string;
  turn: number;
};
export type FinalAnswerEvent = {
  type: "final_answer";
  content: string;
  truncated: boolean;
};
export type TraceEvent = ToolCallEvent | ToolResultEvent | FinalAnswerEvent;

export async function fetchStatus(): Promise<Status> {
  const r = await fetch(`${BASE}/api/status`);
  return r.json();
}

export function openChat(
  onEvent: (e: TraceEvent) => void,
  onClose: () => void,
): WebSocket {
  const ws = new WebSocket(`ws://127.0.0.1:8000/api/chat`);
  ws.onmessage = (m) => onEvent(JSON.parse(m.data));
  ws.onclose = onClose;
  return ws;
}
