// TypeScript interfaces matching the Python Pydantic schemas

// ── Enums ──────────────────────────────────────────────────────────────────────

export type Priority = "hard" | "soft";
export type RuleType = "range" | "minimum" | "maximum" | "enum_match" | "boolean_required" | "free_text_reference";
export type Confidence = "high" | "medium" | "low";
export type VerificationStatus = "pass" | "fail" | "unknown" | "partial";
export type EvidenceStatus = "retrieved" | "unreachable" | "blocked" | "irrelevant" | "parse_failed";
export type SourceType = "coa" | "tds" | "certification_page" | "product_page" | "marketing_page" | "other";
export type SupplierAssessmentStatus =
  | "verified"
  | "verified_with_gaps"
  | "failed_hard_requirements"
  | "insufficient_evidence"
  | "processing_error";

// ── Layer 1: Requirements ──────────────────────────────────────────────────────

export interface RequirementInput {
  requirement_id: string;
  field_name: string;
  rule_type: RuleType;
  operator: string;
  priority: Priority;
  min_value?: number | null;
  max_value?: number | null;
  unit?: string | null;
  allowed_values?: string[] | null;
  source_reference?: string | null;
  reference_text?: string | null;
  required?: boolean | null;
}

// ── Layer 2: Suppliers ─────────────────────────────────────────────────────────

export interface SupplierRef {
  supplier_id: string;
  supplier_name: string;
  country?: string | null;
  website?: string | null;
}

export interface CandidateSupplier {
  supplier: SupplierRef;
  candidate_confidence?: Confidence;
  source_urls?: string[];
}

// ── Layer 3: Quality Verification ──────────────────────────────────────────────

export interface EvidenceItem {
  evidence_id: string;
  source_type: SourceType;
  source_url: string;
  title?: string | null;
  status: EvidenceStatus;
  retrieved_at: string;
}

export interface ExtractedAttribute {
  attribute_id: string;
  field_name: string;
  value: string | number;
  unit?: string | null;
  source_evidence_id: string;
  confidence: Confidence;
  extraction_method: string;
}

export interface VerificationResultItem {
  verification_id: string;
  requirement_id: string;
  field_name: string;
  status: VerificationStatus;
  observed_value?: string | number | null;
  unit?: string | null;
  confidence: Confidence;
  reason: string;
  supporting_evidence_ids: string[];
}

export interface CoverageSummary {
  requirements_total: number;
  hard_pass: number;
  hard_fail: number;
  hard_unknown: number;
  soft_pass: number;
  soft_fail: number;
  soft_unknown: number;
}

export interface SupplierAssessment {
  supplier_id: string;
  evidence_items: EvidenceItem[];
  extracted_attributes: ExtractedAttribute[];
  verification_results: VerificationResultItem[];
  coverage_summary: CoverageSummary;
  overall_evidence_confidence: Confidence;
  overall_status: SupplierAssessmentStatus;
  notes: string[];
}

// ── Pipeline Output ────────────────────────────────────────────────────────────

export interface QualityVerificationOutput {
  schema_version: string;
  ingredient_id: string;
  supplier_assessments: SupplierAssessment[];
}

export interface RankedSupplier {
  supplier_id: string;
  supplier_name: string;
  score: number;
  hard: string;
  soft: string;
  fails: number;
  unknowns: number;
  status: SupplierAssessmentStatus;
}

// ── SSE Events ─────────────────────────────────────────────────────────────────

export interface TraceEvent {
  step: "L1" | "L2" | "L3" | "RANK";
  msg: string;
  ts: string;
  live?: boolean;    // true = transient live trace from logging/print
  links?: string[];  // URLs found in the message
}

export interface PipelineState {
  status: "idle" | "running" | "done" | "error";
  activeLayer: "L1" | "L2" | "L3" | "RANK" | null;
  requirements: RequirementInput[];
  suppliers: CandidateSupplier[];
  supplierNames: Record<string, string>;
  verification: QualityVerificationOutput | null;
  ranking: RankedSupplier[];
  milestones: TraceEvent[];   // persistent milestone events (layer transitions, results)
  liveTraces: TraceEvent[];   // ephemeral live traces (cleared between layers)
  error: string | null;
}
