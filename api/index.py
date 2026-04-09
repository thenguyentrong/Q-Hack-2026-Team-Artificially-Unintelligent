"""Agnes API — FastAPI backend with SSE pipeline streaming."""

import asyncio
import json
import logging
import sqlite3
import sys
import time
import traceback
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Add project root to sys.path
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(base_dir / "src" / "competitor_layer"))
sys.path.insert(0, str(base_dir / "src" / "quality_verification_layer"))

# Real SQLite catalog helpers
from api.catalog_db import (
    get_finished_goods,
    get_bom_for_fg,
    get_all_suppliers,
    get_suppliers_for_rm,
    get_top_raw_materials,
)

app = FastAPI(docs_url="/api/py/docs", openapi_url="/api/py/openapi.json")


@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"→ Request: {request.method} {request.url.path}")
    if request.query_params:
        logger.info(f"   Query params: {dict(request.query_params)}")

    response = await call_next(request)

    logger.info(f"← Response: {response.status_code}")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = base_dir / "data" / "db.sqlite"

logger = logging.getLogger(__name__)


def _load_env():
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(".env.local"))
    load_dotenv()
    # Also load from layer-specific .env files
    load_dotenv(base_dir / "src" / "quality_verification_layer" / ".env")
    load_dotenv(base_dir / "src" / "competitor_layer" / ".env")


# ── Health / meta endpoints ─────────────────────────────────────────────────


@app.get("/api/py")
def root():
    return {"ok": True, "message": "Agnes backend is live"}


@app.get("/api/py/health")
def health():
    return {"status": "healthy"}


@app.get("/api/py/ingredients")
def list_ingredients():
    """Return all unique ingredient slugs from the database."""
    with sqlite3.connect(str(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT DISTINCT SKU FROM Product WHERE Type = 'raw-material' ORDER BY SKU"
        ).fetchall()

    slugs: set = set()
    for row in rows:
        parts = row[0].split("-", 2)
        if len(parts) >= 3:
            ingredient_part = "-".join(parts[2].rsplit("-", 1)[:-1])
            if ingredient_part:
                slugs.add(ingredient_part)

    sorted_slugs = sorted(slugs)
    # Move niacinamide to top
    if "niacinamide" in sorted_slugs:
        sorted_slugs.remove("niacinamide")
        sorted_slugs.insert(0, "niacinamide")

    return {"ingredients": sorted_slugs}


# ── PDF proxy ───────────────────────────────────────────────────────────────


@app.get("/api/py/pdf")
async def proxy_pdf(url: str = Query(...)):
    """Proxy a PDF URL to avoid CORS issues in the browser."""
    try:
        from curl_cffi import requests as cffi_requests

        resp = cffi_requests.get(url, impersonate="chrome", timeout=20, allow_redirects=True)
        if resp.status_code >= 400:
            return {"error": f"HTTP {resp.status_code}"}

        ct = resp.headers.get("content-type", "application/pdf")
        return StreamingResponse(
            iter([resp.content]),
            media_type=ct,
            headers={"Content-Disposition": "inline"},
        )
    except Exception as e:
        return {"error": str(e)}


# ── SSE Pipeline endpoint ──────────────────────────────────────────────────


def _sse_event(event: str, data: dict) -> str:
    """Format an SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _trace(step: str, msg: str) -> str:
    return _sse_event("trace", {"step": step, "msg": msg, "ts": time.strftime("%H:%M:%S")})


def _get_db_suppliers(ingredient_slug: str):
    """Load suppliers from the database."""
    from quality_verification_layer.schemas import CandidateSupplier, SupplierRef

    qvl_path = base_dir / "src" / "quality_verification_layer"
    if str(qvl_path) not in sys.path:
        sys.path.insert(0, str(qvl_path))

    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT DISTINCT s.Id AS supplier_id, s.Name AS supplier_name
            FROM Supplier s
            JOIN Supplier_Product sp ON s.Id = sp.SupplierId
            JOIN Product p ON sp.ProductId = p.Id
            WHERE p.Type = 'raw-material' AND p.SKU LIKE ?
            ORDER BY s.Name
            """,
            (f"%{ingredient_slug}%",),
        ).fetchall()

    return [
        CandidateSupplier(
            supplier=SupplierRef(
                supplier_id=f"DB-{r['supplier_id']}",
                supplier_name=r["supplier_name"],
            ),
        )
        for r in rows
    ]


