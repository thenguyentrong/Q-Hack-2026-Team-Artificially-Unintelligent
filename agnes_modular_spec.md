# Agnes PoC Modular Spec

## Objective
Build a modular decision-support system that identifies consolidation opportunities, defines requirements, finds suppliers, verifies quality via evidence, and produces explainable recommendations.

---

## Architecture Overview

- Layer 0: Consolidation Opportunity (optional)
- Layer 1: Requirements
- Layer 2: Competitor (Supplier Discovery)
- Layer 3: Quality Verification
- Layer 4: Recommendation

Each layer must be independently buildable and connected via clear JSON interfaces.

---

## Core Shared Objects

### IngredientRef
{
  "ingredient_id": "ING-ASCORBIC-ACID",
  "canonical_name": "Ascorbic Acid"
}

### SupplierRef
{
  "supplier_id": "SUP-001",
  "supplier_name": "Example Supplier"
}

### RequirementRule
{
  "requirement_id": "REQ-001",
  "field_name": "assay_percent",
  "rule_type": "range",
  "min_value": 99.0,
  "max_value": 100.5,
  "priority": "hard"
}

### EvidenceItem
{
  "evidence_id": "EVID-001",
  "source_type": "tds",
  "source_url": "https://example.com/spec.pdf"
}

---

## Layer Contracts

### Layer 0 — Consolidation (optional)
Output:
- ranked ingredients
- opportunity score
- explanation

---

### Layer 1 — Requirements
Input:
- IngredientRef

Output:
- list of RequirementRule
- split into hard / soft constraints

---

### Layer 2 — Competitor
Input:
- IngredientRef

Output:
- SupplierRef list
- lightweight evidence hints

---

### Layer 3 — Quality Verification
Input:
- suppliers + requirements

Output:
- extracted attributes
- verification results (pass/fail/unknown)
- evidence links
- confidence score

---

### Layer 4 — Recommendation
Input:
- all previous outputs

Output:
- decision (accept / reject / conditional / insufficient evidence)
- explanation
- confidence

---

## Development Rules

- Each layer must:
  - accept JSON input
  - produce JSON output
  - be runnable independently
  - support mock data

- Do not depend on internal logic of other layers
- Always expose:
  - confidence
  - evidence references
  - missing data explicitly

---

## Suggested Workflow

1. Pick ingredient (or use Layer 0)
2. Define requirements
3. Find suppliers
4. Retrieve TDS / COA
5. Extract and compare quality
6. Generate recommendation

---

## Scope Constraints

### Do
- focus on 3–4 ingredients
- use public evidence (TDS / COA)
- keep scoring explainable

### Do Not
- build full procurement system
- claim perfect quality truth
- over-generalize across all ingredients

---

## One-Line Pitch

Agnes identifies high-value consolidation targets and verifies whether alternative suppliers meet required quality standards using traceable technical evidence.
