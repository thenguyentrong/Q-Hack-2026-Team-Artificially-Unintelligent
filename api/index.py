import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    await asyncio.sleep(1.5)  # Simulate LLM thinking
    return {
        "ingredient": ingredient,
        "status": "success",
        "requirements": {
            "hard_constraints": [
                {"field": "Assay", "value": "≥ 99.0%"},
                {"field": "Heavy Metals", "value": "≤ 10 ppm"},
                {"field": "Moisture", "value": "≤ 1.5%"}
            ],
            "preferences": [
                {"field": "Certifications", "value": "USP/FCC grade preferred"}
            ]
        }
    }

@app.get("/api/layer2")
async def layer2_test(ingredient: str = "Ascorbic Acid"):
    await asyncio.sleep(2.0)
    return {
        "ingredient": ingredient,
        "status": "success",
        "candidates": [
            {"supplier_id": "SUP-101", "name": "GlobalChem", "evidence_hint": "TDS available"},
            {"supplier_id": "SUP-102", "name": "NaturaIng", "evidence_hint": "COA available"},
            {"supplier_id": "SUP-103", "name": "StandardPowders", "evidence_hint": "Website specs only"}
        ]
    }

@app.get("/api/layer3")
async def layer3_test():
    await asyncio.sleep(2.5)
    return {
        "status": "success",
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
        "status": "success",
        "recommendation": "Accept",
        "target_supplier": "NaturaIng",
        "explanation": "NaturaIng exceeds the 99.0% assay requirement (verified at 99.5%) and provides verifiable COA documentation.",
        "confidence": 0.92
    }