def _generate_requirements(ingredient_name: str, ingredient_slug: str):
    """Call Layer 1 to generate requirements."""
    import io

    # Ensure requirement_layer is importable
    req_path = str(base_dir / "src" / "requirement_layer")
    if req_path not in sys.path:
        sys.path.insert(0, req_path)

    from runner import run as run_layer1
    from quality_verification_layer.normalization import CANONICAL_FIELD_MAP

    input_data = {
        "ingredient": {
            "ingredient_id": f"ING-{ingredient_slug}",
            "canonical_name": ingredient_name,
            "aliases": [],
        },
        "context": {
            "end_product_category": "Food and Beverage",
            "region": "Global",
        },
    }

    # Layer 1 prints JSON to stdout — suppress the large JSON dump only
    import io as _io
    old_stdout = sys.stdout
    sys.stdout = _io.StringIO()
    try:
        result = run_layer1(input_data, model="gemini-2.5-flash")
    finally:
        sys.stdout = old_stdout

    raw_reqs = result.get("requirements", [])

    # Normalize field names through CANONICAL_FIELD_MAP
    verifiable_fields = set(CANONICAL_FIELD_MAP.values())
    requirements = []
    seen = set()

    for r in raw_reqs:
        field = r.get("field_name", "").lower().replace(" ", "_")
        canonical = CANONICAL_FIELD_MAP.get(field, field)
        if canonical not in verifiable_fields:
            continue

        key = (canonical, r.get("rule_type", ""))
        if key in seen:
            continue
        seen.add(key)

        r["field_name"] = canonical
        r["requirement_id"] = r.get("requirement_id", f"REQ-{len(requirements)+1:03d}")
        requirements.append(r)

    return requirements


