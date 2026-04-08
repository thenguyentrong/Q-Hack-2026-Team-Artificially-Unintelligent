Agnes PoC Modular Spec
1. Objective

Build a modular decision-support system that:

identifies promising ingredient consolidation opportunities,
defines what an acceptable substitute must satisfy,
finds alternative suppliers,
verifies supplier quality using technical evidence,
produces an explainable recommendation.

The system should be modular by design so each layer can be developed independently.

2. Design principles
2.1 Modular ownership

Each layer should be owned by one person or sub-team and be independently testable.

2.2 Loose coupling

A layer should depend only on the published interface contract of the previous layer, not on its internal implementation.

2.3 Internal freedom, external consistency

Each owner is free to choose:

models
agents
prompting strategy
parsing logic
storage approach
retrieval method

But each layer must expose the agreed input/output format.

2.4 Graceful degradation

The pipeline must still work if:

Part 1 is skipped,
evidence is incomplete,
a supplier has partial data only.
2.5 Traceability

Every downstream decision must be traceable back to:

the input ingredient,
the supplier candidate,
the extracted evidence,
the requirement that was checked.
3. System architecture
Layer 0 — Consolidation Opportunity Layer (optional)

Ranks ingredients by consolidation potential.

Layer 1 — Requirements Layer

Defines substitution requirements for a selected ingredient.

Layer 2 — Competitor Layer

Finds candidate alternative suppliers.

Layer 3 — Quality Verification Layer

Retrieves and analyzes technical evidence such as TDS and COA documents.

Layer 4 — Recommendation Layer

Combines requirements, candidate suppliers, and quality verification results into a final recommendation.

4. Ownership split
Layer 0 owner

Focus: internal data ranking and target prioritization

Layer 1 owner

Focus: requirement modeling and benchmark criteria

Layer 2 owner

Focus: supplier discovery and candidate generation

Layer 3 owner

Focus: evidence retrieval, extraction, and verification

Layer 4 owner

Focus: decision logic, explanation, and final output

5. Cross-layer shared objects

These are the core interface objects. All layers must use them.

5.1 IngredientRef

Represents the canonical ingredient being analyzed.

{
  "schema_version": "1.0",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "canonical_name": "Ascorbic Acid",
  "aliases": ["Vitamin C", "L-Ascorbic Acid"],
  "category": "food ingredient"
}
Notes
ingredient_id must be stable across layers.
If canonical normalization is not available yet, use a deterministic temporary id.
5.2 SupplierRef

Represents a supplier candidate.

{
  "supplier_id": "SUP-BASF",
  "supplier_name": "BASF",
  "country": "DE",
  "website": "https://example.com"
}
5.3 EvidenceItem

Represents a piece of evidence used later by the Quality Layer.

{
  "evidence_id": "EVID-001",
  "supplier_id": "SUP-BASF",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "source_type": "tds",
  "source_url": "https://example.com/spec.pdf",
  "title": "Ascorbic Acid Technical Data Sheet",
  "retrieved_at": "2026-04-08T10:00:00Z",
  "status": "retrieved"
}
Allowed source_type
tds
coa
product_page
certification_page
regulatory_reference
other
5.4 RequirementRule

Represents one requirement to evaluate.

{
  "requirement_id": "REQ-ASC-001",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "field_name": "assay_percent",
  "rule_type": "range",
  "operator": "between",
  "min_value": 99.0,
  "max_value": 100.5,
  "unit": "%",
  "priority": "hard",
  "source_reference": "USP",
  "notes": "Assay requirement for ascorbic acid"
}
Allowed priority
hard
soft
Allowed rule_type
range
minimum
maximum
enum_match
boolean_required
free_text_reference
5.5 ExtractedAttribute

Represents a quality field extracted from evidence.

{
  "attribute_id": "ATTR-001",
  "supplier_id": "SUP-BASF",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "field_name": "assay_percent",
  "value": 99.7,
  "unit": "%",
  "source_evidence_id": "EVID-001",
  "confidence": "high",
  "extraction_method": "document_parser"
}
Allowed confidence
high
medium
low
5.6 VerificationResult

Represents the result of comparing one extracted attribute to one requirement.

{
  "verification_id": "VER-001",
  "supplier_id": "SUP-BASF",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "requirement_id": "REQ-ASC-001",
  "field_name": "assay_percent",
  "status": "pass",
  "observed_value": 99.7,
  "unit": "%",
  "confidence": "high",
  "reason": "Assay falls within required range",
  "supporting_evidence_ids": ["EVID-001"]
}
Allowed status
pass
fail
unknown
partial
6. Layer contracts
Layer 0 — Consolidation Opportunity Layer (optional)
Purpose

Prioritize ingredients with high consolidation potential.

Input

Internal normalized data only.

