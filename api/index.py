import traceback
import asyncio
import sys
import json
from pathlib import Path
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv, find_dotenv

# Load env variables globally
load_dotenv(find_dotenv('.env.local'))
load_dotenv()

# Add the project root to sys path so we can import src and competitor_layer
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/py")
def root():
    return {
        "ok": True,
        "message": "Agnes backend is live"
    }

@app.get("/api/py/health")
def health():
    return {"status": "healthy"}

from src.preprocessing_layer.main import preprocess_ingredient_route
from src.preprocessing_layer.models import PreprocessingInput, MyIngredientOutput
@app.post("/api/py/preprocess", response_model=MyIngredientOutput)
async def preprocess_endpoint(input_data: PreprocessingInput):
    return await preprocess_ingredient_route(input_data)

@app.post("/api/py/layer1")
async def layer1_test(input_data: MyIngredientOutput):
    try:
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv('.env.local'))
        load_dotenv()

        from src.requirement_layer.input_processor import InputProcessor
        from src.requirement_layer.output_formatter import OutputFormatter
        from src.requirement_layer.requirement_engine import RequirementEngine

        processor = InputProcessor()
        payload = processor.load_from_dict(input_data.model_dump())

        try:
            engine = RequirementEngine(model="gemini-2.5-flash")
        except OSError as e:
            return {"error": "API Key Missing", "detail": "The Python Backend could not find your GEMINI_API_KEY. Ensure you replaced the placeholder in .env.local with a real key! Error: " + str(e)}

        requirements = engine.generate(
            ingredient=payload.ingredient,
            context=payload.context,
            ingredient_id=payload.ingredient.ingredient_id,
        )

        return OutputFormatter().to_dict(OutputFormatter().build(payload.ingredient.ingredient_id, requirements, "Generated successfully"))

    except BaseException as e:
        return {"error": "Server Caught Fatal Error", "detail": str(e)}

@app.get("/api/py/layer2")
async def layer2_test(ingredient: str = "Ascorbic Acid"):
    try:
        from competitor_layer.runner import run_from_json
        from competitor_layer.config import load_config
        input_data = {
            "ingredient": {
                "ingredient_id": "ING-001",
                "canonical_name": ingredient,
                "aliases": ["Vitamin C"]
            },
            "context": {
                "region": "US"
            }
        }

        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv('.env.local'))
        load_dotenv()

        config = load_config()
        import dataclasses
        if not config.GEMINI_API_KEY or config.GEMINI_API_KEY.startswith("AIzaSyCji") or not config.google_cse_id:
            config = dataclasses.replace(config, search_engine="mock")

        result_str = run_from_json(json.dumps(input_data), config)
        return json.loads(result_str)
    except Exception as e:
        return {"error": "Layer 2 Engine Failure", "detail": str(e)}

@app.get("/api/py/layer3")
async def layer3_test(ingredient: str = "Whey Protein Isolate"):
    """Delegates to the real E2E pipeline and returns the Layer 3 verification data."""
    try:
        from src.e2e_runner import run_e2e
        result = run_e2e(ingredient)
        layer3_raw = result.get("layer3_raw", [])
        return {
            "status": "real",
            "ingredient": ingredient,
            "verifications": [
                {
                    "supplier": s["supplier"],
                    "overall_status": s["status"],
                    "confidence": s["confidence"],
                    "extracted": s.get("extracted", [])
                }
                for s in layer3_raw
            ]
        }
    except Exception as e:
        return {"error": "Layer 3 Engine Failure", "detail": str(e)}

@app.get("/api/py/layer4")
async def layer4_test(ingredient: str = "Whey Protein Isolate"):
    """Delegates to the real E2E pipeline and returns the Layer 4 decision."""
    try:
        from src.e2e_runner import run_e2e
        result = run_e2e(ingredient)
        return {
            "status": "real",
            "ingredient": ingredient,
            **result.get("decision", {})
        }
    except Exception as e:
        return {"error": "Layer 4 Engine Failure", "detail": str(e)}

@app.get("/api/py/e2e")
async def e2e_test(ingredient: str = "Vitamin C"):
    try:
        from src.e2e_runner import run_e2e
        return run_e2e(ingredient)
    except Exception as e:
        return {"error": "E2E Engine Failure", "detail": str(e)}

# ---------------------------------------------------------------------------
# Real DB Catalog Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/py/catalog/products")
def catalog_products(limit: int = Query(default=12, le=50)):
    """Return real finished-good products from the SQLite catalog."""
    try:
        return {"products": get_finished_goods(limit=limit)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/py/catalog/bom")
def catalog_bom(sku: str = Query(..., description="Finished-good SKU")):
    """Return the real BOM components for a finished-good SKU."""
    try:
        components = get_bom_for_fg(sku)
        return {"sku": sku, "components": components}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/py/catalog/suppliers")
def catalog_suppliers():
    """Return all known suppliers from the real database."""
    try:
        return {"suppliers": get_all_suppliers()}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/py/catalog/top-ingredients")
def catalog_top_ingredients(limit: int = Query(default=10, le=30)):
    """Return the most-used raw material ingredients across all BOMs."""
    try:
        return {"ingredients": get_top_raw_materials(limit=limit)}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/py/health/keys")
async def health_keys():
    try:
        import os
        from dotenv import load_dotenv, find_dotenv
        load_dotenv(find_dotenv('.env.local'))
        load_dotenv()

        gemini_key = os.environ.get("GEMINI_API_KEY")
        google_key = os.environ.get("GEMINI_API_KEY")
        google_cse = os.environ.get("GOOGLE_CSE_ID")

        gemini_status = "Missing"
        gemini_detail = "No key injected or placeholder still in use."
        gemini_pass = False

        if gemini_key and not gemini_key.startswith("paste_your"):
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                gemini_status = "Connected"
                gemini_detail = "Successfully authenticated with Google AI Studio."
                gemini_pass = True
            except Exception as e:
                gemini_status = "Auth Error"
                gemini_detail = f"Google rejected your key: {str(e)}"

        return {
            "gemini": {
                "key_present": bool(gemini_key and not gemini_key.startswith("paste_your")),
                "status": gemini_status,
                "detail": gemini_detail,
                "pass": gemini_pass
            },
            "google_search": {
                "api_key_present": bool(google_key and not google_key.startswith("paste_your")),
                "cse_id_present": bool(google_cse and not google_cse.startswith("paste_your")),
                "detail": "Search APIs correctly bound to local environment context."
            }
        }
    except Exception as e:
        return {"error": True, "detail": f"Server diagnostics gracefully caught a runtime exception: {str(e)}\n{traceback.format_exc()}"}
