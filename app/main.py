"""
Magic Apron — FastAPI backend that calls Vertex AI Search (grounded RAG).

GCP ↔ AWS:
----------
• This app is the orchestration layer (like a small Lambda + API Gateway or ECS task).
  We run it on Cloud Run = AWS Fargate / Lambda for containers: fully managed,
  auto-scaling, pay-per-request. Cloud Run gives built-in logging and metrics
  (like CloudWatch for Lambda/ECS).
"""

import os
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Run from project root: python -m app.main (or uvicorn app.main:app)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Load .env from project root so MAGIC_APRON_* and GOOGLE_CLOUD_PROJECT are set
try:
    from dotenv import load_dotenv
    load_dotenv(str(Path(ROOT) / ".env"))
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from scripts.search_magic_apron import search_magic_apron


def _json_error(status_code: int, detail: str):
    return JSONResponse(status_code=status_code, content={"detail": detail})

STATIC_DIR = Path(ROOT) / "static"

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    summary_text: str | None
    citations: list
    results_count: int
    latency_ms: float

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: could check GCP credentials / data store availability
    yield
    # Shutdown

app = FastAPI(title="Magic Apron API", description="RAG-backed home improvement concierge", lifespan=lifespan)


@app.exception_handler(Exception)
def unhandled_exception(request, exc):
    """Return JSON for any unhandled exception so the frontend never gets HTML."""
    return _json_error(500, str(exc))

# Serve frontend: portfolio-style single-page experience
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")
else:
    @app.get("/")
    def index():
        return {"message": "Magic Apron API. Use POST /search. Static frontend not found (no static/ dir)."}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/search", response_model=QueryResponse)
def search(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="query must be non-empty")
    start = time.perf_counter()
    try:
        out = search_magic_apron(req.query)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    latency_ms = (time.perf_counter() - start) * 1000
    return QueryResponse(
        summary_text=out.get("summary_text"),
        citations=out.get("citations", []),
        results_count=len(out.get("results", [])),
        latency_ms=round(latency_ms, 2),
    )
