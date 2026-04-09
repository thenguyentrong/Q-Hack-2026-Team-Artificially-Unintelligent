"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Separator } from "@/components/ui/separator";
import type {
  EvidenceItem,
  ExtractedAttribute,
  QualityVerificationOutput,
  SupplierAssessment,
  VerificationResultItem,
} from "../types";

const statusIcon: Record<string, string> = {
  pass: "\u2713",
  fail: "\u2717",
  unknown: "?",
  partial: "~",
};

const statusColor: Record<string, string> = {
  pass: "text-green-700",
  fail: "text-red-600",
  unknown: "text-yellow-600",
  partial: "text-blue-600",
};

const evidenceStatusColor: Record<string, string> = {
  retrieved: "text-green-700",
  unreachable: "text-red-600",
  blocked: "text-red-600",
  irrelevant: "text-muted-foreground",
  parse_failed: "text-yellow-600",
};

const overallStatusLabel: Record<string, { text: string; color: string }> = {
  verified: { text: "Verified", color: "bg-green-50 text-green-700 border border-green-200" },
  verified_with_gaps: { text: "Verified (gaps)", color: "bg-yellow-50 text-yellow-700 border border-yellow-200" },
  failed_hard_requirements: { text: "Failed", color: "bg-red-50 text-red-700 border border-red-200" },
  insufficient_evidence: { text: "Insufficient", color: "bg-gray-50 text-gray-500 border border-gray-200" },
  processing_error: { text: "Error", color: "bg-red-50 text-red-700 border border-red-200" },
};

function SourceTypeBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    coa: "bg-green-50 text-green-700",
    tds: "bg-blue-50 text-blue-700",
    certification_page: "bg-purple-50 text-purple-700",
    product_page: "bg-yellow-50 text-yellow-700",
    marketing_page: "bg-orange-50 text-orange-700",
    other: "bg-gray-100 text-gray-500",
  };
  return (
    <Badge className={`text-[10px] uppercase ${colors[type] || colors.other}`}>
      {type.replace("_", " ")}
    </Badge>
  );
}

