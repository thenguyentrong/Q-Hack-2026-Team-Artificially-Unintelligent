"""LangGraph workflow: ingredient → supplier DB lookup → sequential per-supplier Gemini research."""
from __future__ import annotations

import json
import operator
import sys
import time
from typing import Annotated, TypedDict

from langchain_core.messages import ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from .db import get_suppliers_for_ingredient
from .models import QualityProperties, SupplierResult, VerificationResult
from .verify import verify_supplier_result

# Seconds to wait between Gemini calls to stay within free-tier rate limits
_RATE_LIMIT_DELAY = 10
# Max retries on 429 errors
_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# State definitions
# ---------------------------------------------------------------------------

class OverallState(TypedDict):
    ingredient_name: str
    suppliers: list[dict]
    # Index of the next supplier to process (sequential loop)
    supplier_idx: int
    results: Annotated[list[SupplierResult], operator.add]
    # Agent 2 – verification
    verify_idx: int
    verifications: Annotated[list[VerificationResult], operator.add]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_urls_from_messages(messages: list) -> list[str]:
    """Pull Tavily result URLs out of the agent's message history."""
    urls: list[str] = []
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        try:
            items = json.loads(msg.content) if isinstance(msg.content, str) else msg.content
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])
        except (json.JSONDecodeError, TypeError):
            pass
    return list(dict.fromkeys(urls))  # deduplicate, preserve order


def _parse_retry_delay(err_str: str) -> float:
    """Extract the suggested retry delay (seconds) from a 429 error message."""
    import re
    m = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str)
    if m:
        return float(m.group(1)) + 5  # add 5s buffer
    return _RATE_LIMIT_DELAY


def _call_with_retry(fn, *args, **kwargs):
    """Call fn with backoff on 429 / RESOURCE_EXHAUSTED, honouring the API's retry-after hint."""
    for attempt in range(_MAX_RETRIES + 1):  # +1 so last iteration still retries
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if attempt == _MAX_RETRIES:
                    raise  # exhausted retries
                wait = max(_parse_retry_delay(err_str), _RATE_LIMIT_DELAY * (2 ** attempt))
                print(
                    f"  Rate limited (attempt {attempt + 1}/{_MAX_RETRIES}), waiting {wait:.0f}s...",
                    file=sys.stderr, flush=True,
                )
                time.sleep(wait)
            else:
                raise


def _build_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model="gemma-4-31b-it", temperature=0)

#"gemini-2.5-flash"
# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def query_db(state: OverallState) -> dict:
    """Node 1 – query SQLite for suppliers of the given ingredient."""
    suppliers = get_suppliers_for_ingredient(state["ingredient_name"])
    return {"suppliers": suppliers, "supplier_idx": 0}


def check_done(state: OverallState) -> str:
    """Conditional edge – loop or end."""
    if state["supplier_idx"] >= len(state["suppliers"]):
        return "done"
    return "continue"