def _run_pipeline_sync(ingredient_slug: str, current_step=None):
    """Run the full pipeline synchronously, yielding SSE events."""

    _load_env()

    # Ensure quality_verification_layer is importable
    qvl_path = base_dir / "src" / "quality_verification_layer"
    if str(qvl_path) not in sys.path:
        sys.path.insert(0, str(qvl_path))

    def _set_step(step: str):
        if current_step is not None:
            current_step[0] = step

    ingredient_name = ingredient_slug.replace("-", " ").title()

    # ── Layer 1: Requirements ───────────────────────────────────────────────
    _set_step("L1")
    yield _trace("L1", f"Generating requirements for {ingredient_name}...")

    try:
        requirements = _generate_requirements(ingredient_name, ingredient_slug)
        yield _trace("L1", f"Found {len(requirements)} verifiable requirements")

        hard = sum(1 for r in requirements if r.get("priority") == "hard")
        soft = len(requirements) - hard
        yield _trace("L1", f"{hard} hard, {soft} soft requirements")

        # Emit individual requirement traces with source references
        for r in requirements:
            src = r.get("source_reference", "")
            field = r.get("field_name", "")
            rule = r.get("rule_type", "")
            priority = r.get("priority", "hard").upper()
            yield _sse_event("trace", {
                "step": "L1", "ts": time.strftime("%H:%M:%S"), "live": True,
                "msg": f"[{priority}] {field} ({rule}) — source: {src}" if src else f"[{priority}] {field} ({rule})",
            })

        yield _sse_event("layer1", {"requirements": requirements})
    except Exception as e:
        yield _trace("L1", f"Error: {e}")
        yield _sse_event("layer1", {"requirements": [], "error": str(e)})
        requirements = []

    # ── Layer 2: Suppliers ──────────────────────────────────────────────────
    _set_step("L2")
    yield _trace("L2", "Looking up suppliers in database...")

    try:
        from quality_verification_layer.schemas import CandidateSupplier, SupplierRef

        db_suppliers = _get_db_suppliers(ingredient_slug)
        yield _trace("L2", f"Found {len(db_suppliers)} database suppliers")

        # Build supplier list with names
        all_suppliers = []
        names = {}
        for s in db_suppliers:
            all_suppliers.append(s)
            names[s.supplier.supplier_id] = s.supplier.supplier_name

        # Run competitor layer to discover additional suppliers
        yield _trace("L2", "Searching for additional suppliers via web...")
        try:
            from competitor_layer.runner import run_from_json as run_competitor
            from competitor_layer.config import load_config as load_competitor_config
            import dataclasses

            comp_input = {
                "ingredient": {
                    "ingredient_id": f"ING-{ingredient_slug}",
                    "canonical_name": ingredient_name,
                    "aliases": [],
                },
                "context": {"region": "US"},
            }
            comp_config = load_competitor_config()
            # Use DuckDuckGo and disable Gemini classification (too slow for live UI)
            comp_config = dataclasses.replace(
                comp_config,
                search_engine="duckduckgo",
                gemini_api_key=None,  # skip Gemini query planning + classification
                ranking_enabled=False,
            )

            comp_result = json.loads(run_competitor(json.dumps(comp_input), comp_config))
            candidates = comp_result.get("candidates", [])
            yield _trace("L2", f"Competitor layer found {len(candidates)} candidates")

            # Emit per-candidate traces with source URLs
            for c in candidates:
                cname = c.get("supplier", {}).get("supplier_name", "?")
                offers = c.get("matched_offers", [])
                urls = [o.get("source_url") for o in offers if o.get("source_url")]
                conf = c.get("candidate_confidence", "?")
                trace_data = {
                    "step": "L2", "ts": time.strftime("%H:%M:%S"), "live": True,
                    "msg": f"Found: {cname} (confidence: {conf})" + (f" — {len(urls)} source(s)" if urls else ""),
                }
                if urls:
                    trace_data["links"] = urls[:3]
                yield _sse_event("trace", trace_data)

            # Deduplicate against DB suppliers by name
            existing_names = {n.lower() for n in names.values()}
            for c in candidates:
                cname = c.get("supplier", {}).get("supplier_name", "")
                if cname.lower() in existing_names:
                    continue
                existing_names.add(cname.lower())

                sid = f"L2-{c['supplier'].get('supplier_id', cname[:8])}"
                source_urls = [
                    o.get("source_url")
                    for o in c.get("matched_offers", [])
                    if o.get("source_url")
                ]
                website = c["supplier"].get("website")

                supplier = CandidateSupplier(
                    supplier=SupplierRef(
                        supplier_id=sid,
                        supplier_name=cname,
                        country=c["supplier"].get("country"),
                        website=website,
                    ),
                    source_urls=source_urls,
                )
                all_suppliers.append(supplier)
                names[sid] = cname

        except Exception as comp_err:
            yield _trace("L2", f"Competitor layer error (continuing): {comp_err}")

        yield _trace("L2", f"Total: {len(all_suppliers)} suppliers")

        # Serialize for SSE
        suppliers_data = [
            {
                "supplier": {
                    "supplier_id": s.supplier.supplier_id,
                    "supplier_name": s.supplier.supplier_name,
                    "country": s.supplier.country,
                    "website": s.supplier.website,
                },
                "candidate_confidence": s.candidate_confidence if hasattr(s, "candidate_confidence") and s.candidate_confidence else "medium",
                "source_urls": list(s.source_urls) if s.source_urls else [],
            }
            for s in all_suppliers
        ]

        yield _sse_event("layer2", {"suppliers": suppliers_data, "names": names})
    except Exception as e:
        yield _trace("L2", f"Error: {e}")
        yield _sse_event("layer2", {"suppliers": [], "names": {}, "error": str(e)})
        all_suppliers = []
        names = {}

    if not all_suppliers or not requirements:
        yield _trace("L3", "Skipping verification — no suppliers or requirements")
        yield _sse_event("layer3", {"output": None})
        yield _sse_event("ranking", {"ranked": []})
        yield _sse_event("done", {})
        return

    # ── Layer 3: Quality Verification ───────────────────────────────────────
    _set_step("L3")
    yield _trace("L3", f"Starting quality verification for {len(all_suppliers)} suppliers...")

    try:
        from quality_verification_layer.schemas import (
            QualityVerificationInput,
            QualityVerificationOutput,
            IngredientRef,
            RequirementInput as QVLRequirement,
            RunConfig,
            SupplierAssessment,
            SupplierAssessmentStatus,
        )
        from quality_verification_layer.config import load_config
        from quality_verification_layer.runner import _verify_one_supplier
        from quality_verification_layer.gemini_wrapper import create_gemini_client

        config = load_config()
        gemini = create_gemini_client(config.gemini_api_key, config.gemini_model)

        ingredient_ref = IngredientRef(
            ingredient_id=f"ING-{ingredient_slug}",
            canonical_name=ingredient_name,
            aliases=[],
        )

        # Convert requirements dicts to Pydantic models
        qvl_reqs = []
        for r in requirements:
            try:
                qvl_reqs.append(QVLRequirement.model_validate(r))
            except Exception:
                continue

        qvl_input = QualityVerificationInput(
            ingredient=ingredient_ref,
            requirements=qvl_reqs,
            candidate_suppliers=all_suppliers,
            run_config=RunConfig(max_evidence_per_supplier=10),
        )

        # Process each supplier individually so we can stream traces
        total = len(all_suppliers)
        assessments = []
        for i, candidate in enumerate(all_suppliers, 1):
            sid = candidate.supplier.supplier_id
            name = names.get(sid, sid)
            yield _trace("L3", f"[{i}/{total}] Verifying {name}...")

            try:
                assessment = _verify_one_supplier(
                    candidate=candidate,
                    input_data=qvl_input,
                    config=config,
                    gemini_client=gemini,
                )
                # Count results for trace
                passed = sum(
                    1 for vr in assessment.verification_results
                    if (vr.status if isinstance(vr.status, str) else vr.status.value) in ("pass", "partial")
                )
                total_vr = len(assessment.verification_results)
                yield _trace("L3", f"  {name}: {passed}/{total_vr} requirements met")
            except Exception as e:
                yield _trace("L3", f"  Error for {name}: {e}")
                assessment = SupplierAssessment(
                    supplier_id=sid,
                    overall_status=SupplierAssessmentStatus.processing_error,
                    notes=[f"Processing error: {e}"],
                )
            assessments.append(assessment)

        output = QualityVerificationOutput(
            ingredient_id=qvl_input.ingredient.ingredient_id,
            supplier_assessments=assessments,
        )

        # Serialize output
        output_data = json.loads(output.model_dump_json())
        yield _sse_event("layer3", {"output": output_data})

        # ── Ranking ─────────────────────────────────────────────────────────
        _set_step("RANK")
        yield _trace("RANK", "Computing supplier rankings...")

        req_priority = {r.get("requirement_id"): r.get("priority", "hard") for r in requirements}
        # Build requirement lookup for margin scoring
        req_lookup = {r.get("requirement_id"): r for r in requirements}
        ranked = []

        def _quality_score(vr) -> float:
            """Score a single verification result from 0.0 to 1.0.

            - pass with high confidence: 1.0
            - pass with medium confidence: 0.85
            - pass with low confidence / partial: 0.65
            - For numeric pass, bonus for margin (how far inside the limit)
            - unknown: 0.0 (neutral — excluded from denominator)
            - fail: 0.0
            """
            status = vr.status if isinstance(vr.status, str) else vr.status.value
            if status == "fail":
                return 0.0
            if status == "unknown":
                return -1.0  # sentinel: excluded from scoring

            # Base score by confidence
            conf = vr.confidence if isinstance(vr.confidence, str) else vr.confidence.value
            if status == "partial":
                base = 0.65
            elif conf == "high":
                base = 1.0
            elif conf == "medium":
                base = 0.85
            else:
                base = 0.65

            # Margin bonus for numeric requirements (how far inside the limit)
            req = req_lookup.get(vr.requirement_id)
            if req and vr.observed_value is not None:
                try:
                    observed = float(vr.observed_value)
                    rule = req.get("rule_type", "")
                    if rule == "maximum" and req.get("max_value") is not None:
                        limit = float(req["max_value"])
                        if limit > 0 and observed <= limit:
                            margin = 1.0 - (observed / limit)
                            base = min(1.0, base + margin * 0.15)
                    elif rule == "minimum" and req.get("min_value") is not None:
                        limit = float(req["min_value"])
                        if limit > 0 and observed >= limit:
                            margin = (observed - limit) / limit
                            base = min(1.0, base + min(margin, 1.0) * 0.15)
                    elif rule == "range" and req.get("min_value") is not None and req.get("max_value") is not None:
                        lo, hi = float(req["min_value"]), float(req["max_value"])
                        mid = (lo + hi) / 2.0
                        span = (hi - lo) / 2.0
                        if span > 0 and lo <= observed <= hi:
                            closeness = 1.0 - abs(observed - mid) / span
                            base = min(1.0, base + closeness * 0.1)
                except (ValueError, TypeError):
                    pass

            return base

        for sa in output.supplier_assessments:
            if not sa.extracted_attributes:
                continue

            hard_scores = []
            soft_scores = []
            hard_total = hard_fail = 0
            soft_total = soft_fail = 0

            for vr in sa.verification_results:
                priority = req_priority.get(vr.requirement_id, "hard")
                qs = _quality_score(vr)
                status = vr.status if isinstance(vr.status, str) else vr.status.value

                if priority == "hard":
                    hard_total += 1
                    if qs >= 0:  # not unknown
                        hard_scores.append(qs)
                    if status == "fail":
                        hard_fail += 1
                else:
                    soft_total += 1
                    if qs >= 0:
                        soft_scores.append(qs)
                    if status == "fail":
                        soft_fail += 1

            hard_avg = sum(hard_scores) / len(hard_scores) if hard_scores else 0.0
            soft_avg = sum(soft_scores) / len(soft_scores) if soft_scores else 0.0

            # Dynamic weighting: if no soft reqs, hard = 100%. Otherwise 70/30.
            if soft_total == 0:
                total_score = hard_avg
            elif hard_total == 0:
                total_score = soft_avg
            else:
                total_score = hard_avg * 0.70 + soft_avg * 0.30

            overall_status = sa.overall_status
            status_val = overall_status if isinstance(overall_status, str) else overall_status.value

            hard_pass = sum(1 for s in hard_scores if s > 0)
            soft_pass = sum(1 for s in soft_scores if s > 0)

            ranked.append({
                "supplier_id": sa.supplier_id,
                "supplier_name": names.get(sa.supplier_id, sa.supplier_id),
                "score": round(total_score, 4),
                "hard": f"{hard_pass}/{hard_total}",
                "soft": f"{soft_pass}/{soft_total}",
                "fails": hard_fail + soft_fail,
                "unknowns": (hard_total - len(hard_scores)) + (soft_total - len(soft_scores)),
                "status": status_val,
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)

        if ranked:
            yield _trace("RANK", f"Top supplier: {ranked[0]['supplier_name']} ({ranked[0]['score']*100:.0f}%)")

        yield _sse_event("ranking", {"ranked": ranked})

    except Exception as e:
        logger.error("Pipeline error: %s", traceback.format_exc())
        yield _trace("L3", f"Error: {e}")
        yield _sse_event("layer3", {"output": None, "error": str(e)})
        yield _sse_event("ranking", {"ranked": []})

    yield _sse_event("done", {})


class _LiveTraceHandler(logging.Handler):
    """Logging handler that emits SSE trace events for live streaming."""

    # Map logger names to SSE step labels
    _LOGGER_STEP = {
        "layer1": "L1",
        "requirement_engine": "L1",
        "runner": "L1",
        "competitor_layer": "L2",
        "source_collector": "L2",
        "candidate_extractor": "L2",
        "candidate_filter": "L2",
        "query_planner": "L2",
        "quality_verification_layer": "L3",
        "retrieval": "L3",
        "extraction": "L3",
        "verification": "L3",
        "evidence_search": "L3",
        "classification": "L3",
        "normalization": "L3",
        "aggregation": "L3",
    }

    def __init__(self, loop, queue, current_step_ref):
        super().__init__()
        self._loop = loop
        self._queue = queue
        self._current_step = current_step_ref  # mutable list [step]

    # Loggers to ignore (low-level HTTP, internals)
    _IGNORE = {"httpcore", "httpx", "urllib3", "asyncio", "hpack", "h11",
               "google_genai._api_client", "filelock", "fsevents", "watchfiles"}

    def emit(self, record):
        try:
            # Skip noisy loggers
            if any(record.name.startswith(n) for n in self._IGNORE):
                return
            msg = self.format(record)
            if not msg or len(msg) < 3:
                return
            # Redact API keys from messages
            import re
            msg = re.sub(r'key=[A-Za-z0-9_-]{20,}', 'key=***', msg)
            # Determine step from logger name
            name = record.name.split(".")[-1] if record.name else ""
            step = self._LOGGER_STEP.get(name, self._current_step[0])
            # Extract URLs from message for link support
            import re
            urls = re.findall(r'https?://\S+', msg)
            event_data = {
                "step": step,
                "msg": msg,
                "ts": time.strftime("%H:%M:%S"),
                "live": True,
            }
            if urls:
                event_data["links"] = urls
            event = _sse_event("trace", event_data)
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
        except Exception:
            pass


class _PrintCapture:
    """Captures print/stdout and emits SSE trace events."""

    def __init__(self, loop, queue, current_step_ref, original_stdout):
        self._loop = loop
        self._queue = queue
        self._current_step = current_step_ref
        self._original = original_stdout

    def write(self, text):
        import re
        # Strip ANSI escape codes and whitespace
        text = re.sub(r'\033\[[0-9;]*[mKHJ]', '', text).strip()
        if not text or len(text) < 3:
            return
        text = re.sub(r'key=[A-Za-z0-9_-]{20,}', 'key=***', text)
        urls = re.findall(r'https?://\S+', text)
        event_data = {
            "step": self._current_step[0],
            "msg": text,
            "ts": time.strftime("%H:%M:%S"),
            "live": True,
        }
        if urls:
            event_data["links"] = urls
        event = _sse_event("trace", event_data)
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)

    def flush(self):
        pass


