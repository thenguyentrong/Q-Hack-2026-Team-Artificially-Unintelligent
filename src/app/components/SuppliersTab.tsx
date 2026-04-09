"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CandidateSupplier } from "../types";

const confidenceColor: Record<string, string> = {
  high: "text-green-700",
  medium: "text-yellow-600",
  low: "text-muted-foreground",
};

export function SuppliersTab({ suppliers }: { suppliers: CandidateSupplier[] }) {
  if (!suppliers.length) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        Waiting for Layer 2 to complete...
      </div>
    );
  }

  const dbCount = suppliers.filter((s) => s.supplier.supplier_id.startsWith("DB-")).length;
  const l2Count = suppliers.length - dbCount;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span>{suppliers.length} suppliers</span>
        {dbCount > 0 && <Badge className="bg-blue-50 text-blue-700 text-xs">{dbCount} database</Badge>}
        {l2Count > 0 && <Badge className="bg-purple-50 text-purple-700 text-xs">{l2Count} discovered</Badge>}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {suppliers.map((s) => {
          const isDb = s.supplier.supplier_id.startsWith("DB-");
          const conf = s.candidate_confidence || "medium";
          return (
            <Card key={s.supplier.supplier_id} className="bg-white border-[#E2E4E9] shadow-sm">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold">{s.supplier.supplier_name}</CardTitle>
                  <Badge variant="outline" className={isDb ? "border-blue-300 text-blue-700 text-xs" : "border-purple-300 text-purple-700 text-xs"}>
                    {isDb ? "DB" : "L2"}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {s.supplier.country && (
                  <div className="text-muted-foreground">{s.supplier.country}</div>
                )}
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">Confidence:</span>
                  <span className={`font-medium ${confidenceColor[conf]}`}>
                    {conf}
                  </span>
                </div>
                {s.source_urls && s.source_urls.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-muted-foreground text-xs">{s.source_urls.length} source URL(s)</span>
                    {s.source_urls.slice(0, 3).map((url, i) => (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="block text-xs text-blue-600 hover:underline truncate"
                      >
                        {url}
                      </a>
                    ))}
                  </div>
                )}
                {s.supplier.website && (
                  <a
                    href={s.supplier.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    {s.supplier.website}
                  </a>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
