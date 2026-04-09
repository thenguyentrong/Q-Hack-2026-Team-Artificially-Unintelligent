"use client";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { RankedSupplier } from "../types";

const statusBadge: Record<string, { text: string; color: string }> = {
  verified: { text: "\u2713 Verified", color: "bg-green-50 text-green-700 border border-green-200" },
  verified_with_gaps: { text: "\u26A0 Gaps", color: "bg-yellow-50 text-yellow-700 border border-yellow-200" },
  failed_hard_requirements: { text: "\u2717 Failed", color: "bg-red-50 text-red-700 border border-red-200" },
  insufficient_evidence: { text: "\u2014 Insufficient", color: "bg-gray-50 text-gray-500 border border-gray-200" },
  processing_error: { text: "\u2717 Error", color: "bg-red-50 text-red-700 border border-red-200" },
};

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const barColor =
    pct >= 60 ? "bg-green-500" : pct >= 30 ? "bg-yellow-500" : "bg-red-500";
  const textColor =
    pct >= 60 ? "text-green-700" : pct >= 30 ? "text-yellow-700" : "text-red-600";

  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-2 rounded-full bg-gray-200 overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`font-mono font-bold text-sm ${textColor}`}>{pct}%</span>
    </div>
  );
}

export function RankingTab({ ranking }: { ranking: RankedSupplier[] }) {
  if (!ranking.length) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        Waiting for ranking to complete...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-muted-foreground">
        {ranking.length} supplier(s) ranked by quality score
      </div>

      <div className="rounded-lg border border-[#E2E4E9] overflow-hidden bg-white shadow-sm">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#F8F9FA]">
              <TableHead className="w-10">#</TableHead>
              <TableHead>Supplier</TableHead>
              <TableHead>Score</TableHead>
              <TableHead>Hard</TableHead>
              <TableHead>Soft</TableHead>
              <TableHead>Fails</TableHead>
              <TableHead>?</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {ranking.map((r, i) => {
              const status = statusBadge[r.status] || statusBadge.processing_error;
              return (
                <TableRow key={r.supplier_id} className={i === 0 ? "bg-green-50/50" : ""}>
                  <TableCell className="font-bold text-muted-foreground">{i + 1}</TableCell>
                  <TableCell className="font-semibold text-sm">{r.supplier_name}</TableCell>
                  <TableCell>
                    <ScoreBar score={r.score} />
                  </TableCell>
                  <TableCell className="font-mono text-sm">{r.hard}</TableCell>
                  <TableCell className="font-mono text-sm">{r.soft}</TableCell>
                  <TableCell>
                    <span className={`font-mono text-sm ${r.fails > 0 ? "text-red-600 font-bold" : "text-muted-foreground"}`}>
                      {r.fails}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className={`font-mono text-sm ${r.unknowns > 3 ? "text-yellow-600" : "text-muted-foreground"}`}>
                      {r.unknowns}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge className={`text-xs ${status.color}`}>{status.text}</Badge>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>

      <div className="text-xs text-muted-foreground space-y-1">
        <p>Score reflects quality of pass (confidence + margin to limits), not just pass/fail</p>
        <p>Weighting: 70% hard / 30% soft (100% hard if no soft requirements) | Unknown is neutral</p>
      </div>
    </div>
  );
}