@app.get("/api/py/run")
async def run_pipeline(ingredient: str = Query("niacinamide")):
    """Run the full pipeline and stream results via SSE."""
    import threading

    loop = asyncio.get_event_loop()
    aq: asyncio.Queue = asyncio.Queue()

    def producer():
        # Track current pipeline step for print/log attribution
        current_step = ["L1"]

        # Install live trace logging handler — INFO+ only (skip TCP/TLS noise)
        handler = _LiveTraceHandler(loop, aq, current_step)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))

        root_logger = logging.getLogger()
        root_logger.addHandler(handler)

        # Capture stdout/print — this catches print() and status() calls
        original_stdout = sys.stdout
        capture = _PrintCapture(loop, aq, current_step, original_stdout)
        sys.stdout = capture

        try:
            for event in _run_pipeline_sync(ingredient, current_step):
                loop.call_soon_threadsafe(aq.put_nowait, event)
        except Exception as e:
            loop.call_soon_threadsafe(aq.put_nowait, _sse_event("error", {"msg": str(e)}))
        finally:
            root_logger.removeHandler(handler)
            sys.stdout = original_stdout
            loop.call_soon_threadsafe(aq.put_nowait, None)

    thread = threading.Thread(target=producer, daemon=True)
    thread.start()

    async def event_stream() -> AsyncGenerator[str, None]:
        while True:
            event = await aq.get()
            if event is None:
                break
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Legacy endpoints (kept for compatibility) ──────────────────────────────


