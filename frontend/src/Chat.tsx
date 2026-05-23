import { useState } from "react";

export type ChatMessage = { role: "user" | "assistant"; content: string };

type Props = {
  messages: ChatMessage[];
  onSubmit: (question: string) => void;
  pending: boolean;
};

export function Chat({ messages, onSubmit, pending }: Props) {
  const [input, setInput] = useState("");
  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || pending) return;
    onSubmit(input);
    setInput("");
  }
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto space-y-3 pr-2">
        {messages.map((m, i) => (
          <div
            key={i}
            className={
              m.role === "user"
                ? "text-neutral-100"
                : "text-emerald-300 whitespace-pre-wrap"
            }
          >
            <span className="text-neutral-500">
              {m.role === "user" ? "you" : "asst"}:{" "}
            </span>
            {m.content}
          </div>
        ))}
        {pending && <div className="text-neutral-500 italic">thinking…</div>}
      </div>
      <form onSubmit={submit} className="mt-2 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="ask about this codebase…"
          className="flex-1 bg-neutral-900 px-3 py-2 rounded outline-none border border-neutral-800 focus:border-neutral-500"
          disabled={pending}
        />
        <button
          className="px-3 py-2 bg-emerald-700 hover:bg-emerald-600 rounded disabled:opacity-50"
          disabled={pending}
        >
          send
        </button>
      </form>
    </div>
  );
}
