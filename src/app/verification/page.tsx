"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

type SupplierResult = {
  name?: string;
  supplier_name?: string;
  region?: string;
  grade?: string;
  score?: number;
  purity?: string | number;
  assay?: string | number;
  certification?: string;
  processing?: string;
  sodium?: string | number;
  calcium?: string | number;
  esg?: string;
  pass?: boolean;
};

type Status = "idle" | "loading" | "done" | "error";

const CRITERIA = [
  { key: "purity", label: "Purity Profile (>90%)", desc: "Protein content (dry basis) batch verification." },
  { key: "certification", label: "Organic Certification", desc: "EU Council Regulation (EC) No 834/2007 compliance." },
  { key: "processing", label: "Processing Method", desc: "Cold-processed Cross-Flow Microfiltration (CFM) preferred." },
  { key: "mineral", label: "Mineral Profile", desc: "Target: Sodium <180mg, Calcium >450mg per 100g." },
  { key: "esg", label: "Ethical Sourcing (ESG)", desc: "Proof of sustainable animal welfare and supply transparency." },
];

function PassBadge({ pass, value }: { pass?: boolean; value?: string }) {
  if (value === "pending" || !value) {
    return (
      <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-surface-container-highest w-fit text-on-surface-variant opacity-60">
        <span className="material-symbols-outlined text-sm fill-icon">help</span>
        <span className="text-[0.7rem] font-bold uppercase">Pending</span>
      </div>
    );
  }
  if (pass === false) {
    return (
      <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-error-container/20 w-fit text-on-error-container">
        <span className="material-symbols-outlined text-sm fill-icon">cancel</span>
        <span className="text-[0.7rem] font-bold uppercase">{value}</span>
      </div>
    );
  }
  return (
    <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-tertiary-container w-fit text-on-tertiary-container">
      <span className="material-symbols-outlined text-sm fill-icon">check_circle</span>
      <span className="text-[0.7rem] font-bold uppercase">{value}</span>
    </div>
  );
}

