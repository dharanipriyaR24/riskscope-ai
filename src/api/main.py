"""
RiskScope AI — FastAPI: fraud risk score + SHAP (+ optional Ollama narrative).

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
    title="RiskScope AI API",
    description=(
        "Analyze transaction risk with an in-process GBDT model + SHAP explanations. "
        "Optional local-LLM narrative via Ollama. "
        "Use POST /analyze-risk or POST /v1/score (same behavior)."
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


def _score(body: TransactionIn, include_narrative: bool) -> ScoreOut:
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


@app.get("/")
def root():
    return {
        "service": "riskscope-ai",
        "product": "RiskScope AI",
        "docs": "/docs",
        "health": "/health",
        "analyze_risk": "POST /analyze-risk",
        "score_v1": "POST /v1/score",
    }


@app.get("/health")
def health():
    ok = state.engine is not None
    return {
        "status": "ok" if ok else "degraded",
        "model_loaded": ok,
        "detail": state.load_error,
    }


@app.post("/analyze-risk", response_model=ScoreOut)
def analyze_risk(
    body: TransactionIn,
    include_narrative: bool = False,
):
    """
    Primary “product” endpoint: transaction in → risk score + SHAP drivers (+ optional narrative).
    """
    return _score(body, include_narrative)


@app.post("/v1/score", response_model=ScoreOut)
def score_transaction(
    body: TransactionIn,
    include_narrative: bool = False,
):
    """Same as POST /analyze-risk (versioned alias)."""
    return _score(body, include_narrative)