function EvidenceSection({
  items,
  onPreviewPdf,
}: {
  items: EvidenceItem[];
  onPreviewPdf: (url: string, evidenceId: string) => void;
}) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
        Evidence Sources ({items.length})
      </h4>
      <div className="space-y-1">
        {items.map((ev) => {
          return (
            <div
              key={ev.evidence_id}
              className="flex items-center gap-2 text-xs py-1.5 px-2 rounded bg-[#F8F9FA] border border-[#E2E4E9]/50"
              id={`evidence-${ev.evidence_id}`}
            >
              <SourceTypeBadge type={ev.source_type} />
              <a
                href={ev.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline truncate flex-1 min-w-0"
                title={ev.source_url}
              >
                {ev.source_url}
              </a>
              <span className={`flex-shrink-0 ${evidenceStatusColor[ev.status]}`}>
                {ev.status === "retrieved" ? "\u2713" : "\u2717"} {ev.status}
              </span>
              {ev.status === "retrieved" && (
                <button
                  onClick={() => onPreviewPdf(ev.source_url, ev.evidence_id)}
                  className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-700 hover:bg-blue-100 flex-shrink-0"
                >
                  View Source
                </button>
              )}
              <a
                href={ev.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground flex-shrink-0"
                title="Open in new tab"
              >
                &#8599;
              </a>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ExtractionSection({
  attributes,
  evidenceItems,
}: {
  attributes: ExtractedAttribute[];
  evidenceItems: EvidenceItem[];
}) {
  if (!attributes.length) return null;

  const evidenceMap = new Map(evidenceItems.map((e) => [e.evidence_id, e]));

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
        Extracted Values ({attributes.length})
      </h4>
      <div className="rounded border border-[#E2E4E9] overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#F8F9FA]">
              <TableHead className="text-xs">Field</TableHead>
              <TableHead className="text-xs">Value</TableHead>
              <TableHead className="text-xs">Unit</TableHead>
              <TableHead className="text-xs">Confidence</TableHead>
              <TableHead className="text-xs">Source</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {attributes.map((attr) => {
              const ev = evidenceMap.get(attr.source_evidence_id);
              return (
                <TableRow key={attr.attribute_id}>
                  <TableCell className="font-mono text-xs">{attr.field_name}</TableCell>
                  <TableCell className="text-xs font-medium">{String(attr.value)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{attr.unit || "\u2014"}</TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={`text-[10px] ${
                        attr.confidence === "high"
                          ? "border-green-300 text-green-700"
                          : attr.confidence === "medium"
                          ? "border-yellow-300 text-yellow-700"
                          : "border-gray-300 text-gray-500"
                      }`}
                    >
                      {attr.confidence}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {ev ? (
                      <a
                        href={`#evidence-${ev.evidence_id}`}
                        className="text-[10px] text-blue-600 hover:underline"
                        onClick={(e) => {
                          e.preventDefault();
                          document.getElementById(`evidence-${ev.evidence_id}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
                        }}
                      >
                        [{ev.evidence_id}] &#8599;
                      </a>
                    ) : (
                      <span className="text-[10px] text-muted-foreground">\u2014</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function VerificationSection({ results }: { results: VerificationResultItem[] }) {
  if (!results.length) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">
        Verification Results
      </h4>
      <div className="rounded border border-[#E2E4E9] overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#F8F9FA]">
              <TableHead className="text-xs">Field</TableHead>
              <TableHead className="text-xs">Observed</TableHead>
              <TableHead className="text-xs">Status</TableHead>
              <TableHead className="text-xs">Reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {results.map((vr) => {
              const st = typeof vr.status === "string" ? vr.status : "unknown";
              return (
                <TableRow key={vr.verification_id}>
                  <TableCell className="font-mono text-xs">{vr.field_name}</TableCell>
                  <TableCell className="text-xs">
                    {vr.observed_value != null
                      ? `${vr.observed_value}${vr.unit ? " " + vr.unit : ""}`
                      : "\u2014"}
                  </TableCell>
                  <TableCell>
                    <span className={`font-mono font-bold text-xs ${statusColor[st]}`}>
                      {statusIcon[st]} {st.toUpperCase()}
                    </span>
                  </TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-xs truncate" title={vr.reason}>
                    {vr.reason}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function SupplierPanel({
  assessment,
  supplierName,
  onPreviewPdf,
}: {
  assessment: SupplierAssessment;
  supplierName: string;
  onPreviewPdf: (url: string, evidenceId: string) => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const statusInfo = overallStatusLabel[assessment.overall_status] || overallStatusLabel.processing_error;

  return (
    <div className="rounded-lg border border-[#E2E4E9] overflow-hidden bg-white shadow-sm">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 bg-[#F8F9FA] hover:bg-[#F0F1F3] transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="font-semibold text-sm">{supplierName}</span>
          <Badge className={`text-xs ${statusInfo.color}`}>{statusInfo.text}</Badge>
          <Badge variant="outline" className="text-[10px]">
            Confidence: {assessment.overall_evidence_confidence}
          </Badge>
        </div>
        <span className="text-muted-foreground text-xs">{expanded ? "\u25B2" : "\u25BC"}</span>
      </button>

      {expanded && (
        <div className="p-4 space-y-4">
          <EvidenceSection items={assessment.evidence_items} onPreviewPdf={onPreviewPdf} />
          <Separator />
          <ExtractionSection
            attributes={assessment.extracted_attributes}
            evidenceItems={assessment.evidence_items}
          />
          <Separator />
          <VerificationSection results={assessment.verification_results} />

          {assessment.coverage_summary && (
            <div className="text-xs text-muted-foreground pt-2">
              <span className="font-medium">Coverage: </span>
              Hard: {assessment.coverage_summary.hard_pass}P {assessment.coverage_summary.hard_fail}F{" "}
              {assessment.coverage_summary.hard_unknown}U | Soft: {assessment.coverage_summary.soft_pass}P{" "}
              {assessment.coverage_summary.soft_fail}F {assessment.coverage_summary.soft_unknown}U
            </div>
          )}

          {assessment.notes.length > 0 && (
            <div className="text-xs text-muted-foreground">
              {assessment.notes.map((note, i) => (
                <div key={i} className="truncate" title={note}>
                  {note}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function VerificationTab({
  verification,
  supplierNames,
  onPreviewPdf,
}: {
  verification: QualityVerificationOutput | null;
  supplierNames: Record<string, string>;
  onPreviewPdf: (url: string, evidenceId: string) => void;
}) {
  if (!verification) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        Waiting for Layer 3 to complete...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-muted-foreground">
        {verification.supplier_assessments.length} supplier assessment(s)
      </div>
      {verification.supplier_assessments.map((sa) => (
        <SupplierPanel
          key={sa.supplier_id}
          assessment={sa}
          supplierName={supplierNames[sa.supplier_id] || sa.supplier_id}
          onPreviewPdf={onPreviewPdf}
        />
      ))}
    </div>
  );
}
