"""FastAPI web application for ScholarScope.

Serves static UI files and exposes REST API endpoints:
- POST /api/analyze: Executes full 6-stage pipeline (synchronous)
- POST /api/analyze-stream: Executes pipeline with Server-Sent Events (SSE) streaming real-time stage progress
- GET /api/history: Fetches last 10 analyses from Results tab via Apps Script webhook
- GET /api/tests: Fetches test suite runs from Tests tab via Apps Script webhook
- GET /api/prompts: Returns prompt texts and iterative evolution log
- GET /api/health: Makes real check to Gemini and Webhook
"""

import json
import os
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pipeline import run_pipeline, run_pipeline_stream
from prompts import ANALYSIS_PROMPT, SCORING_PROMPTS, REPORT_PROMPT, PROMPT_LOG
from sheets import get_history, get_tests_history, check_webhook_health
from llm import get_api_key, get_model_name

app = FastAPI(
    title="ScholarScope API",
    description="Research Topic Feasibility Analyzer for B.Tech Students",
    version="1.0.0"
)

# CORS middleware for open local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vercel serverless path normalizer
@app.middleware("http")
async def vercel_path_rewrite(request: Request, call_next):
    # Check if Vercel passed the subpath in __path__ query param
    subpath = request.query_params.get("__path__")
    if subpath:
        clean = subpath.strip("/").split("?")[0]
        if clean.startswith("api/"):
            clean = clean[4:]
        request.scope["path"] = f"/api/{clean}"
    elif request.scope.get("path") == "/api/index.py":
        # Fallback if no subpath
        request.scope["path"] = "/"
    return await call_next(request)

# Request schemas
class AnalyzeRequest(BaseModel):
    topic: str = Field(..., description="The research topic to evaluate")
    version: str = Field("V3", description="Prompt version to use: V1, V2, or V3")


# =====================================================================
# API Endpoints
# =====================================================================

@app.post("/api/analyze")
@app.post("/analyze")
async def analyze_topic(req: AnalyzeRequest) -> Dict[str, Any]:
    """Runs the full ScholarScope pipeline synchronously."""
    if not req.topic or not req.topic.strip():
        raise HTTPException(status_code=400, detail="Research topic cannot be empty.")
    result = run_pipeline(topic=req.topic, version=req.version)
    return result


@app.post("/api/analyze-stream")
@app.post("/analyze-stream")
def analyze_topic_stream(req: AnalyzeRequest):
    """Streams real-time per-stage execution events using Server-Sent Events (SSE)."""
    if not req.topic or not req.topic.strip():
        raise HTTPException(status_code=400, detail="Research topic cannot be empty.")

    def event_stream():
        for event in run_pipeline_stream(topic=req.topic, version=req.version):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/api/history")
@app.get("/history")
async def fetch_history() -> Dict[str, Any]:
    """Retrieves the last 10 analyses from the Results tab via Apps Script."""
    ok, records, err = get_history(limit=10)
    return {
        "status": "success" if ok else "error",
        "count": len(records),
        "data": records,
        "error": err
    }


@app.get("/api/tests")
@app.get("/tests")
async def fetch_tests() -> Dict[str, Any]:
    """Retrieves test results from the Tests tab via Apps Script."""
    ok, records, err = get_tests_history(limit=50)
    return {
        "status": "success" if ok else "error",
        "count": len(records),
        "data": records,
        "error": err
    }


@app.get("/api/prompts")
@app.get("/prompts")
async def fetch_prompts() -> Dict[str, Any]:
    """Returns prompt texts and iteration log comparing V1, V2, and V3."""
    return {
        "status": "success",
        "analysis_prompt": ANALYSIS_PROMPT,
        "scoring_prompts": SCORING_PROMPTS,
        "report_prompt": REPORT_PROMPT,
        "prompt_log": PROMPT_LOG
    }


@app.get("/api/health")
@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Makes a real GET to the webhook and checks key and model reachability."""
    has_gemini_key = bool(get_api_key())
    model = get_model_name()
    ok_webhook, webhook_status_msg = check_webhook_health()

    return {
        "status": "healthy" if (has_gemini_key and ok_webhook) else "degraded",
        "gemini": {
            "key_configured": has_gemini_key,
            "model": model,
            "mode": "live_api" if has_gemini_key else "key_missing"
        },
        "webhook": {
            "reachable": ok_webhook,
            "message": webhook_status_msg
        }
    }


# =====================================================================
# Static Files & SPA Routing
# =====================================================================

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
ROOT_DIR = os.path.dirname(__file__)

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
if os.path.exists(DOCS_DIR):
    app.mount("/docs", StaticFiles(directory=DOCS_DIR), name="docs")

@app.get("/")
async def serve_index():
    """Serves the single-page frontend application."""
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(cur_dir)

    for candidate in [
        os.path.join(cur_dir, "api", "index.html"),
        os.path.join(cur_dir, "index.html"),
        os.path.join(cur_dir, "static", "index.html"),
        os.path.join(parent_dir, "api", "index.html"),
        os.path.join(parent_dir, "index.html"),
        os.path.join(parent_dir, "static", "index.html"),
        "api/index.html",
        "index.html",
        "static/index.html"
    ]:
        if os.path.exists(candidate):
            with open(candidate, "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content, status_code=200)

    return HTMLResponse("<h1>ScholarScope</h1><p>UI loading error: index.html not found</p>", status_code=500)
