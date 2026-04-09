"use client";

import { useState, useRef } from "react";

// ─── Types ───────────────────────────────────────────────────────────────────
type StepStatus = "idle" | "running" | "complete" | "error";

interface StepState {
  status: StepStatus;
  data: any;
  duration?: number;
  logs: string[];
}

const LAYERS = [
  {
    id: "layer1",
    num: 1,
    title: "Requirements Extraction",
    desc: "LLM agent identifies hard constraints and regulatory specs via Google Search Grounding",
    endpoint: (ing: string) => `/api/py/layer1?ingredient=${encodeURIComponent(ing)}`,
  },
  {
    id: "layer2",
    num: 2,
    title: "Supplier Discovery",
    desc: "Agentic search pipeline finds functional substitutes from market data and supplier catalogs",
    endpoint: (ing: string) => `/api/py/layer2?ingredient=${encodeURIComponent(ing)}`,
  },
  {
    id: "layer3",
    num: 3,
    title: "Quality Verification",
    desc: "Extracts and compares compliance fields from TDS and Certificates of Analysis",
    endpoint: () => `/api/py/layer3`,
  },
  {
    id: "layer4",
    num: 4,
    title: "Consensus & Decision",
    desc: "Aggregates cost, compliance, and supply-chain tradeoffs into a sourcing recommendation",
    endpoint: () => `/api/py/layer4`,
  },
];

// ─── Layer Result Renderers ───────────────────────────────────────────────────
function Layer1Results({ data }: { data: any }) {
  if (!data || data.error) {
    return (
      <div style={{ padding: "1rem 1.5rem", color: "var(--error)", fontSize: "0.85rem" }}>
        {data?.detail || data?.error || "Unknown error"}
      </div>
    );
  }

  const reqs: any[] = data.requirements || [];

  return (
    <div className="results-area">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.75rem" }}>
        <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
          Found <strong style={{ color: "var(--text-primary)" }}>{reqs.length}</strong> quality requirements
          {data.ingredient_id && <> for <strong style={{ color: "var(--accent-secondary)" }}>{data.ingredient_id}</strong></>}
        </div>
      </div>
      <div className="requirements-grid">
        {reqs.map((r: any, i: number) => (
          <div key={i} className="req-card">
            <div className="req-field">{r.field_name || "Requirement"}</div>
            <div className="req-value">
              {r.operator && <span style={{ color: "var(--text-tertiary)", fontWeight: 400, marginRight: 4 }}>{r.operator}</span>}
              {r.value !== undefined ? String(r.value) : "—"}
            </div>
            {r.unit && <div className="req-unit">{r.unit}</div>}
            {r.priority && (
              <div className={`priority-badge ${r.priority}`}>{r.priority.toUpperCase()}</div>
            )}
            {r.source && (
              <div style={{ marginTop: "0.5rem", fontSize: "0.7rem", color: "var(--text-tertiary)" }}>
                📄 {r.source}
              </div>
            )}
          </div>
        ))}
        {reqs.length === 0 && (
          <div style={{ gridColumn: "1 / -1", color: "var(--text-tertiary)", fontSize: "0.85rem" }}>
            No requirements extracted.
          </div>
        )}
      </div>
      {data.notes && (
        <div style={{ marginTop: "1rem", fontSize: "0.78rem", color: "var(--text-tertiary)", fontStyle: "italic" }}>
          {data.notes}
        </div>
      )}
    </div>
  );
}

