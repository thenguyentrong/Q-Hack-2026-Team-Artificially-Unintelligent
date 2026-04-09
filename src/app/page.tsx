"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

// --- Types from real DB ---
type Product = {
  Id: number;
  SKU: string;
  company: string;
};

type BomComponent = {
  rm_sku: string;
  rm_company: string;
  supplier_count: number;
  name: string;
};

type Status = "idle" | "loading" | "done" | "error";

// Utility: extract ingredient name from raw-material SKU
function skuToName(sku: string): string {
  // RM-Cnn-ingredient-name-hexhash → strip prefix and hash
  return sku
    .replace(/^RM-C\d+-/, "")
    .replace(/-[0-9a-f]{8}$/, "")
    .split("-")
    .map((w: string) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

// Map company to a Material Icon name (best-effort)
const COMPANY_ICON: Record<string, string> = {
  "Optimum Nutrition": "fitness_center",
  "NOW Foods": "science",
  "Nature Made": "eco",
  "One A Day": "local_pharmacy",
  "Animal": "sports_mma",
  "Equate": "medication",
  "Body Fortress": "sports_gymnastics",
  "Biochem": "biotech",
};
function iconForCompany(company: string): string {
  return COMPANY_ICON[company] || "inventory_2";
}

export default function SelectionPage() {
  const router = useRouter();

  // Products from DB
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedSku, setSelectedSku] = useState<string | null>(null);
  const [productsStatus, setProductsStatus] = useState<Status>("idle");

  // BOM from DB
  const [bomComponents, setBomComponents] = useState<BomComponent[]>([]);
  const [bomStatus, setBomStatus] = useState<Status>("idle");
  const [selectedIngredient, setSelectedIngredient] = useState<BomComponent | null>(null);

  const [toastMsg, setToastMsg] = useState("");

  const showToast = (msg: string) => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(""), 3000);
  };

  // Load real products on mount
  useEffect(() => {
    setProductsStatus("loading");
    fetch("/api/py/catalog/products?limit=12")
      .then((r) => r.json())
      .then((data) => {
        if (data.error) throw new Error(data.error);
        const prods: Product[] = data.products || [];
        setProducts(prods);
        if (prods.length > 0) {
          setSelectedSku(prods[0].SKU);
        }
        setProductsStatus("done");
      })
      .catch(() => setProductsStatus("error"));
  }, []);

  // Load BOM whenever selected product changes
  useEffect(() => {
    if (!selectedSku) return;
    setBomStatus("loading");
    setBomComponents([]);
    setSelectedIngredient(null);
    fetch(`/api/py/catalog/bom?sku=${encodeURIComponent(selectedSku)}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.error) throw new Error(data.error);
        const comps: BomComponent[] = data.components || [];
        setBomComponents(comps);
        setBomStatus("done");
      })
      .catch(() => setBomStatus("error"));
  }, [selectedSku]);

  const selectedProduct = products.find((p) => p.SKU === selectedSku) || null;

  const startAnalysis = async (row: BomComponent, product: Product | null) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("agnes_ingredient", row.name);
      localStorage.setItem("agnes_layer1", "");
      localStorage.setItem("agnes_layer2", "");
      localStorage.setItem("agnes_layer3", "");
      localStorage.setItem("agnes_layer4", "");
      localStorage.removeItem("agnes_manual_override");
      localStorage.removeItem("agnes_e2e_result");
      
      try {
        setToastMsg("Running preprocessing layer...");
        const res = await fetch("/api/py/preprocess", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            schema_version: "1.0",
            company_id: product?.Id || 1,
            company_name: row.rm_company,
            RM_id: row.rm_sku,
            RM_sku: row.rm_sku
          })
        });
        
        if (!res.ok) {
           throw new Error("Preprocessing failed");
        }
        const data = await res.json();
        localStorage.setItem("agnes_preprocessed_data", JSON.stringify(data));
        router.push("/requirements");
      } catch (e: any) {
        showToast("Error during preprocessing: " + e.message);
      }
    }
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
    <div className="max-w-7xl mx-auto">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed bottom-4 right-4 bg-tertiary-container text-on-tertiary-container px-6 py-3 rounded-lg shadow-2xl border border-tertiary/20 font-bold text-sm z-50 flex items-center gap-2">
          <span className="material-symbols-outlined text-tertiary fill-icon">info</span>
          {toastMsg}
        </div>
      )}

      {/* Breadcrumb + Title */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[0.7rem] font-bold tracking-widest uppercase text-on-surface-variant">
            Enterprise Procurement
          </span>
          <span className="text-outline-variant">/</span>
          <span className="text-[0.7rem] font-bold tracking-widest uppercase text-primary">
            Agnes Sport Protein Co
          </span>
          {productsStatus === "done" && (
            <>
              <span className="text-outline-variant">/</span>
              <span className="text-[0.65rem] font-bold px-2 py-0.5 bg-tertiary-container/30 text-tertiary rounded-full">
                Live DB
              </span>
            </>
          )}
        </div>
        <h1 className="text-4xl font-extrabold tracking-tight text-on-surface">
          Product &amp; BOM Selection
        </h1>
        <p className="text-on-surface-variant mt-2 text-sm">
          Select a product and identify which BOM component to find a substitute
          for. Data sourced live from the Agnes supplier catalog.
        </p>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-12 gap-8 items-start">
        {/* Product Column */}
        <div className="col-span-12 lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between px-1">
            <h2 className="text-sm font-bold text-on-surface uppercase tracking-wider">
              Active Portfolio
            </h2>
            {productsStatus === "done" && (
              <span className="text-[0.7rem] font-bold text-tertiary px-2 py-0.5 bg-tertiary-container/20 rounded">
                {products.length} Products
              </span>
            )}
            {productsStatus === "loading" && (
              <span className="text-[0.7rem] font-bold text-outline px-2 py-0.5 bg-surface-container rounded">
                Loading DB...
              </span>
            )}
          </div>

          <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
            {productsStatus === "loading" &&
              [...Array(6)].map((_, i) => (
                <div
                  key={i}
                  className="p-4 bg-white rounded-xl border border-surface-container animate-pulse flex items-center gap-3"
                >
                  <div className="w-10 h-10 rounded-lg bg-surface-container" />
                  <div className="flex-1">
                    <div className="h-3 bg-surface-container rounded w-28 mb-2" />
                    <div className="h-2 bg-surface-container rounded w-20" />
                  </div>
                </div>
              ))}

            {productsStatus === "done" &&
              products.map((p) => {
                const isSelected = p.SKU === selectedSku;
                return (
                  <div
                    key={p.SKU}
                    onClick={() => setSelectedSku(p.SKU)}
                    className={`p-4 bg-white rounded-xl flex items-center justify-between cursor-pointer transition-all ${
                      isSelected
                        ? "border-2 border-primary shadow-sm"
                        : "border border-surface-container hover:border-outline-variant/30"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                          isSelected ? "bg-primary/5" : "bg-surface-container"
                        }`}
                      >
                        <span
                          className={`material-symbols-outlined ${
                            isSelected ? "text-primary" : "text-outline-variant"
                          }`}
                          style={
                            isSelected
                              ? { fontVariationSettings: "'FILL' 1" }
                              : {}
                          }
                        >
                          {iconForCompany(p.company)}
                        </span>
                      </div>
                      <div>
                        <p className="text-sm font-bold text-on-surface leading-none mb-1">
                          {p.company}
                        </p>
                        <p className="text-[0.65rem] text-on-surface-variant font-medium uppercase tracking-tighter">
                          SKU: {p.SKU.split("-").slice(-1)[0]}
                        </p>
                      </div>
                    </div>
                    {isSelected && (
                      <span className="material-symbols-outlined text-primary text-xl fill-icon">
                        check_circle
                      </span>
                    )}
                  </div>
                );
              })}
          </div>

          <button
            onClick={() => showToast("SKU Import feature is under development.")}
            className="w-full mt-4 flex items-center justify-center gap-2 py-3 border-2 border-dashed border-outline-variant/30 rounded-xl text-on-surface-variant text-sm font-medium hover:bg-surface-container-low transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">add</span>
            Import New SKU
          </button>
        </div>

        {/* BOM Module */}
        <div className="col-span-12 lg:col-span-8">
          <div className="bg-white rounded-2xl border border-surface-container shadow-sm overflow-hidden">
            {/* BOM Header */}
            <div className="p-6 border-b border-surface-container flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-on-surface">
                    Bill of Materials (BOM)
                  </h2>
                  <span className="text-[0.6rem] font-bold px-2 py-0.5 bg-primary/5 text-primary rounded-full border border-primary/10">
                    LIVE DB
                  </span>
                </div>
                <p className="text-xs text-on-surface-variant font-medium mt-0.5">
                  {selectedProduct
                    ? `${selectedProduct.company} · ${selectedProduct.SKU}`
                    : "Select a product"}
                </p>
              </div>
              {primaryComponent && (
                <div className="text-right">
                  <p className="text-[0.6rem] font-bold text-on-surface-variant uppercase tracking-widest mb-0.5">
                    Target for Substitution
                  </p>
                  <p className="text-sm font-bold text-primary flex items-center gap-1 justify-end">
                    {selectedIngredient
                      ? selectedIngredient.name
                      : primaryComponent.name}
                    <span className="material-symbols-outlined text-[16px]">
                      info
                    </span>
                  </p>
                </div>
              )}
            </div>

            {/* Table */}
            <div className="overflow-x-auto max-h-[380px] overflow-y-auto">
              <table className="w-full text-left">
                <thead className="sticky top-0 z-10">
                  <tr className="bg-surface-container-lowest">
                    <th className="px-6 py-4 text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant">
                      Component Name
                    </th>
                    <th className="px-6 py-4 text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant">
                      Company
                    </th>
                    <th className="px-6 py-4 text-[0.65rem] font-bold uppercase tracking-widest text-on-surface-variant">
                      Suppliers
                    </th>
                    <th className="px-6 py-4 text-right" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-container">
                  {bomStatus === "loading" &&
                    [...Array(5)].map((_, i) => (
                      <tr key={i}>
                        <td className="px-6 py-5" colSpan={4}>
                          <div className="animate-pulse flex gap-3">
                            <div className="w-2 h-2 rounded-full bg-surface-container mt-2" />
                            <div className="flex-1">
                              <div className="h-3 bg-surface-container rounded w-40 mb-1.5" />
                              <div className="h-2 bg-surface-container rounded w-24" />
                            </div>
                          </div>
                        </td>
                      </tr>
                    ))}

                  {bomStatus === "done" &&
                    bomComponents.map((row, idx) => {
                      const isPrimary = idx === 0;
                      const isSelected =
                        selectedIngredient?.rm_sku === row.rm_sku;
                      return (
                        <tr
                          key={row.rm_sku}
                          className={
                            isPrimary
                              ? "bg-primary/5"
                              : isSelected
                              ? "bg-secondary-container/20"
                              : "hover:bg-surface-container-lowest transition-colors"
                          }
                        >
                          <td className="px-6 py-5">
                            <div className="flex items-center gap-3">
                              <div
                                className={`w-2 h-2 rounded-full flex-shrink-0 ${
                                  isPrimary
                                    ? "bg-primary animate-pulse"
                                    : "bg-outline-variant/30"
                                }`}
                              />
                              <div>
                                <p
                                  className={`text-sm leading-tight ${
                                    isPrimary
                                      ? "font-bold text-on-surface"
                                      : "font-medium text-on-surface"
                                  }`}
                                >
                                  {row.name}
                                </p>
                                <p className="text-[0.65rem] text-on-surface-variant font-mono mt-0.5 truncate max-w-[200px]">
                                  {row.rm_sku}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-5 text-sm text-on-surface">
                            {row.rm_company}
                          </td>
                          <td className="px-6 py-5">
                            <span
                              className={`text-xs font-bold px-2 py-1 rounded-full ${
                                row.supplier_count > 0
                                  ? "bg-tertiary-container text-on-tertiary-container"
                                  : "bg-surface-container text-on-surface-variant"
                              }`}
                            >
                              {row.supplier_count > 0
                                ? `${row.supplier_count} supplier${row.supplier_count > 1 ? "s" : ""}`
                                : "No supplier"}
                            </span>
                          </td>
                          <td className="px-6 py-5 text-right">
                            <button
                              onClick={() => {
                                setSelectedIngredient(row);
                                startAnalysis(row, selectedProduct);
                              }}
                              className={`px-4 py-2 rounded-lg text-xs font-bold shadow-sm hover:opacity-90 transition-all flex items-center gap-2 ml-auto ${
                                isPrimary || isSelected
                                  ? "primary-gradient text-on-primary"
                                  : "bg-surface-container text-on-surface hover:bg-surface-container-high"
                              }`}
                            >
                              <span className="material-symbols-outlined text-[16px]">
                                swap_horiz
                              </span>
                              Find Substitute
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>

            {/* BOM Footer */}
            <div className="p-6 bg-surface-container-lowest border-t border-surface-container flex justify-between items-center">
              <p className="text-[0.7rem] text-on-surface-variant font-medium flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px] text-tertiary">
                  database
                </span>
                {bomStatus === "done"
                  ? `${bomComponents.length} components · Agnes Catalog DB`
                  : "Loading from database..."}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleExportBOM}
                  disabled={bomStatus !== "done"}
                  className="px-4 py-1.5 text-xs font-bold text-on-surface border border-outline-variant/30 rounded-md hover:bg-surface-container-low transition-all disabled:opacity-40"
                >
                  Export BOM
                </button>
                <button
                  onClick={() =>
                    showToast("Historical Pricing data not currently available.")
                  }
                  className="px-4 py-1.5 text-xs font-bold text-on-surface border border-outline-variant/30 rounded-md hover:bg-surface-container-low transition-all"
                >
                  Historical Pricing
                </button>
              </div>
            </div>
          </div>

          {/* Intelligence insight */}
          {bomStatus === "done" && primaryComponent && (
            <div className="mt-4 p-4 bg-error-container/10 border border-error/20 rounded-xl flex items-start gap-3">
              <span className="material-symbols-outlined text-error text-xl mt-0.5 fill-icon">
                warning
              </span>
              <div>
                <p className="text-sm font-bold text-on-surface">
                  Supply Risk Detected
                </p>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  <strong>{primaryComponent.name}</strong> is the primary
                  component for {selectedProduct?.company}. Click{" "}
                  <button
                    onClick={() => startAnalysis(primaryComponent, selectedProduct)}
                    className="text-primary font-bold underline decoration-primary/40 hover:decoration-primary"
                  >
                    Find Substitute
                  </button>{" "}
                  to run the Agnes AI pipeline and discover validated
                  alternatives.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
