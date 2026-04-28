"""
RiskLens FastAPI — synchronous fraud score + SHAP (+ optional Ollama narrative).

Run from repo root:
  uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.api.narrative import build_narrative_prompt, try_narrative
from src.api.schemas import Narrative, ScoreOut, TransactionIn, enrich_body
from src.services.risk_engine import RiskEngine


class AppState:
    engine: RiskEngine | None = None
    load_error: str | None = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        state.engine = RiskEngine()
        state.load_error = None
    except Exception as e:
        state.engine = None
        state.load_error = str(e)
    yield


app = FastAPI(
    title="RiskLens AI API",
    description=(
        "Score a single transaction with an in-process GBDT model + SHAP explanations. "
        "Optional local-LLM narrative via Ollama."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "risklens-api",
        "docs": "/docs",
        "health": "/health",
        "score": "POST /v1/score",
    }


@app.get("/health")
def health():
    ok = state.engine is not None
    return {
        "status": "ok" if ok else "degraded",
        "model_loaded": ok,
        "detail": state.load_error,
    }


@app.post("/v1/score", response_model=ScoreOut)
def score_transaction(
    body: TransactionIn,
    include_narrative: bool = False,
):
    """
    Input: transaction features. Output: risk %, SHAP top drivers, optional LLM narrative.
    Set include_narrative=true if Ollama is running (see README).
    """
    if state.engine is None:
        raise HTTPException(
            status_code=503,
            detail=state.load_error or "Model not loaded. Train: python -m src.ml.train_model",
        )

    txn = enrich_body(body)
    result = state.engine.score(txn, shap_mode="always", top_k=5)

    narrative: Narrative | None = None
    if include_narrative:
        prompt = build_narrative_prompt(
            txn,
            result.risk_score,
            result.shap_top,
            result.reasons_str,
        )
        src, txt = try_narrative(prompt)
        narrative = Narrative(source=src, text=txt)

    return ScoreOut(
        risk_score=result.risk_score,
        risk_score_pct=f"{result.risk_score:.2f}%",
        alert=result.alert,
        risk_model_tag="sklearn_gbdt + shap",
        shap_top=result.shap_top,
        reasons_short=result.reasons_str,
        narrative=narrative,
    )