@app.get("/api/py/layer1")
async def layer1_test(ingredient: str = "Ascorbic Acid"):
    try:
        _load_env()
        input_data = {
            "ingredient": {
                "ingredient_id": "ING-001",
                "canonical_name": ingredient,
                "aliases": [],
            },
            "context": {"end_product_category": "Food and Beverage", "region": "Global"},
        }
        from src.requirement_layer.input_processor import InputProcessor
        from src.requirement_layer.output_formatter import OutputFormatter
        from src.requirement_layer.requirement_engine import RequirementEngine

        processor = InputProcessor()
        payload = processor.load_from_dict(input_data)
        engine = RequirementEngine(model="gemini-2.5-flash")
        requirements = engine.generate(
            ingredient=payload.ingredient,
            context=payload.context,
            ingredient_id=payload.ingredient.ingredient_id,
        )
        return OutputFormatter().to_dict(
            OutputFormatter().build(payload.ingredient.ingredient_id, requirements, "Generated successfully")
        )
    except Exception as e:
        return {"error": str(e)}



@app.get("/api/py/layer2")
async def layer2_test(ingredient: str = "Ascorbic Acid"):
    logger.info(f"LAYER2 INPUT: ingredient={ingredient}")
    try:
        _load_env()
        from competitor_layer.runner import run_from_json
        from competitor_layer.config import load_config
        import dataclasses

        input_data = {
            "ingredient": {"ingredient_id": "ING-001", "canonical_name": ingredient, "aliases": []},
            "context": {"region": "US"},
        }
        config = load_config()
        if not config.google_api_key or not config.google_cse_id:
            config = dataclasses.replace(config, search_engine="mock")
        result_str = run_from_json(json.dumps(input_data), config)
        result = json.loads(result_str)
        logger.info(f"LAYER2 OUTPUT: {result}")
        return result
    except Exception as e:
        return {"error": str(e)}
