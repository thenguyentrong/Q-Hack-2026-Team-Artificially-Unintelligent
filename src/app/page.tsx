"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { RequirementsTab } from "./components/RequirementsTab";
import { SuppliersTab } from "./components/SuppliersTab";
import { VerificationTab } from "./components/VerificationTab";
import { RankingTab } from "./components/RankingTab";
import { AgentTrace } from "./components/AgentTrace";
import { SourceViewer } from "./components/PdfPreview";
import { usePipeline } from "./hooks/usePipeline";

const TAB_ORDER = ["requirements", "suppliers", "verification", "ranking"] as const;

const LAYER_TO_TAB: Record<string, string> = {
  L1: "requirements",
  L2: "suppliers",
  L3: "verification",
  RANK: "ranking",
};

export default function WorkspacePage() {
  const { state, run, reset } = usePipeline();
  const [activeTab, setActiveTab] = useState("requirements");
  const [ingredients, setIngredients] = useState<string[]>([]);
  const [selectedIngredient, setSelectedIngredient] = useState("niacinamide");
  const [traceCollapsed, setTraceCollapsed] = useState(false);
  const [pdfPreview, setPdfPreview] = useState<{ url: string; evidenceId: string } | null>(null);

  // Track which tab was manually set to avoid overriding user navigation
  const userNavigatedRef = useRef(false);

  // Load ingredients on mount
  useEffect(() => {
    const isDev = process.env.NODE_ENV === "development";
    const baseUrl = isDev ? "http://127.0.0.1:8000" : "";
    fetch(`${baseUrl}/api/py/ingredients`)
      .then((r) => r.json())
      .then((data) => {
        if (data.ingredients) setIngredients(data.ingredients);
      })
      .catch(() => {});
  }, []);

  // Auto-advance tabs when layers complete
  useEffect(() => {
    if (state.status !== "running" || userNavigatedRef.current) return;
    if (state.activeLayer) {
      const tab = LAYER_TO_TAB[state.activeLayer];
      if (tab) setActiveTab(tab);
    }
  }, [state.activeLayer, state.status]);

  // Reset user navigation flag when pipeline starts
  useEffect(() => {
    if (state.status === "running") {
      userNavigatedRef.current = false;
    }
  }, [state.status]);

  const handleTabChange = useCallback((tab: string) => {
    userNavigatedRef.current = true;
    setActiveTab(tab);
  }, []);

  const handleRun = useCallback(() => {
    reset();
    setActiveTab("requirements");
    run(selectedIngredient);
  }, [selectedIngredient, run, reset]);

  const handlePreviewPdf = useCallback((url: string, evidenceId: string) => {
    setPdfPreview({ url, evidenceId });
  }, []);

  // Tab completion indicators
  const tabStatus = (tab: string): "idle" | "active" | "done" => {
    if (state.status === "idle") return "idle";
    const layerForTab: Record<string, string> = {
      requirements: "L1",
      suppliers: "L2",
      verification: "L3",
      ranking: "RANK",
    };
    const layer = layerForTab[tab];

    // Check if this layer's data is populated
    const hasData: Record<string, boolean> = {
      requirements: state.requirements.length > 0,
      suppliers: state.suppliers.length > 0,
      verification: state.verification !== null,
      ranking: state.ranking.length > 0,
    };

    if (hasData[tab]) return "done";
    if (state.activeLayer === layer) return "active";
    return "idle";
  };

  const handleExportBOM = () => {
    const csvContent =
      "data:text/csv;charset=utf-8," +
      "Component Name,Company,Supplier Count,RM SKU\n" +
      bomComponents
        .map(
          (r) =>
            `"${r.name}","${r.rm_company}","${r.supplier_count}","${r.rm_sku}"`
        )
        .join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `BOM_${selectedSku || "Export"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Find the primary (most-used / first) component
  const primaryComponent = bomComponents[0] || null;

  return (
    <div className="flex h-[calc(100vh-72px)]">
      {/* Main content */}
      <div className="flex-1 overflow-hidden flex flex-col min-w-0">
        {/* Header controls */}
        <div className="flex items-center gap-4 px-6 py-4 border-b border-border/50 flex-shrink-0">
          <div className="flex items-center gap-2">
            <label className="text-sm text-muted-foreground">Ingredient:</label>
            <select
              value={selectedIngredient}
              onChange={(e) => setSelectedIngredient(e.target.value)}
              disabled={state.status === "running"}
              className="bg-white text-[#1B263B] border border-[#E2E4E9] rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-[#1B263B]/20 min-w-[200px] cursor-pointer"
            >
              {ingredients.length > 0
                ? ingredients.map((ing) => (
                    <option key={ing} value={ing}>
                      {ing.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    </option>
                  ))
                : (
                    <option value="niacinamide">Niacinamide</option>
                  )
              }
            </select>
          </div>

          <button
            onClick={handleRun}
            disabled={state.status === "running"}
            className="inline-flex items-center gap-2 bg-[#1B263B] text-white rounded-md px-4 py-1.5 text-sm font-semibold hover:bg-[#2D3A4F] transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
          >
            {state.status === "running" ? (
              <>
                <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Running Pipeline...
              </>
            ) : (
              <>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Run Pipeline
              </>
            )}
          </button>

          {state.status === "done" && (
            <span className="text-xs text-green-600 font-medium">Pipeline complete</span>
          )}
          {state.status === "error" && (
            <span className="text-xs text-red-600 font-medium">Error: {state.error}</span>
          )}
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={handleTabChange} className="flex-1 flex flex-col overflow-hidden">
          <TabsList className="bg-transparent border-b border-border/50 rounded-none h-auto p-0 px-6 flex-shrink-0">
            {TAB_ORDER.map((tab) => {
              const labels: Record<string, string> = {
                requirements: "1. Requirements",
                suppliers: "2. Suppliers",
                verification: "3. Verification",
                ranking: "4. Ranking",
              };
              const status = tabStatus(tab);
              return (
                <TabsTrigger
                  key={tab}
                  value={tab}
                  className="rounded-none border-b-2 border-transparent data-[state=active]:border-[#1B263B] data-[state=active]:bg-transparent data-[state=active]:text-foreground text-muted-foreground px-4 py-2.5 text-sm"
                >
                  <span className="flex items-center gap-1.5">
                    {status === "done" && <span className="text-green-600 text-xs">{"\u2713"}</span>}
                    {status === "active" && (
                      <span className="w-2 h-2 rounded-full bg-[#4DA8DA] animate-pulse" />
                    )}
                    {labels[tab]}
                  </span>
                </TabsTrigger>
              );
            })}
          </TabsList>

          <div className="flex-1 overflow-auto p-6">
            <TabsContent value="requirements" className="mt-0">
              <RequirementsTab requirements={state.requirements} />
            </TabsContent>
            <TabsContent value="suppliers" className="mt-0">
              <SuppliersTab suppliers={state.suppliers} />
            </TabsContent>
            <TabsContent value="verification" className="mt-0">
              <VerificationTab
                verification={state.verification}
                supplierNames={state.supplierNames}
                onPreviewPdf={handlePreviewPdf}
              />
            </TabsContent>
            <TabsContent value="ranking" className="mt-0">
              <RankingTab ranking={state.ranking} />
            </TabsContent>
          </div>
        </Tabs>
      </div>

      {/* Agent trace sidebar */}
      <AgentTrace
        milestones={state.milestones}
        liveTraces={state.liveTraces}
        isRunning={state.status === "running"}
        collapsed={traceCollapsed}
        onToggle={() => setTraceCollapsed(!traceCollapsed)}
      />

      {/* Source viewer modal */}
      <SourceViewer
        url={pdfPreview?.url ?? null}
        evidenceId={pdfPreview?.evidenceId ?? null}
        onClose={() => setPdfPreview(null)}
      />
    </div>
  );
}
