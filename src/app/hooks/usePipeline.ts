"use client";

import { useCallback, useRef, useState } from "react";
import type {
  CandidateSupplier,
  PipelineState,
  QualityVerificationOutput,
  RankedSupplier,
  RequirementInput,
  TraceEvent,
} from "../types";

const MAX_TRACES = 12;

const INITIAL_STATE: PipelineState = {
  status: "idle",
  activeLayer: null,
  requirements: [],
  suppliers: [],
  supplierNames: {},
  verification: null,
  ranking: [],
  milestones: [],
  liveTraces: [],
  error: null,
};

export function usePipeline() {
  const [state, setState] = useState<PipelineState>(INITIAL_STATE);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback((ingredient: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ ...INITIAL_STATE, status: "running", activeLayer: "L1" });

    const isDev = process.env.NODE_ENV === "development";
    const baseUrl = isDev ? "http://127.0.0.1:8000" : "";
    const url = `${baseUrl}/api/py/run?ingredient=${encodeURIComponent(ingredient)}`;

    fetch(url, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let eventType = "";
          let eventData = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              eventData = line.slice(6);
            } else if (line === "" && eventType && eventData) {
              try {
                const data = JSON.parse(eventData);
                processEvent(eventType, data);
              } catch {
                // skip malformed
              }
              eventType = "";
              eventData = "";
            }
          }
        }

        setState((prev) => ({ ...prev, status: "done", liveTraces: [] }));
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setState((prev) => ({
          ...prev,
          status: "error",
          error: err.message,
        }));
      });
  }, []);

  function processEvent(type: string, data: Record<string, unknown>) {
    switch (type) {
      case "trace": {
        const trace = data as unknown as TraceEvent;
        setState((prev) => {
          const newLayer = trace.step as PipelineState["activeLayer"];

          if (trace.live) {
            // Live trace: rolling window, only keep last MAX_TRACES
            const newLive = [...prev.liveTraces, trace].slice(-MAX_TRACES);
            return { ...prev, activeLayer: newLayer, liveTraces: newLive };
          }
          // Milestone: keep it, and clear live traces
          return {
            ...prev,
            activeLayer: newLayer,
            milestones: [...prev.milestones, trace],
            liveTraces: [],
          };
        });
        break;
      }
      case "layer1":
        setState((prev) => ({
          ...prev,
          requirements: (data.requirements as RequirementInput[]) || [],
        }));
        break;

      case "layer2":
        setState((prev) => ({
          ...prev,
          suppliers: (data.suppliers as CandidateSupplier[]) || [],
          supplierNames: (data.names as Record<string, string>) || {},
        }));
        break;

      case "layer3":
        setState((prev) => ({
          ...prev,
          verification: (data.output as QualityVerificationOutput) || null,
        }));
        break;

      case "ranking":
        setState((prev) => ({
          ...prev,
          ranking: (data.ranked as RankedSupplier[]) || [],
        }));
        break;

      case "done":
        setState((prev) => ({ ...prev, status: "done", liveTraces: [] }));
        break;
    }
  }

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState(INITIAL_STATE);
  }, []);

  return { state, run, reset };
}
