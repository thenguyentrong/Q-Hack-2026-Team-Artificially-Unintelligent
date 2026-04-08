# Agnes Competitor Layer Spec

**Version:** 1.0  
**Status:** Ready for implementation  
**Scope:** Competitor Layer only  
**Last updated:** 2026-04-08

---

## 1. Purpose

The Competitor Layer identifies **plausible alternative suppliers** for a selected ingredient and returns a **clean candidate set** for the Quality Layer.

It is intentionally designed as **semi-filtered discovery**:

- broader than strict verification,
- narrower than raw web search,
- focused on generating candidates that are relevant enough to be worth technical verification later.

This layer is not responsible for proving compliance or parsing technical specs in depth.

---

## 2. What this layer must answer

> Given an ingredient, which supplier candidates are plausible alternatives worth sending to the Quality Layer?

---

## 3. Final design decisions

These decisions are locked for this spec.

### 3.1 Responsibility model
The Competitor Layer uses **semi-filtered discovery**.

It should:
- find plausible suppliers,
- remove obviously irrelevant ones,
- return evidence hints and source URLs,
- optionally rank candidates if this stays simple.

It should not:
- perform deep TDS/COA extraction,
- verify technical compliance,
- make the final sourcing recommendation.

### 3.2 Input scope
The layer accepts:

- `IngredientRef`
- aliases
- category
- optional Layer 1 context
- optional region constraint

Layer 1 input is **optional**, but supported.

### 3.3 Competitor definition
A competitor is:

> a supplier offering the same ingredient or an equivalent ingredient in a relevant use context.

This excludes obviously irrelevant results such as unrelated industries or mismatched use contexts.

### 3.4 Output richness
The layer returns:

- supplier candidates
- source URLs found
- lightweight evidence hints

### 3.5 Ranking behavior
Preferred behavior:
- return ranked candidates with simple confidence and reasoning

Fallback behavior:
- if ranking adds too much complexity, return an unranked clean candidate list

### 3.6 Stopping rule
Preferred behavior:
- return top N candidates above a minimum threshold

Fallback behavior:
- return a fixed top N

### 3.7 Supplier types
Include:
- manufacturers
- distributors / resellers

But label supplier type explicitly.

### 3.8 Deduplication strategy
Internally, the layer may operate at the **product-offer level**, but the final output should roll up to **one supplier-level entry** where possible.

### 3.9 Minimum evidence hint set
Use the following minimum evidence hints:

- `website_found`
- `product_page_found`
- `pdf_found`
- `technical_doc_likely`

### 3.10 Synonym handling
Use:
- upstream aliases if present
- light internal synonym expansion

Do not build a full ontology inside this layer.

### 3.11 Geography handling
If region is provided, use it.  
If not, remain global.

### 3.12 Empty-result policy
Do not hard-fail unless absolutely necessary.

Return best-effort output with explicit uncertainty:
- low confidence,
- weak evidence,
- or empty candidates if nothing usable exists.

---

## 4. Non-goals

This layer must **not**:

- parse and extract TDS or COA fields in detail
- verify USP / FCC / Ph. Eur. requirements
- score regulatory compliance
- decide accept / reject / conditional accept
- optimize cost or consolidation
- build a universal supplier knowledge graph

Those responsibilities belong downstream.

---

## 5. Recommended technical approach

## 5.1 Agent shape

Implement this layer as a **single Competitor Agent** with a small supporting tool stack.

The agent should orchestrate:

1. query expansion
2. supplier search
3. source collection
4. candidate normalization
5. lightweight filtering
6. optional ranking
7. JSON output generation

This should be implemented as a normal application module first, not as an MCP server first.

---

## 5.2 Gemini model recommendation

### Default model
Use **`gemini-3.1-pro-preview`** as the default reasoning model for this layer.

Why:
- Google describes Gemini 3 as its **most intelligent model family to date**, designed for **agentic workflows**, **autonomous coding**, and **complex multimodal tasks**.
- The Gemini 3 guide states that **Gemini 3.1 Pro** is best for **complex tasks that require broad world knowledge and advanced reasoning across modalities**.

This makes it the best default for supplier discovery, candidate reasoning, synonym expansion, and evidence-hint generation.

### Stable fallback
Use **`gemini-2.5-pro`** as the stable fallback model.

Why:
- Google describes Gemini 2.5 Pro as **its most advanced model for complex tasks**, with **deep reasoning and coding capabilities**.
- It is the safer fallback if you want to reduce preview-model risk.

### Optional auxiliary model
If the implementation needs embeddings for deduplication or semantic clustering, optionally use:
- `gemini-embedding-2-preview`

This is optional, not required for the first implementation.

---

## 5.3 API style recommendation

