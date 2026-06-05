"""
FastAPI Application — API layer for the AI App Compiler.
Provides endpoints for prompt compilation, evaluation, and health checks.
"""

from __future__ import annotations
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from backend.config import CORS_ORIGINS, GENERATED_APPS_DIR
from backend.pipeline.orchestrator import PipelineOrchestrator
from backend.runtime.simulator import RuntimeSimulator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("[START] PromptForge starting up...")
    yield
    logger.info("[STOP] PromptForge shutting down.")


app = FastAPI(
    title="PromptForge",
    description="Compiler-like pipeline: Natural Language → Structured Config → Validated → Executable App",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ============= Request / Response Models =============

class CompileRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Natural language application description",
        examples=["Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments."],
    )


class CompileResponse(BaseModel):
    success: bool
    app_spec: dict | None = None
    pipeline: dict | None = None
    cost: dict | None = None
    runtime: dict | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"


# ============= Endpoints =============

@app.get("/", response_class=FileResponse)
async def serve_frontend():
    """Serve the frontend UI."""
    return FileResponse("frontend/index.html")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.post("/api/compile", response_model=CompileResponse)
async def compile_app(request: CompileRequest):
    """
    Compile a natural language prompt into a full application specification.

    This is the main endpoint. It runs the 4-stage compiler pipeline:
    1. Lexer (Intent Extraction)
    2. Parser (System Design)
    3. IR Generator (Schema Generation)
    4. Optimizer (Refinement)

    Each stage passes through a validation gate with repair capability.
    On success, the output is also run through the Runtime Simulator.
    """
    logger.info(f"[API] Compile request: {request.prompt[:100]}...")

    try:
        # Run the pipeline
        orchestrator = PipelineOrchestrator()
        result = orchestrator.run(request.prompt)

        runtime_report = None

        # If pipeline succeeded, run runtime simulation
        if result.success and result.app_spec_dict:
            try:
                simulator = RuntimeSimulator()
                exec_report = simulator.simulate(result.app_spec_dict)
                runtime_report = exec_report.to_dict()
            except Exception as e:
                logger.error(f"[API] Runtime simulation error: {e}")
                runtime_report = {"error": str(e)}

        response_data = result.to_dict()
        response_data["runtime"] = runtime_report

        return CompileResponse(**response_data)

    except Exception as e:
        logger.error(f"[API] Compilation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Compilation failed: {str(e)}",
        )


@app.get("/api/preview/{app_name}", response_class=HTMLResponse)
async def preview_app(app_name: str):
    """Serve a generated app preview."""
    import os
    filepath = os.path.join(str(GENERATED_APPS_DIR), f"{app_name}.html")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Generated app not found")
    with open(filepath, "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/api/evaluation/results")
async def get_evaluation_results():
    """Serve the latest evaluation results JSON."""
    import os
    import json
    from backend.config import EVAL_RESULTS_DIR

    results_path = os.path.join(str(EVAL_RESULTS_DIR), "latest_evaluation.json")
    if not os.path.exists(results_path):
        raise HTTPException(
            status_code=404,
            detail="No evaluation results found. Run an evaluation first.",
        )

    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@app.post("/api/evaluation/run")
async def run_evaluation(count: int = 3):
    """
    Run evaluation on a subset of test prompts.
    Use count=3 for a quick check or count=20 for full evaluation.
    """
    from backend.evaluation.test_prompts import ALL_PROMPTS
    from backend.evaluation.runner import EvaluationRunner

    prompts = ALL_PROMPTS[:min(count, len(ALL_PROMPTS))]
    runner = EvaluationRunner()
    summary = runner.run_all(prompts)
    return summary.model_dump()


# ============= Run =============

if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