def research_supplier(state: OverallState) -> dict:
    """Node 2 – run a Gemini ReAct agent to find product specs for ONE supplier, then advance index."""
    idx = state["supplier_idx"]
    s = state["suppliers"][idx]
    ingredient = state["ingredient_name"]
    supplier = s["supplier_name"]

    print(f"\n[{idx + 1}/{len(state['suppliers'])}] Researching {supplier}...", file=sys.stderr, flush=True)

    search_tool = TavilySearchResults(max_results=4)
    agent = create_react_agent(_build_llm(), [search_tool])

    prompt = f"""You are a procurement research assistant for a CPG supply chain AI called Agnes.

Your task: find quality and compliance information for the ingredient **'{ingredient}'** as sold by **'{supplier}'**.

Search for:
1. The supplier's product page for this ingredient
2. Technical Data Sheet (TDS) or specification sheet
3. Certificate of Analysis (COA) template
4. Safety Data Sheet (SDS / MSDS)
5. Quality certifications (USP, NSF, FCC, Kosher, Halal, Non-GMO, Organic, etc.)
6. Purity/assay spec, physical form (powder/granule/liquid), grade

Search queries to use:
- "{supplier} {ingredient} product specification"
- "{supplier} {ingredient} TDS COA SDS"
- "{supplier} {ingredient} product specification"
- "{supplier} {ingredient} TDS COA SDS"
- "{supplier} {ingredient} filetype:pdf TDS"
- "{supplier} {ingredient} technical data sheet download"
- "{supplier} {ingredient} specification sheet pdf"
- "{supplier} {ingredient} certificate of analysis download"

After searching, report:
- All relevant URLs you found
- Key quality properties (purity, grade, certifications, form, particle size, origin)
- Any compliance or regulatory notes
"""

    # Run agent with retry
    time.sleep(_RATE_LIMIT_DELAY)  # Proactive delay to avoid 429
    response = _call_with_retry(agent.invoke, {"messages": [("human", prompt)]})
    last_content = response["messages"][-1].content
    # gemini-2.5-flash may return content as a list of parts; flatten to string
    if isinstance(last_content, list):
        raw_findings = " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p)
            for p in last_content
        ).strip()
    else:
        raw_findings = str(last_content)
    search_urls = _extract_urls_from_messages(response["messages"])

    # Structured extraction pass (with retry + delay)
    time.sleep(_RATE_LIMIT_DELAY)
    extractor = _build_llm().with_structured_output(QualityProperties)
    quality: QualityProperties = _call_with_retry(
        extractor.invoke,
        f"""Extract structured quality properties from this research about '{ingredient}' from '{supplier}'.
Use null for any field you cannot confidently determine from the text below.

--- RESEARCH FINDINGS ---
{raw_findings}
""",
    )

    result = SupplierResult(
        supplier_id=s["supplier_id"],
        supplier_name=supplier,
        skus=s["skus"],
        ingredient=ingredient,
        quality_properties=quality,
        raw_findings=raw_findings,
        search_urls=search_urls,
    )

    return {"results": [result], "supplier_idx": idx + 1}


# ---------------------------------------------------------------------------
# Agent 2 – verification nodes
# ---------------------------------------------------------------------------

def start_verification(state: OverallState) -> dict:
    """Transition node: reset verify_idx to 0 before the verification loop."""
    return {"verify_idx": 0}


def check_verify_done(state: OverallState) -> str:
    """Conditional edge – loop through results for verification or end."""
    if state["verify_idx"] >= len(state["results"]):
        return "done"
    return "continue"


def verify_supplier(state: OverallState) -> dict:
    """Node 3 – run quality verification for ONE supplier result."""
    idx = state["verify_idx"]
    result = state["results"][idx]
    total = len(state["results"])

    print(
        f"\n[Verify {idx + 1}/{total}] Verifying {result.supplier_name}...",
        file=sys.stderr, flush=True,
    )

    verification = verify_supplier_result(
        result,
        call_with_retry=_call_with_retry,
        build_llm=_build_llm,
        rate_limit_delay=_RATE_LIMIT_DELAY,
    )

    passed = sum(1 for c in verification.comparison if c.verdict == "pass")
    failed = sum(1 for c in verification.comparison if c.verdict == "fail")
    missing = sum(1 for c in verification.comparison if c.verdict == "missing")
    print(
        f"  Results: {passed} pass, {failed} fail, {missing} missing "
        f"| evidence: {verification.evidence_quality} "
        f"| confidence: {verification.confidence_score}",
        file=sys.stderr, flush=True,
    )

    return {"verifications": [verification], "verify_idx": idx + 1}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph():
    g = StateGraph(OverallState)

    # Agent 1 nodes
    g.add_node("query_db", query_db)
    g.add_node("research_supplier", research_supplier)

    # Agent 2 nodes
    g.add_node("start_verification", start_verification)
    g.add_node("verify_supplier", verify_supplier)

    # Agent 1 flow: query → research loop
    g.add_edge(START, "query_db")
    g.add_conditional_edges(
        "query_db",
        lambda state: "done" if not state["suppliers"] else "continue",
        {"continue": "research_supplier", "done": END},
    )
    g.add_conditional_edges(
        "research_supplier",
        check_done,
        {"continue": "research_supplier", "done": "start_verification"},
    )

    # Agent 2 flow: verification loop
    g.add_conditional_edges(
        "start_verification",
        check_verify_done,
        {"continue": "verify_supplier", "done": END},
    )
    g.add_conditional_edges(
        "verify_supplier",
        check_verify_done,
        {"continue": "verify_supplier", "done": END},
    )

    return g.compile()
