"""Core runner — orchestrates the quality verification pipeline."""

from __future__ import annotations

import logging
import time
from typing import Optional

from .aggregation import (
    compute_coverage_summary,
    compute_overall_confidence,
    compute_overall_status,
)
from .classification import classify_evidence_items
from .config import QualityVerificationConfig, load_config
from .extraction import extract_attributes_with_gemini
from .gemini_wrapper import create_gemini_client
from .id_generator import QualityIdGenerator
from .normalization import normalize_attributes, resolve_conflicts
from .retrieval import retrieve_evidence
from .schemas import (
    QualityVerificationInput,
    QualityVerificationOutput,
    SupplierAssessment,
    SupplierAssessmentStatus,
)
from .verification import verify_requirements

logger = logging.getLogger(__name__)


def run_quality_verification(
    input_data: QualityVerificationInput,
    config: QualityVerificationConfig,
) -> QualityVerificationOutput:
    """Run the full quality verification pipeline for all candidate suppliers."""
    logger.info(
        "Starting quality verification for %s (%d suppliers)",
        input_data.ingredient.ingredient_id,
        len(input_data.candidate_suppliers),
    )
    t0 = time.monotonic()

    gemini = create_gemini_client(config.gemini_api_key, config.gemini_model)

    total = len(input_data.candidate_suppliers)
    assessments = []
    for i, candidate in enumerate(input_data.candidate_suppliers, 1):
        supplier_id = candidate.supplier.supplier_id
        supplier_name = candidate.supplier.supplier_name
        logger.info("Processing supplier %s", supplier_id)
        print(
            f"  [{i}/{total}] Verifying {supplier_name} ({supplier_id})...",
            flush=True,
        )

        try:
            assessment = _verify_one_supplier(
                candidate=candidate,
                input_data=input_data,
                config=config,
                gemini_client=gemini,
            )
        except Exception as e:
            logger.error("Error processing supplier %s: %s", supplier_id, e)
            assessment = SupplierAssessment(
                supplier_id=supplier_id,
                overall_status=SupplierAssessmentStatus.processing_error,
                notes=[f"Processing error: {e}"],
            )

        assessments.append(assessment)

    elapsed = time.monotonic() - t0
    logger.info("Completed in %.1fs — %d supplier assessments", elapsed, len(assessments))

    return QualityVerificationOutput(
        ingredient_id=input_data.ingredient.ingredient_id,
        supplier_assessments=assessments,
    )


def _verify_one_supplier(candidate, input_data, config, gemini_client):
    """Run the verification pipeline for a single supplier."""
    supplier_id = candidate.supplier.supplier_id
    id_gen = QualityIdGenerator(supplier_id)

    # 1. Retrieve evidence (searches if no source_urls provided)
    evidence_items, fetched_sources = retrieve_evidence(
        candidate=candidate,
        ingredient=input_data.ingredient,
        id_gen=id_gen,
        run_config=input_data.run_config,
        fetch_timeout=config.fetch_timeout,
        search_delay=config.search_delay,
        search_results_per_query=config.search_results_per_query,
    )

    # 2. Classify sources
    evidence_items = classify_evidence_items(
        fetched_sources, evidence_items, input_data.ingredient.canonical_name
    )

    # 3. Extract attributes via Gemini
    ok_count = sum(1 for s in fetched_sources if s.ok)
    print(f"       {ok_count}/{len(fetched_sources)} sources accessible, extracting via Gemini...", flush=True)
    req_fields = [r.field_name for r in input_data.requirements]
    if gemini_client:
        attributes = extract_attributes_with_gemini(
            ingredient=input_data.ingredient.canonical_name,
            supplier=candidate.supplier.supplier_name,
            sources=fetched_sources,
            id_gen=id_gen,
            gemini_client=gemini_client,
            rate_limit_delay=config.rate_limit_delay,
            requirement_fields=req_fields,
        )
    else:
        attributes = []

    # 4. Normalize field names
    attributes = normalize_attributes(attributes, input_data.ingredient.canonical_name)

    # 5. Resolve conflicts
    attributes, conflict_notes = resolve_conflicts(attributes, evidence_items)

    # 6. Verify against requirements
    verification_results = verify_requirements(
        attributes, input_data.requirements, id_gen
    )

    # 7. Aggregate
    coverage = compute_coverage_summary(verification_results, input_data.requirements)
    overall_status = compute_overall_status(coverage, evidence_items)
    overall_confidence = compute_overall_confidence(evidence_items, attributes)

    # Build notes
    notes = list(conflict_notes)
    missing = [
        vr.field_name for vr in verification_results
        if (vr.status if isinstance(vr.status, str) else vr.status.value) in ("unknown",)
    ]
    if missing:
        notes.append(f"No values found for: {', '.join(missing)}")

    return SupplierAssessment(
        supplier_id=supplier_id,
        evidence_items=evidence_items,
        extracted_attributes=attributes,
        verification_results=verification_results,
        coverage_summary=coverage,
        overall_evidence_confidence=overall_confidence,
        overall_status=overall_status,
        notes=notes,
    )


# ── Convenience functions ────────────────────────────────────────────────────


def run_from_json(json_str: str, config: Optional[QualityVerificationConfig] = None) -> str:
    """Accept raw JSON string, return raw JSON string."""
    import json

    input_data = QualityVerificationInput.model_validate(json.loads(json_str))
    if config is None:
        config = load_config()
    output = run_quality_verification(input_data, config)
    return output.model_dump_json(indent=2)


def run_from_file(path: str, config: Optional[QualityVerificationConfig] = None) -> QualityVerificationOutput:
    """Read JSON file, return QualityVerificationOutput."""
    import json
    from pathlib import Path

    raw = Path(path).read_text()
    input_data = QualityVerificationInput.model_validate(json.loads(raw))
    if config is None:
        config = load_config()
    return run_quality_verification(input_data, config)
