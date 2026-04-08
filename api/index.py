import asyncio
import sys
import json
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the project root to sys path so we can import src and competitor_layer
base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir))
sys.path.insert(0, str(base_dir / "competitor_layer"))

app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api")
def root():
    return {
        "ok": True,
        "message": "Agnes backend is live"
    }

@app.get("/api/health")
def health():
    return {"status": "healthy"}

@app.get("/api/layer1")
async def layer1_test(ingredient: str = "Ascorbic Acid"):
    try:
        from src.requirement_layer.runner import run as run_requirement_layer
        input_data = {
            "ingredient": {
                "ingredient_id": "ING-001",
                "canonical_name": ingredient,
                "aliases": ["Vitamin C"]
            },
            "context": {
                "end_product_category": "Food and Beverage",
                "region": "Global"
            }
        }
        result = run_requirement_layer(input_data)
        return result
    except BaseException as e:
        return {"error": "Layer 1 Engine Failure", "detail": str(e), "note": "If you see a SystemExit, Vercel is missing your GEMINI_API_KEY environment variable."}

@app.get("/api/layer2")
async def layer2_test(ingredient: str = "Ascorbic Acid"):
    try:
        from competitor_layer.competitor_layer.runner import run_from_json
        from competitor_layer.competitor_layer.config import load_config
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
        
        # Load environment config
        config = load_config()
        # Fallback to mock search if APIs aren't fully configured in the environment
        if not config.tavily_api_key and not config.exa_api_key:
             config.search_engine = "mock"
             
        result_str = run_from_json(json.dumps(input_data), config)
        return json.loads(result_str)
    except Exception as e:
        return {"error": "Layer 2 Engine Failure", "detail": str(e)}

@app.get("/api/layer3")
async def layer3_test():
    await asyncio.sleep(2.5)
    return {
        "status": "simulated",
        "verifications": [
            {"supplier": "GlobalChem", "assay_extracted": "99.2%", "pass": True, "confidence": 0.95},
            {"supplier": "NaturaIng", "assay_extracted": "99.5%", "pass": True, "confidence": 0.98},
            {"supplier": "StandardPowders", "assay_extracted": "Unknown", "pass": False, "confidence": 0.40}
        ]
    }

@app.get("/api/layer4")
async def layer4_test():
    await asyncio.sleep(1.0)
    return {
        "status": "simulated",
        "recommendation": "Accept",
        "target_supplier": "NaturaIng",
        "explanation": "NaturaIng exceeds the 99.0% assay requirement (verified at 99.5%) and provides verifiable COA documentation.",
        "confidence": 0.92
    }