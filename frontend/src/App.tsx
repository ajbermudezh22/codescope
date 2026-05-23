import { useEffect, useRef, useState } from "react";
import { Chat } from "./Chat";
import type { ChatMessage } from "./Chat";
import { Trace } from "./Trace";
import type { Status, TraceEvent } from "./api";
import { fetchStatus, openChat } from "./api";

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [pending, setPending] = useState(false);
  const [elapsedMs, setElapsedMs] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetchStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  function onSubmit(question: string) {
    const start = Date.now();
    setMessages((m) => [...m, { role: "user", content: question }]);
    setEvents([]);
    setElapsedMs(0);
    setPending(true);
    const ws = openChat(
      (ev: TraceEvent) => {
        setEvents((es) => [...es, ev]);
        if (ev.type === "final_answer") {
          setMessages((m) => [
            ...m,
            { role: "assistant", content: ev.content },
          ]);
          setElapsedMs(Date.now() - start);
          setPending(false);
          ws.close();
        }
      },
      () => setPending(false),
    );
    wsRef.current = ws;
    ws.onopen = () => ws.send(JSON.stringify({ question }));
  }

  return (
    <div className="h-screen flex flex-col">
      <header className="px-4 py-2 border-b border-neutral-800 flex justify-between">
        <span>codescope — {status?.repo_name ?? "—"}</span>
        <span className="text-xs text-neutral-400">
          {status?.indexed
            ? `● ${status.symbol_count} symbols`
            : "● not indexed"}
        </span>
      </header>
      <main className="flex-1 grid grid-cols-[55%_45%] gap-4 p-4 overflow-hidden">
        <Chat messages={messages} onSubmit={onSubmit} pending={pending} />
        <Trace events={events} />
      </main>
      <footer className="px-4 py-1 border-t border-neutral-800 text-xs text-neutral-500 flex justify-end gap-4">
        <span>tool calls: {events.filter((e) => e.type === "tool_call").length}</span>
        <span>{elapsedMs > 0 ? `${(elapsedMs / 1000).toFixed(1)}s` : "—"}</span>
      </footer>
    </div>
  );
}
