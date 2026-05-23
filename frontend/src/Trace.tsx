import { useState } from "react";
import type { TraceEvent } from "./api";

type CardData =
  | {
      kind: "tool_call";
      name: string;
      args: Record<string, unknown>;
      result?: string;
      resultRaw?: string;
    }
  | { kind: "final"; content: string; truncated: boolean };

export function eventsToCards(events: TraceEvent[]): CardData[] {
  const cards: CardData[] = [];
  for (const ev of events) {
    if (ev.type === "tool_call") {
      cards.push({ kind: "tool_call", name: ev.name, args: ev.args });
    } else if (ev.type === "tool_result") {
      for (let i = cards.length - 1; i >= 0; i--) {
        const c = cards[i];
        if (c.kind === "tool_call" && c.name === ev.name && c.result === undefined) {
          c.result = ev.summary;
          c.resultRaw = ev.full_result_json;
          break;
        }
      }
    } else if (ev.type === "final_answer") {
      cards.push({ kind: "final", content: ev.content, truncated: ev.truncated });
    }
  }
  return cards;
}

export function Trace({ events }: { events: TraceEvent[] }) {
  const cards = eventsToCards(events);
  const [expanded, setExpanded] = useState<number | null>(null);
  return (
    <div className="h-full overflow-auto space-y-2 pl-2 border-l border-neutral-800">
      {cards.map((c, i) =>
        c.kind === "tool_call" ? (
          <div
            key={i}
            className="bg-neutral-900 border border-neutral-800 rounded p-2 cursor-pointer"
            onClick={() => setExpanded(expanded === i ? null : i)}
          >
            <div>
              <span className="text-emerald-400">▸ {c.name}</span>
              <span className="text-neutral-500">
                {" "}
                (
                {Object.entries(c.args)
                  .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                  .join(", ")}
                )
              </span>
            </div>
            {c.result && (
              <div className="text-neutral-400 ml-3 mt-1">→ {c.result}</div>
            )}
            {expanded === i && c.resultRaw && (
              <pre className="text-xs text-neutral-500 mt-2 overflow-auto max-h-48 whitespace-pre-wrap">
                {c.resultRaw}
              </pre>
            )}
          </div>
        ) : (
          <div
            key={i}
            className="bg-emerald-950/40 border border-emerald-900 rounded p-2 text-emerald-200"
          >
            ✓ final answer{c.truncated ? " (truncated)" : ""}
          </div>
        ),
      )}
    </div>
  );
}
