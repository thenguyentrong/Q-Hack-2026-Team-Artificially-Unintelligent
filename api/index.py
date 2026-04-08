from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {
        "ok": True,
        "message": "Agnes backend is live"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}