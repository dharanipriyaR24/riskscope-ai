"""
Trained model + SHAP in one place: used by streaming consumer and HTTP API.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

import joblib
import pandas as pd
import shap

DEFAULT_MODEL_PATH = os.path.join("artifacts", "risk_model.joblib")
ALERT_THRESHOLD = 80.0


@dataclass
class ScoreResult:
    """One scored transaction."""

    risk_score: float
    alert: bool
    reasons_str: str = ""
    shap_top: list[dict[str, Any]] = field(default_factory=list)


class RiskEngine:
    """Loads GradientBoosting pipeline once; scores dict-shaped transactions."""

    def __init__(self, model_path: str | None = None):
        path = model_path or DEFAULT_MODEL_PATH
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Model not found at {path}. Run: python -m src.ml.train_model")

        self.pipe = joblib.load(path)
        self.pre = self.pipe.named_steps["pre"]
        self.model = self.pipe.named_steps["model"]
        self.explainer = shap.TreeExplainer(self.model)
        self.feature_names: list[str] = list(self.pre.get_feature_names_out())
        self.alert_threshold = ALERT_THRESHOLD

    def _build_X(self, txn: dict) -> pd.DataFrame:
        return pd.DataFrame([txn]).drop(
            columns=["transaction_id", "ts", "from_acct", "to_acct"],
            errors="ignore",
        )

    def _top_shap(
        self,
        _X_raw: pd.DataFrame,
        X_trans,
        top_k: int = 5,
    ) -> tuple[list[dict[str, Any]], str]:
        shap_vals = self.explainer.shap_values(X_trans)
        sv = shap_vals[0] if isinstance(shap_vals, list) else shap_vals
        sv_row = sv[0]
        top_idx = sorted(range(len(sv_row)), key=lambda i: abs(sv_row[i]), reverse=True)[:top_k]
        shap_top = [
            {
                "feature": self.feature_names[i],
                "shap_value": float(sv_row[i]),
                "direction": "increases_risk" if sv_row[i] > 0 else "decreases_risk",
            }
            for i in top_idx
        ]
        reasons_str = ", ".join([f"{self.feature_names[i]}({sv_row[i]:+.3f})" for i in top_idx[:3]])
        return shap_top, reasons_str

    def score(
        self,
        txn: dict,
        *,
        shap_mode: str = "auto",
        top_k: int = 5,
    ) -> ScoreResult:
        """
        shap_mode:
          - \"auto\": compute SHAP only when risk >= alert_threshold (streaming-friendly).
          - \"always\": always compute SHAP (API / analyst UX).
        """
        customer_id = int(txn.get("customer_id", 0))
        txn = dict(txn)
        txn.setdefault("from_acct", customer_id)
        txn.setdefault("to_acct", 0)

        X = self._build_X(txn)
        risk = float(self.pipe.predict_proba(X)[0, 1] * 100)
        alert = risk >= self.alert_threshold

        compute_shap = shap_mode == "always" or (shap_mode == "auto" and alert)
        if not compute_shap:
            return ScoreResult(risk_score=round(risk, 4), alert=alert, reasons_str="")

        X_trans = self.pre.transform(X)
        shap_top, reasons_str = self._top_shap(X, X_trans, top_k=top_k)
        return ScoreResult(
            risk_score=round(risk, 4),
            alert=alert,
            reasons_str=reasons_str,
            shap_top=shap_top,
        )
