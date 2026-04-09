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
import type { RequirementInput } from "../types";

function formatConstraint(r: RequirementInput): string {
  if (r.rule_type === "range" && r.min_value != null && r.max_value != null) {
    return `${r.min_value} – ${r.max_value}${r.unit ? " " + r.unit : ""}`;
  }
  if (r.rule_type === "minimum" && r.min_value != null) {
    return `≥ ${r.min_value}${r.unit ? " " + r.unit : ""}`;
  }
  if (r.rule_type === "maximum" && r.max_value != null) {
    return `≤ ${r.max_value}${r.unit ? " " + r.unit : ""}`;
  }
  if (r.rule_type === "enum_match" && r.allowed_values?.length) {
    return r.allowed_values.join(", ");
  }
  if (r.rule_type === "boolean_required") {
    return r.required ? "Required" : "Optional";
  }
  return r.operator || "—";
}

export function RequirementsTab({ requirements }: { requirements: RequirementInput[] }) {
  if (!requirements.length) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        Waiting for Layer 1 to complete...
      </div>
    );
  }

  const hard = requirements.filter((r) => r.priority === "hard").length;
  const soft = requirements.length - hard;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span>{requirements.length} requirements</span>
        <Badge variant="destructive" className="text-xs">{hard} hard</Badge>
        <Badge variant="secondary" className="text-xs">{soft} soft</Badge>
      </div>

      <div className="rounded-lg border border-border/50 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="w-10">#</TableHead>
              <TableHead>Field</TableHead>
              <TableHead>Rule</TableHead>
              <TableHead>Constraint</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Source</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {requirements.map((r, i) => (
              <TableRow
                key={r.requirement_id}
                className={r.priority === "hard" ? "border-l-2 border-l-red-500" : "border-l-2 border-l-yellow-500"}
              >
                <TableCell className="text-muted-foreground text-xs">{i + 1}</TableCell>
                <TableCell className="font-mono text-sm">{r.field_name}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{r.rule_type}</TableCell>
                <TableCell className="text-sm">{formatConstraint(r)}</TableCell>
                <TableCell>
                  <Badge variant={r.priority === "hard" ? "destructive" : "secondary"} className="text-xs">
                    {r.priority.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {r.source_reference || "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
