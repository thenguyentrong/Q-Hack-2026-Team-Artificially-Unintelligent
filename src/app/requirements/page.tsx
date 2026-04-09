"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

type Req = {
  requirement_id?: string;
  field_name?: string;
  rule_type?: string;
  value?: unknown;
  unit?: string;
  operator?: string;
  priority?: string;
  source?: string;
  notes?: string;
};

type Status = "idle" | "loading" | "done" | "error";

const PRIORITY_MAP: Record<string, string> = {
  must: "bg-on-error-container/10 text-on-error-container",
  should: "bg-secondary-container text-on-secondary-container",
  may: "bg-primary-container/30 text-on-primary-container",
};

export default function RequirementsPage() {
  const router = useRouter();
  const [ingredient, setIngredient] = useState("Whey Protein Isolate");
  const [status, setStatus] = useState<Status>("idle");
  const [reqs, setReqs] = useState<Req[]>([]);
  const [confirmed, setConfirmed] = useState<Set<string>>(new Set());
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>("");
  const [toastMsg, setToastMsg] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem("agnes_ingredient");
    if (stored) setIngredient(stored);

    // Auto-run if we have an ingredient
    if (stored) runLayer1(stored);
  }, []);

  const runLayer1 = async (ing?: string) => {
    setStatus("loading");
    setReqs([]);
    setError("");

    try {
      const storedData = localStorage.getItem("agnes_preprocessed_data");
      if (!storedData) {
        throw new Error("No preprocessed data found. Please start from the Selection page.");
      }

      const payload = JSON.parse(storedData);

      const res = await fetch(`/api/py/layer1`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const text = await res.text();
      const data = JSON.parse(text);

      if (data.error) {
        setError(data.detail || data.error);
        setStatus("error");
        return;
      }

      const requirements: Req[] = data.requirements || [];
      setReqs(requirements);
      localStorage.setItem("agnes_layer1", JSON.stringify(data));
      setStatus("done");
    } catch (e: any) {
      setError(e.message);
      setStatus("error");
    }
  };

  const toggleConfirm = (id: string) => {
    setConfirmed((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs font-medium text-outline-variant mb-6">
        <span>PROJECTS</span>
        <span className="material-symbols-outlined text-[14px]">chevron_right</span>
        <span>WPI ANALYSIS 2024</span>
        <span className="material-symbols-outlined text-[14px]">chevron_right</span>
        <span className="text-primary font-bold">STEP 2: REQUIREMENTS &amp; CONSTRAINTS</span>
      </div>

      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed bottom-4 right-4 bg-tertiary-container text-on-tertiary-container px-6 py-3 rounded-lg shadow-2xl border border-tertiary/20 font-bold text-sm z-50 flex items-center gap-2">
          <span className="material-symbols-outlined text-tertiary fill-icon">check_circle</span>
          {toastMsg}
        </div>
      )}

      {/* Header */}
      <div className="flex justify-between items-end mb-10">
        <div>
          <h1 className="text-4xl font-extrabold text-on-surface tracking-tight leading-tight">
            Constraint Analysis
          </h1>
          <p className="text-on-surface-variant mt-1 text-sm">
            AI-powered extraction of quality requirements for{" "}
            <strong className="text-primary">{ingredient}</strong>
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => runLayer1()}
            disabled={status === "loading"}
            className="flex items-center gap-2 px-5 py-2.5 border border-outline-variant/30 rounded-lg text-sm font-bold text-on-surface hover:bg-surface-container transition-all disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-lg">sync</span>
            {status === "loading" ? "Analyzing..." : "Re-run Analysis"}
          </button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <span className="text-[0.65rem] font-bold uppercase tracking-widest text-outline">Total Constraints</span>
            {status === "done" && <span className="text-xs font-bold text-tertiary">Live AI</span>}
          </div>
          <div className="text-5xl font-extrabold text-on-surface mb-1">
            {status === "loading" ? (
              <div className="animate-pulse bg-surface-container h-12 w-16 rounded" />
            ) : (
              reqs.length || "—"
            )}
          </div>
          {status === "done" && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-on-tertiary-container bg-tertiary-container px-2 py-0.5 rounded-full font-bold">
                {reqs.filter((r) => r.priority === "must").length} Hard
              </span>
              <span className="text-on-primary-container bg-primary-container px-2 py-0.5 rounded-full font-bold">
                {reqs.filter((r) => r.priority !== "must").length} Soft
              </span>
            </div>
          )}
        </div>
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm">
          <div className="text-[0.65rem] font-bold uppercase tracking-widest text-outline mb-4">Confirmed</div>
          <div className="text-5xl font-extrabold text-on-surface mb-1">{confirmed.size}</div>
          <div className="text-xs text-on-surface-variant">of {reqs.length} total requirements</div>
        </div>
        <div className="bg-surface-container-lowest p-6 rounded-xl shadow-sm">
          <div className="text-[0.65rem] font-bold uppercase tracking-widest text-outline mb-4">Step Progress</div>
          <div className="text-5xl font-extrabold text-on-surface mb-1">
            {reqs.length ? Math.round((confirmed.size / reqs.length) * 100) : 0}%
          </div>
          <div className="w-full bg-surface-container h-2 rounded-full mt-2 overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all"
              style={{ width: `${reqs.length ? (confirmed.size / reqs.length) * 100 : 0}%` }}
            />
          </div>
        </div>
      </div>

      {/* Constraint Catalog */}
      <div className="bg-surface-container-lowest rounded-xl shadow-sm overflow-hidden">
        <div className="px-8 py-6 border-b border-surface-container-low flex justify-between items-center">
          <h2 className="text-xl font-bold text-on-surface">Constraint Catalog</h2>
          {status === "loading" && (
            <div className="flex items-center gap-2 text-sm text-primary">
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              AI agent is running Layer 1...
            </div>
          )}
        </div>

        <div className="divide-y divide-surface-container-low">
          {status === "loading" && (
            [...Array(3)].map((_, i) => (
              <div key={i} className="px-8 py-6 animate-pulse flex items-start gap-4">
                <div className="w-10 h-10 bg-surface-container rounded" />
                <div className="flex-1">
                  <div className="h-4 bg-surface-container rounded w-48 mb-2" />
                  <div className="h-3 bg-surface-container rounded w-72" />
                </div>
              </div>
            ))
          )}

          {status === "error" && (
            <div className="px-8 py-10 text-center">
              <span className="material-symbols-outlined text-error text-4xl mb-3 fill-icon block">error_outline</span>
              <p className="text-sm font-bold text-on-surface mb-1">Layer 1 Agent Error</p>
              <p className="text-xs text-on-surface-variant">{error}</p>
              <button
                onClick={() => runLayer1()}
                className="mt-4 px-5 py-2 primary-gradient text-on-primary rounded-lg text-sm font-bold"
              >
                Retry
              </button>
            </div>
          )}

          {status === "done" && reqs.length === 0 && (
            <div className="px-8 py-10 text-center text-on-surface-variant text-sm">
              No requirements extracted. Try re-running the analysis.
            </div>
          )}

          {reqs.map((req, i) => {
            const id = req.requirement_id || String(i);
            const isConfirmed = confirmed.has(id);
            const isMust = req.priority === "must";
            const priorityClass = PRIORITY_MAP[req.priority || "may"] || PRIORITY_MAP.may;

            return (
              <div
                key={id}
                className="px-8 py-5 hover:bg-surface-container-low/10 flex items-center justify-between transition-colors"
              >
                <div className="flex items-start gap-4">
                  <div
                    className={`w-10 h-10 rounded flex items-center justify-center mt-1 ${
                      isMust ? "bg-error-container/20" : "bg-primary-container/20"
                    }`}
                  >
                    <span
                      className={`material-symbols-outlined ${isMust ? "text-error" : "text-primary"} fill-icon`}
                    >
                      {isMust ? "priority_high" : "workspace_premium"}
                    </span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h4 className="font-bold text-on-surface">{req.field_name || `Requirement ${i + 1}`}</h4>
                      <span className={`text-[10px] font-black px-1.5 py-0.5 rounded tracking-tighter uppercase ${priorityClass}`}>
                        {req.priority || "may"}
                      </span>
                      {req.rule_type && (
                        <span className="text-[10px] font-medium text-outline bg-surface-container px-1.5 py-0.5 rounded uppercase">
                          {req.rule_type}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-on-surface-variant mt-1">
                      {req.operator}{" "}
                      {editingId === id ? (
                        <input
                          type="text"
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          className="bg-surface-container-high text-on-surface px-2 py-0.5 rounded text-xs border border-outline-variant/30 focus:outline-none focus:border-primary/50"
                        />
                      ) : (
                        String(req.value ?? "")
                      )}
                      {req.unit && ` ${req.unit}`}
                    </p>
                    {req.source && (
                      <div className="flex items-center gap-1 mt-2">
                        <span className="material-symbols-outlined text-[14px] text-outline">database</span>
                        <span className="text-[10px] font-medium text-outline">{req.source}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 flex-shrink-0">
                  {editingId === id ? (
                    <button
                      onClick={() => {
                        setReqs((prev) =>
                          prev.map((r, index) =>
                            (r.requirement_id || String(index)) === id
                              ? { ...r, value: editValue }
                              : r
                          )
                        );
                        setEditingId(null);
                      }}
                      className="px-4 py-2 text-xs font-bold text-primary hover:text-primary/80 transition-colors"
                    >
                      Save
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        setEditingId(id);
                        setEditValue(String(req.value ?? ""));
                      }}
                      className="px-4 py-2 text-xs font-bold text-outline hover:text-on-surface transition-colors"
                    >
                      Edit
                    </button>
                  )}
                  <button
                    onClick={() => toggleConfirm(id)}
                    className={`px-4 py-2 text-xs font-bold rounded-lg flex items-center gap-2 transition-all ${
                      isConfirmed
                        ? "bg-tertiary-container text-on-tertiary-container"
                        : "bg-surface-container text-on-surface hover:bg-tertiary-container/50"
                    }`}
                  >
                    <span className="material-symbols-outlined text-[16px]">
                      {isConfirmed ? "check_circle" : "radio_button_unchecked"}
                    </span>
                    {isConfirmed ? "Confirmed" : "Confirm"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {status === "done" && (
          <div className="px-8 py-6 bg-surface-container-low/50 flex justify-end gap-3">
            <button
              onClick={() => {
                setToastMsg("Draft saved successfully!");
                setTimeout(() => setToastMsg(""), 3000);
              }}
              className="px-6 py-3 text-sm font-bold text-primary hover:bg-surface-container transition-all rounded-lg"
            >
              Save Draft
            </button>
            <button
              onClick={() => router.push("/verification")}
              className="px-8 py-3 primary-gradient text-on-primary text-sm font-bold rounded-lg shadow-lg hover:opacity-90 active:scale-95 transition-all"
            >
              Finalize Step 2 →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
