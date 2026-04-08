# Layer 1 — Requirements Layer

## Purpose

Layer 1 defines **what a valid ingredient substitute must satisfy**. Given an ingredient reference and optional context (product category, region), it produces a structured set of `RequirementRule` objects sourced from industry standards such as USP, FCC, FDA, EU regulations, and Codex Alimentarius.

This layer sits between:
- **Layer 0** (optional consolidation ranking) — which identifies which ingredient to target
- **Layer 2** (supplier discovery) — which consumes Layer 1's output to find candidates

---

## Architecture

```
Input JSON
    │
    ▼
InputProcessor      ← validates, normalises aliases, applies defaults
    │
    ▼
RequirementEngine   ← LLM agent with two tools:
    ├── mcp_lookup  ← primary: queries an MCP regulatory standards server
    └── web_search  ← fallback: Tavily web search if MCP returns nothing
    │
    ▼
RuleValidator       ← validates rule logic, normalises units
    │
    ▼
IdGenerator         ← assigns stable REQ-{INGREDIENT}-{SEQ} IDs
    │
    ▼
OutputFormatter     ← serialises to Layer 1 output contract
    │
    ▼
Output JSON (consumed by Layer 2)
```

---

## Input Contract

```json
{
  "schema_version": "1.0",
  "ingredient": {
    "ingredient_id": "ING-ASCORBIC-ACID",
    "canonical_name": "Ascorbic Acid",
    "aliases": ["Vitamin C", "L-Ascorbic Acid"]
  },
  "context": {
    "product_category": "beverage",
    "region": "EU"
  },
  "baseline_supplier": null
}
```

All fields except `ingredient` are optional. When `context` is omitted the system defaults to `region: global`.

---

## Output Contract

```json
{
  "schema_version": "1.0",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "requirements": [
    {
      "requirement_id": "REQ-ASCORBIC-ACID-001",
      "field_name": "assay_percent",
      "rule_type": "range",
      "operator": "between",
      "min_value": 99.0,
      "max_value": 100.5,
      "unit": "%",
      "priority": "hard",
      "source_reference": "USP 43, EU 231/2012",
      "notes": "..."
    }
  ],
  "notes": "..."
}
```

See `sample_output.json` for a complete 12-requirement example for Ascorbic Acid.

---

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# From the repo root
uv sync

# Copy and fill in environment variables
cp src/requirement_layer/.env.example .env
# Edit .env with your API keys
```

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | Google AI Studio key – powers the Gemini agent |
| `TAVILY_API_KEY` | No | Enables web search fallback |
| `MCP_SERVER_URL` | No | URL of an MCP regulatory standards server |
| `MCP_TOOL_NAME` | No | Tool name on MCP server (default: `search`) |

---

## Running with mock data

Run from the **repo root**:

```bash
# Simple ingredient (Citric Acid, 5-8 requirements)
uv run src/requirement_layer/runner.py --input src/requirement_layer/mock_data/mock_citric_acid.json

# Complex ingredient (Ascorbic Acid, 10-15 requirements)
uv run src/requirement_layer/runner.py --input src/requirement_layer/mock_data/mock_ascorbic_acid.json --output output.json

# Edge case (Natural Vanilla Flavor, minimal numerical specs, no context)
uv run src/requirement_layer/runner.py --input src/requirement_layer/mock_data/mock_natural_vanilla_flavor.json

# Use a more capable model
uv run src/requirement_layer/runner.py --input src/requirement_layer/mock_data/mock_ascorbic_acid.json --model gemini-2.5-pro
```

The output is printed to stdout and optionally written to a file via `--output`.

---

## Mock test cases

| File | Ingredient | Pattern | Key test |
|---|---|---|---|
| `mock_citric_acid.json` | Citric Acid | 5-8 requirements | Basic ranges, maximums |
| `mock_ascorbic_acid.json` | Ascorbic Acid | 10-15 requirements | Mixed rule types, negative ranges, boolean |
| `mock_natural_vanilla_flavor.json` | Natural Vanilla Flavor | Minimal numerical | Enum match, free-text, no context |

---

## Rule types

| `rule_type` | Operator | Required fields |
|---|---|---|
| `range` | `between` | `min_value`, `max_value` |
| `minimum` | `>=` | `min_value` |
| `maximum` | `<=` | `max_value` |
| `enum_match` | `in` | `allowed_values` |
| `boolean_required` | `==` | `required` |
| `free_text_reference` | `reference` | `reference_text` |

---

## Priority classification

- **hard**: safety or regulatory (assay purity, heavy metals, microbial limits, identity tests)
- **soft**: processing or physical properties (particle size, colour, pH, solubility)

---

## Integration

Layer 2 (Supplier Discovery) should consume the output JSON directly. The `ingredient_id` and `requirement_id` values are stable across runs and serve as join keys for downstream layers.

Error responses (invalid input, missing API key) have the format:
```json
{
  "schema_version": "1.0",
  "error": "...",
  "detail": "..."
}
```

---

## Directory structure

```
layer1/
├── runner.py              ← CLI entry point
├── input_processor.py     ← input validation & normalisation
├── requirement_engine.py  ← LLM agent (MCP + web search)
├── rule_validator.py      ← rule logic validation, unit normalisation
├── id_generator.py        ← stable ID generation
├── output_formatter.py    ← output serialisation
├── schemas/
│   ├── models.py          ← Pydantic models for all contracts
│   └── __init__.py
├── mock_data/
│   ├── mock_citric_acid.json
│   ├── mock_ascorbic_acid.json
│   └── mock_natural_vanilla_flavor.json
├── sample_input.json
├── sample_output.json
├── pyproject.toml
└── .env.example
```