function Layer2Results({ data }: { data: any }) {
  if (!data || data.error) {
    return (
      <div style={{ padding: "1rem 1.5rem", color: "var(--error)", fontSize: "0.85rem" }}>
        {data?.detail || data?.error || "Unknown error"}
      </div>
    );
  }

  const candidates: any[] = data.candidates || data.suppliers || [];

  if (candidates.length === 0) {
    return (
      <div className="results-area">
        <p style={{ color: "var(--text-tertiary)", fontSize: "0.85rem" }}>
          No suppliers discovered. Raw: {JSON.stringify(data).substring(0, 200)}
        </p>
      </div>
    );
  }

  return (
    <div className="results-area">
      <div style={{ marginBottom: "0.75rem", fontSize: "0.8rem", color: "var(--text-secondary)" }}>
        Discovered <strong style={{ color: "var(--text-primary)" }}>{candidates.length}</strong> candidate suppliers
      </div>
      {candidates.map((s: any, i: number) => (
        <div key={i} className="supplier-card">
          <div className="supplier-rank">#{i + 1}</div>
          <div style={{ flex: 1 }}>
            <div className="supplier-name">{s.name || s.supplier_name || `Supplier ${i + 1}`}</div>
            <div className="supplier-meta">
              {[s.region, s.grade, s.certifications].filter(Boolean).join(" · ") || s.source || ""}
            </div>
          </div>
          {s.score !== undefined && (
            <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "var(--accent-secondary)" }}>
              {(s.score * 100).toFixed(0)}%
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Layer3Results({ data }: { data: any }) {
  if (!data) return null;
  const verifications: any[] = data.verifications || [];

  return (
    <div className="results-area">
      {verifications.map((v: any, i: number) => (
        <div key={i} className="verification-row">
          <div>
            <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{v.supplier}</div>
            <div style={{ fontSize: "0.78rem", color: "var(--text-tertiary)", marginTop: 2 }}>
              Assay: {v.assay_extracted} · Confidence: {(v.confidence * 100).toFixed(0)}%
            </div>
          </div>
          <div className={`pass-pill ${v.pass ? "pass" : "fail"}`}>
            {v.pass ? "✓ PASS" : "✗ FAIL"}
          </div>
        </div>
      ))}
    </div>
  );
}

function Layer4Results({ data }: { data: any }) {
  if (!data) return null;

  return (
    <div className="results-area">
      <div className="recommendation-box">
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "1rem" }}>
          <div>
            <div style={{ fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.8px", color: "var(--success)", fontWeight: 700, marginBottom: 6 }}>
              Final Recommendation
            </div>
            <div style={{ fontSize: "1.35rem", fontWeight: 800, letterSpacing: "-0.5px" }}>
              {data.recommendation?.toUpperCase() || "N/A"}
            </div>
          </div>
          {data.target_supplier && (
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "0.72rem", color: "var(--text-tertiary)", marginBottom: 4 }}>Selected Supplier</div>
              <div style={{ fontWeight: 700, color: "var(--accent-secondary)" }}>{data.target_supplier}</div>
            </div>
          )}
        </div>

        {data.explanation && (
          <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "1rem" }}>
            {data.explanation}
          </p>
        )}

        {data.confidence !== undefined && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>Confidence</span>
              <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--success)" }}>
                {(data.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="confidence-bar-track">
              <div className="confidence-bar-fill" style={{ width: `${(data.confidence * 100).toFixed(0)}%` }} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Step component ───────────────────────────────────────────────────────────
function PipelineStep({
  layer,
  step,
  isExpanded,
  onToggle,
  onRun,
  isAnyRunning,
  ingredient,
}: {
  layer: typeof LAYERS[0];
  step: StepState;
  isExpanded: boolean;
  onToggle: () => void;
  onRun: () => void;
  isAnyRunning: boolean;
  ingredient: string;
}) {
  const statusClass =
    step.status === "running" ? "running" :
    step.status === "complete" ? "complete" :
    step.status === "error" ? "error-state" : "";

  const badgeLabel =
    step.status === "running" ? "Running..." :
    step.status === "complete" ? `Done${step.duration ? ` · ${step.duration}s` : ""}` :
    step.status === "error" ? "Error" : "Idle";

  return (
    <div className={`pipeline-step ${statusClass} animate-in`}>
      {/* Header */}
      <div className="step-header" onClick={onToggle} id={`step-header-${layer.id}`}>
        <div className="step-number">
          {step.status === "running" ? (
            <div className="spinner" style={{ width: 14, height: 14, borderWidth: "1.5px" }} />
          ) : step.status === "complete" ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : step.status === "error" ? (
            <span style={{ fontSize: "0.9rem" }}>!</span>
          ) : (
            layer.num
          )}
        </div>

        <div className="step-info">
          <div className="step-title">{layer.title}</div>
          <div className="step-desc">{layer.desc}</div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexShrink: 0 }}>
          <span className={`step-badge ${step.status === "error" ? "error" : step.status}`}>{badgeLabel}</span>
          {step.status === "idle" && (
            <button
              className="btn-primary"
              style={{ padding: "6px 14px", fontSize: "0.8rem" }}
              onClick={(e) => { e.stopPropagation(); onRun(); }}
              disabled={isAnyRunning}
              id={`run-${layer.id}-btn`}
            >
              Run
            </button>
          )}
          {step.status !== "idle" && (
            <svg className={`step-chevron ${isExpanded ? "open" : ""}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          )}
        </div>
      </div>

      {/* Body */}
      {isExpanded && step.status !== "idle" && (
        <div className="step-body">
          {/* Agent log */}
          {step.logs.length > 0 && (
            <div className="agent-log" id={`log-${layer.id}`}>
              {step.logs.map((log, i) => {
                const isOk = log.includes("✓") || log.includes("complete");
                const isErr = log.includes("✗") || log.includes("error");
                const isInfo = log.includes("→") || log.includes("Querying");
                return (
                  <div key={i} className="log-line">
                    <span className="log-time">{new Date().toTimeString().slice(0, 8)}</span>
                    <span className={`log-text ${isOk ? "ok" : isErr ? "error" : isInfo ? "info" : ""}`}>{log}</span>
                  </div>
                );
              })}
              {step.status === "running" && <span style={{ color: "var(--accent-primary)" }}>▊</span>}
            </div>
          )}

          {/* Results */}
          {step.status === "complete" && step.data && (
            layer.id === "layer1" ? <Layer1Results data={step.data} /> :
            layer.id === "layer2" ? <Layer2Results data={step.data} /> :
            layer.id === "layer3" ? <Layer3Results data={step.data} /> :
            <Layer4Results data={step.data} />
          )}
          {step.status === "error" && (
            <div style={{ padding: "1rem 1.5rem", color: "var(--error)", fontSize: "0.85rem" }}>
              {step.data?.detail || step.data?.error || "Request failed."}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function WorkspacePage() {
  const [ingredient, setIngredient] = useState("Ascorbic Acid");
  const [steps, setSteps] = useState<Record<string, StepState>>({
    layer1: { status: "idle", data: null, logs: [] },
    layer2: { status: "idle", data: null, logs: [] },
    layer3: { status: "idle", data: null, logs: [] },
    layer4: { status: "idle", data: null, logs: [] },
  });
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    layer1: true, layer2: true, layer3: true, layer4: true,
  });

  const isAnyRunning = Object.values(steps).some((s) => s.status === "running");

  const appendLog = (id: string, msg: string) => {
    setSteps((prev) => ({
      ...prev,
      [id]: { ...prev[id], logs: [...prev[id].logs, msg] },
    }));
  };

  const runLayer = async (layerId: string, urlFn: (ing: string) => string) => {
    const url = urlFn(ingredient);

    setSteps((prev) => ({
      ...prev,
      [layerId]: { status: "running", data: null, logs: [] },
    }));
    setExpanded((prev) => ({ ...prev, [layerId]: true }));

    const start = Date.now();

    setTimeout(() => appendLog(layerId, `→ Initializing agent pipeline for "${ingredient}"...`), 100);
    setTimeout(() => appendLog(layerId, `→ Querying backend: ${url}`), 400);

    try {
      const res = await fetch(url);
      const text = await res.text();
      let data: any;
      try { data = JSON.parse(text); } catch { data = { error: "Non-JSON response", detail: text.substring(0, 300) }; }

      const duration = ((Date.now() - start) / 1000).toFixed(1);

      if (data.error) {
        appendLog(layerId, `✗ Agent returned error: ${data.error}`);
        setSteps((prev) => ({
          ...prev,
          [layerId]: { ...prev[layerId], status: "error", data, duration: parseFloat(duration) },
        }));
      } else {
        const count =
          data.requirements?.length ?? data.candidates?.length ?? data.verifications?.length;
        appendLog(layerId, `✓ Complete in ${duration}s${count !== undefined ? ` · ${count} records` : ""}`);
        setSteps((prev) => ({
          ...prev,
          [layerId]: { ...prev[layerId], status: "complete", data, duration: parseFloat(duration) },
        }));
      }
    } catch (err: any) {
      const duration = ((Date.now() - start) / 1000).toFixed(1);
      appendLog(layerId, `✗ Network error: ${err.message}`);
      setSteps((prev) => ({
        ...prev,
        [layerId]: { ...prev[layerId], status: "error", data: { error: err.message }, duration: parseFloat(duration) },
      }));
    }
  };

  const runAllSequential = async () => {
    // Reset all
    setSteps({
      layer1: { status: "idle", data: null, logs: [] },
      layer2: { status: "idle", data: null, logs: [] },
      layer3: { status: "idle", data: null, logs: [] },
      layer4: { status: "idle", data: null, logs: [] },
    });
    setExpanded({ layer1: true, layer2: true, layer3: true, layer4: true });

    for (const layer of LAYERS) {
      await runLayer(layer.id, layer.endpoint);
      await new Promise((r) => setTimeout(r, 300));
    }
  };

  const resetAll = () => {
    setSteps({
      layer1: { status: "idle", data: null, logs: [] },
      layer2: { status: "idle", data: null, logs: [] },
      layer3: { status: "idle", data: null, logs: [] },
      layer4: { status: "idle", data: null, logs: [] },
    });
  };

  const completedCount = Object.values(steps).filter((s) => s.status === "complete").length;
  const errorCount = Object.values(steps).filter((s) => s.status === "error").length;

  return (
    <div className="animate-in">
      {/* Page Header */}
      <div className="page-header">
        <h1 className="page-title">Ingredient Analysis</h1>
        <p className="page-subtitle">
          Run the 4-layer AI pipeline to identify functional substitutes, verify quality compliance, and generate a sourcing recommendation.
        </p>
      </div>

      {/* Stats Row */}
      {completedCount > 0 && (
        <div className="stats-row fade-in">
          <div className="stat-card">
            <div className="stat-icon" style={{ background: "rgba(16,185,129,0.1)" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </div>
            <div>
              <div className="stat-label">Layers Complete</div>
              <div className="stat-value">{completedCount}<span style={{ fontSize: "0.8rem", color: "var(--text-tertiary)", fontWeight: 400 }}>/4</span></div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: "rgba(255,90,31,0.1)" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-secondary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </div>
            <div>
              <div className="stat-label">Requirements Found</div>
              <div className="stat-value">{steps.layer1?.data?.requirements?.length ?? "—"}</div>
            </div>
          </div>
          <div className="stat-card">
            <div className="stat-icon" style={{ background: "rgba(99,102,241,0.1)" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#818CF8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
            <div>
              <div className="stat-label">Suppliers Discovered</div>
              <div className="stat-value">{steps.layer2?.data?.candidates?.length ?? steps.layer2?.data?.suppliers?.length ?? "—"}</div>
            </div>
          </div>
          {steps.layer4?.data?.recommendation && (
            <div className="stat-card">
              <div className="stat-icon" style={{ background: "var(--success-bg)" }}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--success)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
                </svg>
              </div>
              <div>
                <div className="stat-label">Decision</div>
                <div className="stat-value" style={{ color: "var(--success)", fontSize: "1rem" }}>
                  {steps.layer4.data.recommendation}
                </div>
                <div className="stat-sub">{steps.layer4.data.target_supplier}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Input Card */}
      <div className="analysis-input-card">
        <div style={{ marginBottom: "0.875rem" }}>
          <div className="section-label">Target Ingredient</div>
          <p style={{ fontSize: "0.82rem", color: "var(--text-tertiary)" }}>
            Enter the canonical ingredient name to analyze across all 4 agent layers.
          </p>
        </div>
        <div className="input-row">
          <div style={{ position: "relative", flex: 1 }}>
            <svg style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text-tertiary)" }}
              width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              id="ingredient-input"
              className="input-field"
              style={{ paddingLeft: "2.25rem" }}
              value={ingredient}
              onChange={(e) => setIngredient(e.target.value)}
              placeholder="e.g. Ascorbic Acid, Citric Acid, Xanthan Gum..."
              onKeyDown={(e) => e.key === "Enter" && !isAnyRunning && runAllSequential()}
            />
          </div>
          <button
            className="btn-primary"
            style={{ padding: "10px 20px", fontSize: "0.9rem" }}
            onClick={runAllSequential}
            disabled={isAnyRunning || !ingredient.trim()}
            id="run-all-btn"
          >
            {isAnyRunning ? (
              <><div className="spinner" style={{ width: 14, height: 14, borderWidth: "1.5px" }} /> Running Pipeline...</>
            ) : (
              <>
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Run Full Pipeline
              </>
            )}
          </button>
          {!isAnyRunning && completedCount > 0 && (
            <button className="btn-ghost" onClick={resetAll} id="reset-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="1 4 1 10 7 10" /><path d="M3.51 15a9 9 0 1 0 .49-6.5" />
              </svg>
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Pipeline */}
      <div className="section-label">Agent Pipeline</div>
      <div className="pipeline-wrapper">
        {LAYERS.map((layer) => (
          <PipelineStep
            key={layer.id}
            layer={layer}
            step={steps[layer.id]}
            isExpanded={expanded[layer.id]}
            onToggle={() => setExpanded((p) => ({ ...p, [layer.id]: !p[layer.id] }))}
            onRun={() => runLayer(layer.id, layer.endpoint)}
            isAnyRunning={isAnyRunning}
            ingredient={ingredient}
          />
        ))}
      </div>
    </div>
  );
}