Preferred:
- Google GenAI SDK
- structured outputs / JSON schema enforcement
- function-calling for tools

### Why
This layer naturally benefits from:
- tool-driven web/source collection
- typed JSON output
- deterministic contracts between layers

---

## 5.4 MCP recommendation

### Recommendation
Do **not** start by building this layer as an MCP server.

Build the core module first.

### Why
An MCP wrapper is only useful after:
- the input/output schema is stable,
- the core logic works,
- the JSON contract is tested.

### When MCP becomes useful
Build an MCP server **only if** one of these is true:

- multiple other agents/tools need to call this layer as a shared tool
- you want the Competitor Layer to be reusable from IDE agents, orchestration tools, or external layer runners
- the team wants protocol-level modularity instead of direct Python imports or HTTP endpoints

### Decision for this spec
MCP is **optional** and should be added only in a later phase.

---

## 6. Functional requirements

## 6.1 Required inputs

### Minimum input
```json
{
  "schema_version": "1.0",
  "ingredient": {
    "ingredient_id": "ING-ASCORBIC-ACID",
    "canonical_name": "Ascorbic Acid",
    "aliases": ["Vitamin C", "L-Ascorbic Acid"],
    "category": "food ingredient"
  }
}
```

### Supported optional input
```json
{
  "schema_version": "1.0",
  "ingredient": {
    "ingredient_id": "ING-ASCORBIC-ACID",
    "canonical_name": "Ascorbic Acid",
    "aliases": ["Vitamin C", "L-Ascorbic Acid"],
    "category": "food ingredient"
  },
  "context": {
    "region": "EU",
    "product_category": "beverage",
    "grade_hint": "food-grade"
  },
  "requirements_context": {
    "required_grade": "food",
    "notes": "Prefer food-relevant suppliers"
  },
  "runtime": {
    "max_candidates": 10,
    "ranking_enabled": true
  }
}
```

---

## 6.2 Required outputs

### Output contract
```json
{
  "schema_version": "1.0",
  "ingredient_id": "ING-ASCORBIC-ACID",
  "search_summary": {
    "queries_used": [
      "ascorbic acid food grade supplier",
      "vitamin c supplier technical data sheet"
    ],
    "region_applied": "EU",
    "ranking_enabled": true
  },
  "candidates": [
    {
      "supplier": {
        "supplier_id": "SUP-001",
        "supplier_name": "Example Supplier",
        "supplier_type": "manufacturer",
        "country": "DE",
        "website": "https://example.com"
      },
      "matched_offers": [
        {
          "offer_label": "Ascorbic Acid Food Grade",
          "matched_name": "L-Ascorbic Acid",
          "source_url": "https://example.com/product/ascorbic-acid"
        }
      ],
      "evidence_hints": {
        "website_found": true,
        "product_page_found": true,
        "pdf_found": true,
        "technical_doc_likely": true
      },
      "candidate_confidence": "high",
      "rank": 1,
      "reason": "Strong ingredient match, food-grade context match, and technical documentation likely"
    }
  ],
  "warnings": [],
  "stats": {
    "raw_results_seen": 42,
    "deduped_suppliers": 8,
    "returned_candidates": 5
  }
}
```

### Allowed `supplier_type`
- `manufacturer`
- `distributor`
- `reseller`
- `unknown`

### Allowed `candidate_confidence`
- `high`
- `medium`
- `low`

---

## 6.3 Minimum behavior requirements

The Competitor Layer must:

1. expand ingredient search terms using aliases and light synonym expansion
2. search for plausible suppliers
3. collect source URLs
4. classify supplier type if possible
5. deduplicate results
6. remove obviously irrelevant results
7. attach minimum evidence hints
8. return explicit confidence
9. preserve reasoning in a short explanation field
10. produce valid JSON conforming to the contract

---

## 7. Suggested internal architecture

This section defines recommended components. Internal implementation choices remain flexible.

## 7.1 Core modules

### A. Input Normalizer
Purpose:
- validate input JSON
- normalize aliases
- normalize category and region
- construct search plan

### B. Query Planner
Purpose:
- generate search queries from ingredient, aliases, category, region, and optional context

Example query families:
- ingredient + supplier
- ingredient + manufacturer
- ingredient + distributor
- ingredient + product page
- ingredient + PDF / spec terms
- ingredient + use-context term, e.g. food grade

### C. Source Discovery Adapter
Purpose:
- run search and collect initial URLs
- fetch candidate pages / snippets if needed

Implementation is flexible:
- web search API
- HTTP fetch + search engine wrapper
- manual supplier seed list + web enrichment

### D. Candidate Extractor
Purpose:
- infer supplier candidates from discovered pages
- distinguish supplier from random mentions
- attach matched offer labels and source URLs