Minimum input contract
{
  "schema_version": "1.0",
  "ingredients": [],
  "boms": [],
  "suppliers": [],
  "supplier_mappings": []
}

Internal shape is flexible as long as Layer 0 can produce the agreed output.

Output

A ranked list of ingredient targets.

{
  "schema_version": "1.0",
  "targets": [
    {
      "ingredient": {
        "ingredient_id": "ING-ASCORBIC-ACID",
        "canonical_name": "Ascorbic Acid",
        "aliases": ["Vitamin C"]
      },
      "opportunity_score": 0.84,
      "score_factors": {
        "company_usage": 0.9,
        "bom_frequency": 0.8,
        "supplier_fragmentation": 0.83
      },
      "reason": "Used across multiple companies and BOMs with fragmented supplier base"
    }
  ]
}
Optionality

This layer is optional.

If skipped, the user or another layer may directly provide:

a manually selected ingredient, or
a shortlist of ingredients.
Responsibility boundaries
Responsible for
ranking
prioritization
score explanation
Not responsible for
supplier discovery
quality verification
TDS / COA parsing
Layer 1 — Requirements Layer
Purpose

Define what a valid substitute must satisfy.

Inputs
one IngredientRef
optional product or category context
optional current supplier baseline
optional benchmark references
Input contract
{
  "schema_version": "1.0",
  "ingredient": {
    "ingredient_id": "ING-ASCORBIC-ACID",
    "canonical_name": "Ascorbic Acid"
  },
  "context": {
    "product_category": "beverage",
    "region": "EU"
  },
  "baseline_supplier": null
}
Output

A structured requirement spec.

{
  "schema_version": "1.0",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "requirements": [
    {
      "requirement_id": "REQ-ASC-001",
      "field_name": "assay_percent",
      "rule_type": "range",
      "operator": "between",
      "min_value": 99.0,
      "max_value": 100.5,
      "unit": "%",
      "priority": "hard",
      "source_reference": "USP"
    },
    {
      "requirement_id": "REQ-ASC-002",
      "field_name": "heavy_metals_ppm",
      "rule_type": "maximum",
      "operator": "<=",
      "max_value": 10,
      "unit": "ppm",
      "priority": "soft",
      "source_reference": "Supplier/benchmark synthesis"
    }
  ],
  "notes": "Initial PoC requirements for ascorbic acid"
}
Responsibility boundaries
Responsible for
benchmark mapping
hard vs soft requirement split
requirement schema definition
Not responsible for
finding suppliers
retrieving supplier evidence
final recommendation
Layer 2 — Competitor Layer
Purpose

Find plausible alternative suppliers for a selected ingredient.

Inputs
one IngredientRef
optional Requirements Layer output
optional search constraints
Input contract
{
  "schema_version": "1.0",
  "ingredient": {
    "ingredient_id": "ING-ASCORBIC-ACID",
    "canonical_name": "Ascorbic Acid",
    "aliases": ["Vitamin C", "L-Ascorbic Acid"]
  },
  "constraints": {
    "region": "global",
    "max_candidates": 10
  }
}
Output

A candidate supplier set.

{
  "schema_version": "1.0",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "candidates": [
    {
      "supplier": {
        "supplier_id": "SUP-BASF",
        "supplier_name": "BASF",
        "country": "DE",
        "website": "https://example.com"
      },
      "candidate_confidence": "high",
      "evidence_hints": {
        "website_found": true,
        "product_page_found": true,
        "technical_docs_likely": true
      },
      "notes": "Candidate supplier for food-grade ascorbic acid"
    }
  ]
}
Responsibility boundaries
Responsible for
supplier search
deduplication
candidate generation
lightweight evidence hints only
Not responsible for
full TDS / COA retrieval
document extraction
requirement verification
Important rule

This layer may check whether technical evidence appears likely to exist, but it should not own detailed TDS/COA processing.

Layer 3 — Quality Verification Layer
Purpose

Retrieve supplier evidence and determine whether each candidate meets the defined requirements.

Inputs
IngredientRef
candidate suppliers from Layer 2
requirements from Layer 1
Input contract
{
  "schema_version": "1.0",
  "ingredient": {
    "ingredient_id": "ING-ASCORBIC-ACID",
    "canonical_name": "Ascorbic Acid"
  },
  "requirements": [],
  "candidate_suppliers": []
}
Output

A structured assessment per supplier.

