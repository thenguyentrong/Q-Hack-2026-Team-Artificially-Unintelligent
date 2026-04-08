from fastapi import FastAPI

app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")

@app.get("/api")
def root():
    return {
        "ok": True,
        "message": "Agnes backend is live"
    }

@app.get("/api/health")
def health():
    return {"status": "healthy"}