export default function VerificationPage() {
  const router = useRouter();
  const [ingredient, setIngredient] = useState("Whey Protein Isolate");
  const [status, setStatus] = useState<Status>("idle");
  const [suppliers, setSuppliers] = useState<SupplierResult[]>([]);
  const [scanProgress, setScanProgress] = useState(0);
  const [error, setError] = useState("");
  const [docsRequested, setDocsRequested] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem("agnes_ingredient");
    if (stored) setIngredient(stored);
    runVerification(stored || "Whey Protein Isolate");
  }, []);

  const runVerification = async (ing: string) => {
    setStatus("loading");
    setScanProgress(0);
    setSuppliers([]);
    setError("");

    // Simulate progressive scan
    const progressInterval = setInterval(() => {
      setScanProgress((p) => Math.min(p + Math.random() * 12, 88));
    }, 600);

    try {
      // Run Layer 2 (supplier discovery)
      // Run the real E2E Pipeline (this takes 60-90s)
      const res = await fetch(`/api/py/e2e?ingredient=${encodeURIComponent(ing)}`);
      const data = await res.json();

      if (data.error || data.status === "error") {
        throw new Error(data.error_detail || data.error || "E2E Engine Failure");
      }

      clearInterval(progressInterval);
      setScanProgress(100);

      const layer3Raw = data.layer3_raw || [];

      // Map layer3_raw to SupplierResult
      const finalSuppliers: SupplierResult[] = layer3Raw.map((s: any) => {
        // Extract fields dynamically from what the AI extracted
        const getField = (fName: string) => s.extracted?.find((x: any) => x.field.toLowerCase() === fName.toLowerCase())?.value;

        return {
          name: s.supplier,
          supplier_name: s.supplier,
          region: "Global", // fallback since region isn't extracted
          purity: getField("purity") || getField("protein") || getField("assay"),
          certification: getField("certification") || getField("organic"),
          processing: getField("processing"),
          sodium: getField("sodium"),
          calcium: getField("calcium"),
          esg: getField("esg") || getField("sustainability"),
          pass: s.status === "verified" || s.status === "verified_with_gaps" ? true : s.status === "failed_hard_requirements" ? false : undefined,
        };
      });

      setSuppliers(finalSuppliers);
      localStorage.setItem("agnes_e2e_result", JSON.stringify(data));
      setStatus("done");
    } catch (e: any) {
      clearInterval(progressInterval);
      setError(e.message);
      setStatus("error");
    }
  };

  const initials = (name: string) =>
    name
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();

  const getCellValue = (s: SupplierResult, key: string): { val: string; pass?: boolean } => {
    switch (key) {
      case "purity":
        return { val: s.purity ? String(s.purity) : "pending", pass: s.purity ? true : undefined };
      case "certification":
        return {
          val: s.certification || "pending",
          pass: s.certification === "Expired" ? false : s.certification ? true : undefined,
        };
      case "processing":
        return { val: s.processing || "pending", pass: s.processing === "Cold-processed" ? true : s.processing ? false : undefined };
      case "mineral": {
        const na = s.sodium ? String(s.sodium) : undefined;
        const ca = s.calcium ? String(s.calcium) : undefined;
        if (!na && !ca) return { val: "pending" };
        return { val: `Na: ${na ?? "?"} · Ca: ${ca ?? "?"}`, pass: na ? !na.includes("195") : undefined };
      }
      case "esg":
        return { val: s.esg || "pending", pass: s.esg === "Verified" ? true : s.esg === "Pending" ? undefined : false };
      default:
        return { val: "—" };
    }
  };

  const passCount = suppliers.filter((s) => s.pass === true).length;
  const gapCount = suppliers.filter((s) => s.pass === false).length;

  return (
    <div className="max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-medium text-outline-variant mb-2">
            <span>Project 402</span>
            <span className="material-symbols-outlined text-[14px]">chevron_right</span>
            <span className="text-primary font-bold">Verification Matrix</span>
          </div>
          <h1 className="text-3xl font-extrabold text-on-surface tracking-tight">Verification Matrix</h1>
          <p className="text-sm text-on-surface-variant mt-1">
            AI-extracted compliance fields for{" "}
            <strong className="text-primary">{ingredient}</strong> substitutes
          </p>
        </div>

        {/* Scan Progress */}
        <div className="flex items-center gap-4">
          {status !== "idle" && (
            <div className="flex items-center bg-surface-container-low px-4 py-1.5 rounded-full text-[0.65rem] font-bold text-on-surface-variant border border-outline-variant/10">
              <span className="mr-2 uppercase">Scan Progress</span>
              <div className="w-24 h-1 bg-surface-variant rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-500"
                  style={{ width: `${scanProgress}%` }}
                />
              </div>
              <span className="ml-2">{Math.round(scanProgress)}%</span>
            </div>
          )}
          <button
            onClick={() => runVerification(ingredient)}
            disabled={status === "loading"}
            className="px-4 py-2 border border-outline-variant/30 rounded-lg text-xs font-bold text-on-surface hover:bg-surface-container transition-all flex items-center gap-2 disabled:opacity-50"
          >
            <span className="material-symbols-outlined text-[16px]">refresh</span>
            Re-scan
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        {[
          { label: "Total Suppliers", value: suppliers.length || "—", sub: status === "done" ? "+3 New discovery" : "Scanning...", color: "border-primary", textColor: "text-tertiary" },
          { label: "Verified Passes", value: passCount || "—", sub: passCount ? `${Math.round((passCount / Math.max(suppliers.length, 1)) * 100)}% pass rate` : "Scanning...", color: "border-tertiary", textColor: "text-tertiary-dim" },
          { label: "Critical Gaps", value: gapCount || "—", sub: gapCount ? "Requires review" : "None detected", color: "border-error", textColor: "text-error" },
        ].map((s) => (
          <div key={s.label} className={`bg-surface-container-lowest p-6 rounded-xl shadow-sm border-l-4 ${s.color}`}>
            <p className="text-[0.7rem] font-bold text-on-surface-variant uppercase tracking-[0.1em] mb-2">{s.label}</p>
            <div className="flex items-baseline gap-2">
              {status === "loading" ? (
                <div className="animate-pulse bg-surface-container h-8 w-12 rounded" />
              ) : (
                <span className="text-3xl font-extrabold text-on-surface">{s.value}</span>
              )}
              <span className={`text-xs font-medium ${s.textColor}`}>{s.sub}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
        {/* Comparison Matrix */}
        <section className="xl:col-span-3">
          <div className="bg-surface-container-lowest rounded-xl border border-surface-container overflow-hidden">
            {status === "loading" ? (
              <div className="p-12 text-center">
                <svg className="animate-spin h-8 w-8 text-primary mx-auto mb-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                <p className="text-sm font-bold text-on-surface">AI agents scanning supplier databases...</p>
                <p className="text-xs text-on-surface-variant mt-1">Extracting compliance fields from TDS and CoA documents</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-surface-container-low border-b border-surface-container-high">
                      <th className="p-6 w-[280px]">
                        <span className="text-[0.65rem] font-bold uppercase tracking-[0.15em] text-on-surface-variant">
                          Criterion
                        </span>
                      </th>
                      {suppliers.map((s) => (
                        <th key={s.name || s.supplier_name} className="p-6 border-l border-surface-container/50">
                          <div className="flex flex-col gap-3">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center font-bold text-xs text-primary">
                                {initials(s.name || s.supplier_name || "?")}
                              </div>
                              <div>
                                <p className="text-[0.75rem] font-bold text-on-surface">
                                  {s.name || s.supplier_name}
                                </p>
                                <p className="text-[0.6rem] text-on-surface-variant">{s.region || ""}</p>
                              </div>
                            </div>
                            <button
                              onClick={() => {
                                localStorage.setItem("agnes_manual_override", s.name || s.supplier_name || "");
                                router.push("/decision");
                              }}
                              className="w-full py-2 primary-gradient text-on-primary text-[0.7rem] font-bold uppercase tracking-widest rounded-lg shadow-sm hover:opacity-90 transition-all"
                            >
                              Select Option
                            </button>
                          </div>
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-container/50">
                    {CRITERIA.map((criterion) => (
                      <tr key={criterion.key} className="group hover:bg-surface-container-low transition-colors">
                        <td className="p-6">
                          <p className="text-sm font-bold text-on-surface">{criterion.label}</p>
                          <p className="text-[0.65rem] text-on-surface-variant mt-1 leading-relaxed">
                            {criterion.desc}
                          </p>
                        </td>
                        {suppliers.map((s) => {
                          const { val, pass } = getCellValue(s, criterion.key);
                          return (
                            <td key={s.name} className="p-6 border-l border-surface-container/50">
                              <PassBadge pass={pass} value={val} />
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        {/* Evidence Repository */}
        <section className="xl:col-span-1">
          <div className="bg-surface-container-low p-6 rounded-xl border border-surface-container h-full flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-base font-extrabold text-on-surface">Evidence Repository</h3>
              <button className="text-xs font-bold text-primary tracking-widest hover:underline">VIEW ALL</button>
            </div>

            <div className="flex-1 space-y-3 mb-6">
              {[
                { name: "actus_whey_iso_tds.pdf", size: "2.4 MB", status: "Verified by AI", type: "pdf" },
                { name: "arla_ingredients_coa.pdf", size: "1.8 MB", status: "Verified by AI", type: "pdf" },
                { name: "factory_audit_photos.zip", size: "45 MB", status: "Manual Upload", type: "img" },
                { name: "prinova_compliance.pdf", size: "1.2 MB", status: "Processing...", type: "doc" },
              ].map((doc) => (
                <div
                  key={doc.name}
                  className="flex items-center gap-3 p-3 bg-surface-container-lowest rounded-xl shadow-sm border border-outline-variant/5"
                >
                  <div
                    className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      doc.type === "pdf"
                        ? "bg-error/10 text-error"
                        : doc.type === "img"
                        ? "bg-secondary/10 text-secondary"
                        : "bg-primary/10 text-primary"
                    }`}
                  >
                    <span className="material-symbols-outlined text-xl fill-icon">
                      {doc.type === "pdf" ? "picture_as_pdf" : doc.type === "img" ? "image" : "description"}
                    </span>
                  </div>
                  <div className="flex-1 overflow-hidden">
                    <p className="text-xs font-bold text-on-surface truncate">{doc.name}</p>
                    <p className="text-[0.6rem] text-on-surface-variant">
                      {doc.size} • {doc.status}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Gap Action */}
            <div className="space-y-3 bg-primary/5 p-5 rounded-2xl border border-primary/10">
              <div className="flex items-center gap-2 text-primary">
                <span className="material-symbols-outlined text-lg">report_problem</span>
                <span className="text-[0.7rem] font-bold uppercase tracking-widest">Document Gaps</span>
              </div>
              <p className="text-xs text-on-surface-variant leading-relaxed">
                4 missing documents required to finalize high-confidence verification.
              </p>
              <button
                onClick={() => setDocsRequested(true)}
                disabled={docsRequested}
                className={`w-full py-3 ${
                  docsRequested
                    ? "bg-tertiary-container text-on-tertiary-container"
                    : "primary-gradient text-on-primary shadow-lg"
                } rounded-xl text-xs font-black uppercase tracking-[0.12em] hover:opacity-90 transition-all flex items-center justify-center gap-2`}
              >
                <span className="material-symbols-outlined text-lg">
                  {docsRequested ? "check_circle" : "mail"}
                </span>
                {docsRequested ? "Requested" : "Request Missing Docs"}
              </button>
            </div>

            <button
              onClick={() => router.push("/decision")}
              disabled={status !== "done"}
              className="w-full mt-4 primary-gradient text-on-primary py-3 rounded-xl text-sm font-bold shadow-md hover:opacity-90 transition-all disabled:opacity-40 flex items-center justify-center gap-2"
            >
              Continue to Decision →
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