{
  "schema_version": "1.0",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "supplier_assessments": [
    {
      "supplier_id": "SUP-BASF",
      "evidence_items": [
        {
          "evidence_id": "EVID-001",
          "source_type": "tds",
          "source_url": "https://example.com/spec.pdf",
          "status": "retrieved"
        }
      ],
      "extracted_attributes": [
        {
          "field_name": "assay_percent",
          "value": 99.7,
          "unit": "%",
          "confidence": "high",
          "source_evidence_id": "EVID-001"
        }
      ],
      "verification_results": [
        {
          "requirement_id": "REQ-ASC-001",
          "field_name": "assay_percent",
          "status": "pass",
          "observed_value": 99.7,
          "unit": "%",
          "confidence": "high",
          "reason": "Within required range"
        }
      ],
      "coverage_summary": {
        "hard_requirements_passed": 3,
        "hard_requirements_failed": 0,
        "hard_requirements_unknown": 1
      },
      "overall_evidence_confidence": "medium"
    }
  ]
}
Responsibility boundaries
Responsible for
TDS / COA retrieval
evidence collection
extraction
requirement checks
evidence confidence
Not responsible for
candidate generation
business prioritization
final business recommendation
Layer 4 — Recommendation Layer
Purpose

Combine prior outputs into a usable sourcing recommendation.

Inputs
ingredient
optional opportunity score from Layer 0
requirements from Layer 1
candidate suppliers from Layer 2
supplier assessments from Layer 3
Input contract
{
  "schema_version": "1.0",
  "ingredient": {
    "ingredient_id": "ING-ASCORBIC-ACID",
    "canonical_name": "Ascorbic Acid"
  },
  "opportunity_context": null,
  "requirements": [],
  "candidate_suppliers": [],
  "supplier_assessments": []
}
Output

A final recommendation payload.

{
  "schema_version": "1.0",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "recommendations": [
    {
      "supplier_id": "SUP-BASF",
      "decision": "conditional_accept",
      "decision_confidence": "medium",
      "summary": "Supplier meets known hard constraints, but one requirement remains unverified",
      "key_reasons": [
        "Assay passes required range",
        "Technical documentation retrieved successfully",
        "One hard requirement remains unknown"
      ],
      "supporting_evidence_ids": ["EVID-001"]
    }
  ]
}
Allowed decision
accept
reject
conditional_accept
insufficient_evidence
Responsibility boundaries
Responsible for
final synthesis
decision logic
explanation
uncertainty presentation
Not responsible for
benchmark extraction
supplier search
raw evidence parsing
7. Plug-and-play development rules

To keep the work parallelizable, every layer must support the following:

7.1 Read input from file or API

Each layer should be able to consume input from:

JSON file, or
simple API endpoint
7.2 Produce JSON output

Each layer must export its output as JSON using the agreed schema.

7.3 Support mock inputs

If upstream layers are not ready, each owner should be able to use:

mock ingredient input
mock supplier lists
mock requirement sets
mock evidence items
7.4 No direct dependency on upstream codebase internals

Only depend on:

schema contract
documented fields
stable ids
8. Required integration conventions
8.1 Schema versioning

Every payload must include:

{
  "schema_version": "1.0"
}
8.2 Stable IDs

Use stable ids for:

ingredients
suppliers
requirements
evidence
verifications
8.3 Missing data handling

Missing data must not be silently dropped.

Use explicit statuses:

unknown
partial
insufficient_evidence
8.4 Confidence must be explicit

Every extraction or recommendation should expose confidence:

high
medium
low
8.5 Preserve provenance

Every verification result should be traceable to one or more evidence ids.

9. Minimum deliverable per layer

Each owner should deliver:

9.1 A README

Must explain:

what the layer does
what it expects as input
what it produces as output
how to run it with mock data
9.2 A sample input file
9.3 A sample output file
9.4 A simple runner

This can be:

CLI script
notebook
API endpoint
Streamlit action

Implementation is open.

10. Suggested division of work
Person A — Layer 0 (optional)

Builds consolidation ranking over internal data.

Person B — Layer 1

Builds requirement schema and ingredient-specific benchmarks.

Person C — Layer 2

Builds supplier discovery and candidate generation.

Person D — Layer 3

Builds TDS / COA retrieval, extraction, and verification.

Person E — Layer 4

Builds recommendation logic and explanation layer.

If fewer people are available:

combine Layer 0 + Layer 1
combine Layer 2 + Layer 3
11. Suggested first PoC flow

For the first integrated version:

manually pick one ingredient if Layer 0 is not ready,
define requirements for that ingredient,
find 3–5 supplier candidates,
retrieve evidence for those suppliers,
verify extracted quality attributes,
produce a recommendation.

This allows the whole system to work even if the optional ranking layer is unfinished.

12. Non-goals for the PoC

The team should explicitly avoid:

full regulatory automation across all regions,
universal ingredient ontology,
full procurement workflow automation,
perfect truth claims about supplier quality,
dependence on private supplier data.
13. Final summary

The architecture should be treated as:

Layer 0: Where should we look? (optional)
Layer 1: What must be true?
Layer 2: Who are the alternatives?
Layer 3: Do they actually meet the requirements?
Layer 4: What should we recommend?

That separation is strong because it lets people work independently while preserving clean interfaces for later integration.