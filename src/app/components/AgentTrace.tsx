"use client";

import { useEffect, useRef } from "react";
import type { TraceEvent } from "../types";

const layerColor: Record<string, string> = {
  L1: "text-blue-700",
  L2: "text-purple-700",
  L3: "text-green-700",
  RANK: "text-[#1B263B]",
};

const layerBg: Record<string, string> = {
  L1: "bg-blue-50",
  L2: "bg-purple-50",
  L3: "bg-green-50",
  RANK: "bg-slate-100",
};

function TraceMessage({ trace }: { trace: TraceEvent }) {
  const { msg, links, live } = trace;

  if (links && links.length > 0) {
    let parts: (string | { url: string })[] = [msg];
    for (const url of links) {
      const newParts: (string | { url: string })[] = [];
      for (const part of parts) {
        if (typeof part !== "string") {
          newParts.push(part);
          continue;
        }
        const idx = part.indexOf(url);
        if (idx === -1) {
          newParts.push(part);
          continue;
        }
        if (idx > 0) newParts.push(part.slice(0, idx));
        newParts.push({ url });
        if (idx + url.length < part.length) newParts.push(part.slice(idx + url.length));
      }
      parts = newParts;
    }

    return (
      <span className="break-words min-w-0">
        {parts.map((p, i) =>
          typeof p === "string" ? (
            <span key={i} className={live ? "text-foreground/50" : "text-foreground/80"}>
              {p}
            </span>
          ) : (
            <a
              key={i}
              href={p.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:underline break-all"
            >
              {p.url.length > 50 ? p.url.slice(0, 50) + "\u2026" : p.url}
            </a>
          )
        )}
      </span>
    );
  }

  return (
    <span className={`break-words min-w-0 ${live ? "text-foreground/50" : "text-foreground/80"}`}>
      {msg}
    </span>
  );
}

function TraceLine({ trace }: { trace: TraceEvent }) {
  return (
    <div
      className={`flex gap-1.5 text-[11px] py-0.5 px-1.5 rounded ${
        trace.live ? "" : layerBg[trace.step] || ""
      }`}
    >
      <span className="text-muted-foreground/50 flex-shrink-0 font-mono text-[10px]">
        {trace.ts}
      </span>
      <span
        className={`font-bold flex-shrink-0 text-[10px] ${
          layerColor[trace.step] || "text-foreground"
        }`}
      >
        {trace.step}
      </span>
      <TraceMessage trace={trace} />
    </div>
  );
}

export function AgentTrace({
  milestones,
  liveTraces,
  isRunning,
  collapsed,
  onToggle,
}: {
  milestones: TraceEvent[];
  liveTraces: TraceEvent[];
  isRunning: boolean;
  collapsed: boolean;
  onToggle: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const total = milestones.length + liveTraces.length;

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [milestones.length, liveTraces.length]);

  if (collapsed) {
    return (
      <button
        onClick={onToggle}
        className="fixed right-0 top-1/2 -translate-y-1/2 z-20 bg-white border border-[#E2E4E9] rounded-l-lg px-2 py-4 text-xs text-muted-foreground hover:text-foreground transition-colors shadow-sm"
        style={{ writingMode: "vertical-rl" }}
      >
        Live Trace {total > 0 && `(${total})`}
      </button>
    );
  }

  return (
    <div
      className="w-80 border-l border-[#E2E4E9] bg-white flex-shrink-0 flex flex-col"
      style={{ height: "calc(100vh - 72px)" }}
    >
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#E2E4E9] flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Live Trace
          </span>
          {isRunning && (
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          )}
        </div>
        <button
          onClick={onToggle}
          className="text-muted-foreground hover:text-foreground text-xs"
        >
          {"\u25B6"}
        </button>
      </div>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-2"
        style={{ minHeight: 0 }}
      >
        {total === 0 && (
          <div className="text-xs text-muted-foreground text-center py-8">
            Run the pipeline to see live traces
          </div>
        )}

        {/* Persistent milestones */}
        {milestones.map((t, i) => (
          <TraceLine key={`m-${i}`} trace={t} />
        ))}

        {/* Live traces — rolling window */}
        {liveTraces.length > 0 && milestones.length > 0 && (
          <div className="border-t border-dashed border-[#E2E4E9] my-1" />
        )}
        {liveTraces.map((t, i) => (
          <TraceLine key={`l-${i}`} trace={t} />
        ))}
      </div>
    </div>
  );
}