### E. Candidate Normalizer / Deduper
Purpose:
- merge duplicate supplier mentions
- roll multiple offers into one supplier-level result
- normalize supplier name variants

### F. Light Filter
Purpose:
- remove obviously irrelevant results

Examples:
- wrong ingredient
- wrong use context
- irrelevant domain type
- no credible supplier signal at all

### G. Ranker (optional but preferred)
Purpose:
- assign a simple rank or confidence score

### H. Output Formatter
Purpose:
- generate final JSON contract
- include warnings and stats

---

## 8. Ranking and filtering logic

## 8.1 Keep ranking simple

Only rank if this can be implemented without major complexity.

Suggested simple score:

```text
candidate_score =
0.40 * ingredient_match
+ 0.25 * use_context_match
+ 0.20 * evidence_hint_strength
+ 0.15 * source_quality
```

Where:
- `ingredient_match` = exact / alias / weak semantic match
- `use_context_match` = food-grade / product-category relevance
- `evidence_hint_strength` = product page, PDF, technical doc likely
- `source_quality` = manufacturer page stronger than random reseller listing

If this is too much effort, skip the score and return a clean candidate list with confidence only.

---

## 8.2 Lightweight filtering rules

The filter should remove only clearly weak results.

### Remove if:
- ingredient match is clearly wrong
- supplier is not actually a seller/manufacturer/distributor
- result is only a forum mention or unrelated article
- result has no supplier signal and no product signal

### Keep if:
- ingredient match is plausible
- supplier role is plausible
- at least one source URL supports the result
- evidence is partial but potentially useful

Do not over-filter.

---

## 9. Interface boundaries with other layers

## 9.1 Upstream dependency
This layer depends on:
- ingredient identity
- aliases
- category
- optional requirements context

It must **not** depend on the internal logic of Layer 1.

### Rule
Consume Layer 1 only through explicit JSON fields, never through shared internal code assumptions.

---

## 9.2 Downstream contract to Quality Layer
The Quality Layer should be able to consume Competitor Layer output directly.

Therefore each candidate must expose:

- stable supplier identity
- source URLs
- matched offer labels
- evidence hints
- confidence
- reason

This is enough for the Quality Layer to decide which candidates to investigate first.

---

## 10. Error handling and uncertainty

The layer must never silently swallow uncertainty.

### Required warning patterns
Examples:
- `"No region supplied; search remained global"`
- `"Ranking disabled; output is unranked"`
- `"Candidate confidence low due to weak evidence"`
- `"No product pages found for 3 of 5 candidates"`

### Failure policy
If search succeeds but evidence is weak:
- return candidates with low confidence

If search fails completely:
- return empty candidates plus warnings

---

## 11. Implementation phases

Each phase should be small enough for a coding agent to complete and test.

---

## Phase 1 — Contract-first skeleton

### Goal
Create the core package, schema contracts, mock runner, and deterministic output format.

### Deliverables
- module scaffold
- input schema
- output schema
- example input files
- example output files
- basic CLI entrypoint
- config file support for Gemini API key and model name

### Recommended files
```text
competitor_layer/
  README.md
  pyproject.toml
  competitor_layer/
    __init__.py
    config.py
    schemas.py
    models.py
    runner.py
    cli.py
  tests/
    test_schemas.py
    test_mock_runner.py
  examples/
    input_ascorbic_acid.json
    output_mock.json
```

### Tests
- schema validation test
- CLI smoke test
- mock input -> valid JSON output test

### Exit criteria
A valid JSON output can be produced from mock input without external search.

---

## Phase 2 — Query planning and search integration

### Goal
Generate search queries and collect raw discovery results.

### Deliverables
- query planner
- simple search adapter
- source collection logic
- trace of queries used

### Tests
- alias expansion test
- region-aware query generation test
- search adapter response normalization test
- regression test for known ingredient inputs

### Exit criteria
Given an ingredient, the layer can produce a list of raw candidate pages / URLs.

---

## Phase 3 — Candidate extraction and normalization

### Goal
Turn raw search results into normalized supplier candidates.

### Deliverables
- supplier extraction logic
- supplier name normalization
- product-offer grouping
- supplier roll-up

### Tests
- duplicate supplier merge test
- manufacturer vs distributor labeling test
- matched-offer roll-up test
- incorrect-domain rejection test

### Exit criteria
The layer produces supplier-level candidate objects from noisy raw results.

---

## Phase 4 — Light filtering, evidence hints, and confidence

### Goal
Add pragmatic filtering and lightweight evidence evaluation.

### Deliverables
- filter rules
- evidence hint detection
- confidence labels
- optional rank assignment

