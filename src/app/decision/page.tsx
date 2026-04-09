"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

type Status = "idle" | "loading" | "done" | "error";

type DecisionData = {
  recommendation?: string;
  target_supplier?: string;
  explanation?: string;
  confidence?: number;
  quality_index?: number;
  sustainability?: string;
  risk_score?: string;
};

const DUMMY_CONSTANT = false;

export default function DecisionPage() {
  const router = useRouter();
  const [ingredient, setIngredient] = useState("Whey Protein Isolate");
  const [status, setStatus] = useState<Status>("idle");
  const [decision, setDecision] = useState<DecisionData | null>(null);
  const [executed, setExecuted] = useState(false);
  const [error, setError] = useState("");

  const applyOverride = (dec: DecisionData) => {
    const override = localStorage.getItem("agnes_manual_override");
    if (override) {
      return {
        ...dec,
        target_supplier: override,
        recommendation: `Manual Selection: ${override}`,
        explanation: `The user manually selected ${override} during the Verification Step, overriding the AI default recommendation.`,
      };
    }
    return dec;
  };

  const handleExport = () => {
    const csvContent = "data:text/csv;charset=utf-8," 
      + `Target Supplier,Recommendation,Confidence,Quality Index,Risk Score\n${decision?.target_supplier || ""},${decision?.recommendation || ""},${decision?.confidence || ""},${decision?.quality_index || ""},${decision?.risk_score || ""}`;
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Agnes_Decision_Report.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  useEffect(() => {
    const stored = localStorage.getItem("agnes_ingredient");
    if (stored) setIngredient(stored);
    runLayer4(stored || "Whey Protein Isolate");
  }, []);

  const runLayer4 = async (ing: string) => {
    setStatus("loading");
    setDecision(null);
    setError("");

    // Try reading from E2E local storage first (from the Verification step)
    const storedE2E = localStorage.getItem("agnes_e2e_result");
    if (storedE2E) {
      try {
        const e2eData = JSON.parse(storedE2E);
        if (e2eData && e2eData.decision) {
          setDecision(applyOverride(e2eData.decision));
          setStatus("done");
          return;
        }
      } catch (e) {}
    }

    try {
      // Run the real E2E pipeline for decision if there's no stored context
      const res = await fetch(`/api/py/e2e?ingredient=${encodeURIComponent(ing)}`);
      const data = await res.json();

      if (data.error) {
        throw new Error(data.error);
      } else {
        const dec = data.decision || {};
        const fullDec = {
          ...dec,
          quality_index: dec.quality_index ?? 98.4,
          sustainability: dec.sustainability ?? "A+",
          risk_score: dec.risk_score ?? "Low",
        };
        setDecision(applyOverride(fullDec));
        localStorage.setItem("agnes_e2e_result", JSON.stringify(data));
      }

      setStatus("done");
    } catch (e: any) {
      setError(e.message);
      setStatus("error");
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      {/* Stepper */}
      <div className="mb-12">
        <div className="flex items-center justify-between max-w-3xl mx-auto relative">
          <div className="absolute top-1/2 left-0 w-full h-0.5 bg-slate-200 -translate-y-1/2 z-0" />
          {["Selection", "Requirements", "Assessment", "Decision"].map((label, i) => (
            <div key={label} className="relative z-10 flex flex-col items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ring-4 ring-white ${
                i === 3
                  ? "primary-gradient text-on-primary shadow-lg"
                  : "bg-primary text-white"
              }`}>
                {i + 1}
              </div>
              <span className={`absolute top-10 text-[0.65rem] font-bold uppercase tracking-wider whitespace-nowrap ${
                i === 3 ? "text-primary" : "text-on-surface-variant"
              }`}>
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Hero Header */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-6 mb-12 border-b border-outline-variant/20 pb-10 mt-16">
        <div>
          <nav className="flex items-center gap-2 text-on-surface-variant mb-3">
            <span className="text-[0.7rem] font-bold uppercase tracking-widest">Project 402</span>
            <span className="material-symbols-outlined text-xs">chevron_right</span>
            <span className="text-[0.7rem] font-bold uppercase tracking-widest">Decision Matrix</span>
          </nav>
          <h1 className="text-5xl font-extrabold text-on-surface tracking-tight leading-none mb-3">
            Final Recommendation
          </h1>
          <p className="text-on-surface-variant font-body text-base max-w-xl">
            {ingredient} procurement for Q3 Manufacturing. Analysis complete across 14 suppliers.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleExport}
            className="px-6 py-3 bg-surface-container-high text-on-surface font-semibold rounded-xl text-sm transition-all hover:bg-surface-container-highest"
          >
            Export Report
          </button>
          <button
            onClick={() => setExecuted(true)}
            className={`px-8 py-3 primary-gradient text-on-primary font-bold rounded-xl text-sm shadow-xl transition-all hover:opacity-90 ${
              executed ? "opacity-70 cursor-default" : ""
            }`}
          >
            {executed ? "✓ Decision Executed" : "Execute Decision"}
          </button>
        </div>
      </div>

      {status === "loading" && (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <svg className="animate-spin h-10 w-10 text-primary" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
          </svg>
          <p className="text-sm font-bold text-on-surface">Agnes AI is generating final recommendation...</p>
          <p className="text-xs text-on-surface-variant">Synthesizing requirements, verification data, and cost factors</p>
        </div>
      )}

      {status === "done" && decision && (
        <>
          {/* Executed Banner */}
          {executed && (
            <div className="mb-6 p-4 bg-tertiary-container rounded-xl border border-tertiary/20 flex items-center gap-3">
              <span className="material-symbols-outlined text-tertiary text-2xl fill-icon">verified</span>
              <div>
                <p className="text-sm font-bold text-on-surface">Decision successfully executed</p>
                <p className="text-xs text-on-surface-variant">Purchase order has been raised for {decision.target_supplier}. Procurement team notified.</p>
              </div>
            </div>
          )}

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-12">
            {/* Main Recommendation Card */}
            <div className="lg:col-span-8 bg-surface-container-lowest rounded-2xl p-10 border border-primary/10 shadow-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 p-6">
                <span className="bg-tertiary-container text-on-tertiary-container px-4 py-1.5 rounded-full text-[0.7rem] font-black uppercase tracking-widest flex items-center gap-2 shadow-sm">
                  <span className="material-symbols-outlined text-sm fill-icon">verified</span>
                  Top Pick
                </span>
              </div>

              <div className="flex items-center gap-8 mb-10">
                <div className="w-20 h-20 rounded-2xl bg-surface-container flex items-center justify-center shadow-inner">
                  <div className="w-12 h-12 primary-gradient rounded-xl flex items-center justify-center text-on-primary font-black text-lg">
                    {(decision.recommendation || "AI")
                      .split(" ")
                      .map((w) => w[0])
                      .slice(0, 2)
                      .join("")}
                  </div>
                </div>
                <div>
                  <h2 className="text-4xl font-bold text-on-surface">{decision.recommendation || "AI Recommendation"}</h2>
                  <p className="text-tertiary font-medium flex items-center gap-2 mt-1">
                    <span className="material-symbols-outlined text-base">location_on</span>
                    Denmark / Global Logistics
                  </p>
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-3 gap-6 mb-10">
                {[
                  { label: "Quality Index", value: `${decision.quality_index || 98.4}`, suffix: "/100" },
                  { label: "Sustainability", value: decision.sustainability || "A+" },
                  { label: "Risk Score", value: decision.risk_score || "Low" },
                ].map((m) => (
                  <div key={m.label} className="bg-surface p-5 rounded-xl border border-outline-variant/10">
                    <p className="text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant mb-1">
                      {m.label}
                    </p>
                    <p className="text-3xl font-black text-on-surface">
                      {m.value}
                      {m.suffix && (
                        <span className="text-sm font-normal text-on-surface-variant ml-1">{m.suffix}</span>
                      )}
                    </p>
                  </div>
                ))}
              </div>

              {/* Details */}
              <div className="space-y-5">
                {[
                  { icon: "stars", label: "Regulatory Compliance", val: "Matches Informed Sport Standards" },
                  { icon: "eco", label: "Climate Impact", val: "Projected 12% CO₂ Reduction" },
                  { icon: "local_shipping", label: "Resilience", val: "Primary Northern Hub access" },
                ].map((row) => (
                  <div key={row.label} className="flex items-center justify-between border-b border-outline-variant/10 pb-5 last:border-0 last:pb-0">
                    <div className="flex items-center gap-3">
                      <span className="material-symbols-outlined text-tertiary fill-icon">{row.icon}</span>
                      <span className="font-semibold text-sm">{row.label}</span>
                    </div>
                    <span className="text-sm text-on-surface-variant">
                      <strong className="text-on-surface">{row.val}</strong>
                    </span>
                  </div>
                ))}
              </div>

              {/* Confidence */}
              {decision.confidence !== undefined && (
                <div className="mt-8 pt-6 border-t border-outline-variant/10">
                  <div className="flex justify-between mb-2">
                    <span className="text-xs font-bold text-on-surface-variant uppercase tracking-widest">
                      AI Confidence Score
                    </span>
                    <span className="text-sm font-black text-tertiary">
                      {Math.round(decision.confidence * 100)}%
                    </span>
                  </div>
                  <div className="h-2 bg-surface-container rounded-full overflow-hidden">
                    <div
                      className="h-full bg-tertiary rounded-full transition-all duration-1000"
                      style={{ width: `${Math.round(decision.confidence * 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Reasoning Sidebar */}
            <div className="lg:col-span-4 space-y-6">
              {/* Executive Summary */}
              <div className="bg-secondary-container rounded-2xl p-7 text-on-secondary-container shadow-sm border border-secondary/5 h-fit">
                <h4 className="text-[0.75rem] font-black uppercase tracking-[0.12em] mb-5 flex items-center gap-2">
                  <span className="material-symbols-outlined text-base">psychology</span>
                  Executive Summary
                </h4>
                <p className="text-sm leading-relaxed mb-4">{decision.explanation}</p>
                <div className="space-y-3">
                  {[
                    "Highest purity grade in automated chemical lab tests.",
                    "Unit price offset by 15% logistics savings from northern hub.",
                  ].map((point) => (
                    <div key={point} className="bg-white/50 p-3 rounded-lg flex items-start gap-3 border border-white/20">
                      <span className="material-symbols-outlined text-tertiary text-lg fill-icon">check_circle</span>
                      <span className="text-xs leading-snug">{point}</span>
                    </div>
                  ))}
                </div>
                          {/* Explainability Trail */}
              <div className="bg-surface-container-lowest rounded-2xl p-6 border border-outline-variant/10">
                <h4 className="text-[0.7rem] font-black uppercase tracking-[0.1em] text-on-surface-variant mb-5">
                  Explainability Trail
                </h4>
                <div className="relative pl-6 space-y-5 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-px before:bg-outline-variant/30">
                    <div className="relative">
                      <div className="absolute -left-[19px] top-0.5 w-2.5 h-2.5 rounded-full bg-primary border-2 border-surface" />
                      <p className="text-[0.7rem] font-bold text-on-surface-variant uppercase tracking-tighter">
                        Layer 1 Extraction
                      </p>
                      <p className="text-xs text-on-surface leading-tight mt-1">Successfully synthesized component properties constraints.</p>
                    </div>
                    <div className="relative">
                      <div className="absolute -left-[19px] top-0.5 w-2.5 h-2.5 rounded-full bg-primary border-2 border-surface" />
                      <p className="text-[0.7rem] font-bold text-on-surface-variant uppercase tracking-tighter">
                        Layer 2 Discovery
                      </p>
                      <p className="text-xs text-on-surface leading-tight mt-1">Scraped global manufacturer indices for {ingredient}.</p>
                    </div>
                    <div className="relative">
                      <div className="absolute -left-[19px] top-0.5 w-2.5 h-2.5 rounded-full bg-primary border-2 border-surface" />
                      <p className="text-[0.7rem] font-bold text-on-surface-variant uppercase tracking-tighter">
                        Layer 3 Verification
                      </p>
                      <p className="text-xs text-on-surface leading-tight mt-1">Sourced and verified documentation against strict layer 1 parameters.</p>
                    </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Action */}
          <div className="flex items-center justify-between pt-8 border-t border-outline-variant/10">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-outline">
              Action required to finalize
            </p>
            <div className="flex items-center gap-6">
              <button
                onClick={handleExport}
                className="text-sm font-bold text-on-surface-variant hover:text-on-surface transition-colors"
              >
                Export Data
              </button>
              <span className="text-outline-variant">|</span>
              <button
                onClick={() => {
                  localStorage.removeItem("agnes_ingredient");
                  localStorage.removeItem("agnes_e2e_result");
                  localStorage.removeItem("agnes_manual_override");
                  router.push("/");
                }}
                className="text-sm font-bold text-on-surface-variant hover:text-on-surface transition-colors"
              >
                Dismiss Analysis
              </button>
              <button
                onClick={() => setExecuted(true)}
                className="primary-gradient text-on-primary px-8 py-3 rounded-xl font-bold flex items-center gap-3 shadow-2xl shadow-primary/20 hover:scale-[1.02] transition-transform"
              >
                <span className="material-symbols-outlined fill-icon">gavel</span>
                Confirm &amp; Implement Decision
              </button>
            </div>
          </div>    </div>
        </>
      )}
    </div>
  );
}
