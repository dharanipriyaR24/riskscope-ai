"""Pydantic models for the public API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field, field_validator


class TransactionIn(BaseModel):
    """Transaction payload (same fields the ML pipeline expects)."""

    customer_id: int = Field(..., ge=0)
    amount: float = Field(..., ge=0)
    merchant_category: str
    state: str
    hour: int = Field(..., ge=0, le=23)
    is_new_device: int = Field(0, ge=0, le=1)
    is_international: int = Field(0, ge=0, le=1)
    velocity_1h: int = Field(0, ge=0)
    transaction_id: str | None = None
    ts: str | None = None
    from_acct: int | None = None
    to_acct: int | None = None

    @field_validator("merchant_category")
    @classmethod
    def strip_cat(cls, v: str) -> str:
        return v.strip()


class Narrative(BaseModel):
    """Optional analyst-style narrative from a local LLM."""

    source: str
    text: str


class ScoreOut(BaseModel):
    risk_score: float
    risk_score_pct: str
    alert: bool
    risk_model_tag: str = "sklearn_gbdt + shap"
    shap_top: list[dict[str, Any]]
    reasons_short: str
    narrative: Narrative | None = None


def enrich_body(body: TransactionIn) -> dict:
    """Build full transaction dict for the engine."""
    import uuid

    out = body.model_dump()
    out["transaction_id"] = out.get("transaction_id") or str(uuid.uuid4())
    out["ts"] = out.get("ts") or datetime.now(timezone.utc).isoformat()
    if out.get("from_acct") is None:
        out["from_acct"] = int(out["customer_id"])
    if out.get("to_acct") is None:
        out["to_acct"] = 0
    return out