### Tests
- irrelevant result removal test
- evidence hint population test
- confidence labeling test
- fixed-top-N / threshold behavior test

### Exit criteria
The layer returns a clean candidate list with evidence hints and confidence.

---

## Phase 5 — Gemini agent orchestration

### Goal
Use Gemini for reasoning-heavy parts while preserving structured output.

### Recommended uses of Gemini
- synonym/query expansion
- supplier candidate reasoning
- ambiguous result classification
- concise candidate reasoning strings

### Deliverables
- Gemini client wrapper
- prompt templates
- structured output enforcement
- retry handling
- model configuration
- fallback model logic

### Tests
- prompt-to-JSON conformance test
- malformed model output recovery test
- fallback-to-stable-model test
- deterministic snapshot test for a fixture input

### Exit criteria
The layer can run end-to-end with Gemini-backed reasoning and valid structured output.

---

## Phase 6 — Integration hardening

### Goal
Make the layer easy to plug into the rest of the system.

### Deliverables
- stable JSON versioning
- logging and trace ids
- clean runner API
- example integration with Layer 3 mock consumer

### Tests
- contract compatibility test with a mock Quality Layer consumer
- backward compatibility test for output schema
- warning propagation test

### Exit criteria
The output is stable enough for team integration.

---

## Phase 7 — Optional MCP server

### Goal
Expose the Competitor Layer as a tool callable by other agents.

### Recommendation
Only do this after Phase 6 is stable.

### Suggested MCP tools
- `find_competitors`
- `get_competitor_layer_schema`
- `health_check`

### Deliverables
- MCP server wrapper around the core module
- tool schemas
- local run instructions

### Tests
- MCP startup test
- tool-call contract test
- end-to-end `find_competitors` test with fixture input

### Exit criteria
External agents can call the Competitor Layer through MCP without knowing internal code.

---

## 12. Testing strategy

## 12.1 General principle
Every phase must end with:
- unit tests,
- one happy-path integration test,
- one failure or uncertainty-path test.

## 12.2 Fixture strategy
Create stable fixtures for:
- Ascorbic Acid
- Citric Acid
- Xanthan Gum

Use them throughout development.

## 12.3 Golden output snapshots
For at least one fixture, keep a golden JSON output snapshot to detect accidental contract drift.

---

## 13. Recommended tech stack

## 13.1 Language
Python

## 13.2 Packaging
- `pyproject.toml`
- typed dataclasses or Pydantic models

## 13.3 Gemini client
Google GenAI SDK

## 13.4 Config
Environment variables:
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `COMPETITOR_MAX_CANDIDATES`
- `COMPETITOR_RANKING_ENABLED`

## 13.5 Validation
Pydantic or equivalent schema validation

---

## 14. Prompting and output discipline

The Gemini-powered parts should be constrained to produce:

- typed JSON
- concise reasons
- no markdown
- no free-form essays

### Recommended pattern
Use Gemini only for reasoning-heavy intermediate steps, then validate and normalize everything in code.

Do not rely on raw model prose as the system contract.

---

## 15. Minimal acceptance criteria

The Competitor Layer is considered done when it can:

1. accept a canonical ingredient input with aliases
2. search and discover plausible supplier candidates
3. deduplicate and normalize them
4. attach source URLs and minimum evidence hints
5. return confidence and short reasons
6. export valid JSON
7. pass contract tests
8. be callable independently of the rest of the pipeline

---

## 16. Nice-to-have features

Only after the core layer works:

- optional embedding-based deduplication
- cached supplier memory
- domain reputation heuristics
- seed-list support for known suppliers
- MCP server wrapper
- small UI/debug page for query traces

---

## 17. Source notes for implementation decisions

These are the main external references behind the Gemini-specific recommendations in this spec:

- Google describes Gemini 3 as its most intelligent model family, designed for agentic workflows, autonomous coding, and complex multimodal tasks.
- Google describes Gemini 3.1 Pro as best for complex tasks requiring broad world knowledge and advanced reasoning.
- Google describes Gemini 2.5 Pro as its most advanced model for complex tasks, with deep reasoning and coding capabilities.
- Google recommends structured outputs for predictable, type-safe JSON.
- Google recommends function calling for connecting models to tools and APIs.
- Google documents the Interactions API as a unified interface for Gemini models and agents, but notes it is still Beta and subject to breaking changes.
- Google recommends using the Gemini Docs MCP for coding assistants to stay current with Gemini API changes; that recommendation supports using MCP for development workflows, but does not by itself justify making the Competitor Layer an MCP server from day one.

Suggested implementation reference pages:
- Gemini 3 guide
- Gemini models page
- Structured outputs guide
- Function calling guide
- Interactions API guide
- Gemini coding assistants / MCP guide
