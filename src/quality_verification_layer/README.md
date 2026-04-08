# Agnes Quality Verification Layer

Evidence-based supplier quality verification for CPG ingredient sourcing. Given an ingredient, requirements, and candidate suppliers, this layer retrieves technical evidence, extracts quality attributes, and verifies them against requirement rules — returning traceable pass/fail/unknown results with explicit confidence.

Part of the Agnes decision-support system (Layer 3). See [`quality_verification_layer_spec.md`](../../quality_verification_layer_spec.md) for the full specification.

## Install

```bash
pip install -e .
```

## Configure

```bash
cp .env.example .env
# Set GEMINI_API_KEY for Gemini-powered field extraction
```

## Usage

```bash
quality-verification inputs/sample_input.json
quality-verification inputs/sample_input.json -o outputs/result.json
```

### Programmatic

```python
from quality_verification_layer import run_quality_verification, QualityVerificationInput
from quality_verification_layer.config import load_config

input_data = QualityVerificationInput.model_validate(json_dict)
config = load_config()
output = run_quality_verification(input_data, config)
```

## Input Schema

```json
{
  "schema_version": "1.0",
  "ingredient": { "ingredient_id", "canonical_name", "aliases", "category" },
  "requirements": [{ "requirement_id", "field_name", "rule_type", "operator", "min_value", "max_value", "unit", "priority" }],
  "candidate_suppliers": [{ "supplier": { "supplier_id", "supplier_name" }, "source_urls": [...] }]
}
```

## Output Schema

Each supplier gets a `SupplierAssessment` with:
- `evidence_items[]` — what was retrieved, with source type and status
- `extracted_attributes[]` — structured values extracted from evidence
- `verification_results[]` — pass/fail/unknown per requirement, with reasons
- `coverage_summary` — counts of hard/soft pass/fail/unknown
- `overall_status` — verified, verified_with_gaps, failed_hard_requirements, insufficient_evidence
- `overall_evidence_confidence` — high, medium, low

## Supported Fields

assay_percent, loss_on_drying_percent, heavy_metals_ppm, lead_ppm, arsenic_ppm, particle_size_mesh, pH, shelf_life_months, grade_claims, certifications, appearance, micro_limits

## Supported Rule Types

range, minimum, maximum, enum_match, boolean_required, free_text_reference

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## Known Limitations

- Supports 3-4 ingredient families
- Limited to public documents (TDS, COA, product pages)
- Heuristic confidence scoring
- Gemini required for field extraction (no extraction without API key)
- Limited conflict resolution across sources
