"""Optional LLM narrative for API responses (Ollama, same as dashboard copilot)."""

from __future__ import annotations

from src.ui.llm import run_copilot


def build_narrative_prompt(
    transaction: dict,
    risk_score: float,
    shap_top: list[dict],
    reasons_short: str,
) -> str:
    lines = [
        "You are a bank fraud analyst assistant. Be concise (bullets).",
        "",
        f"Transaction: {transaction}",
        f"Model risk score: {risk_score:.2f}%",
        f"Top SHAP drivers: {reasons_short or 'N/A'}",
        f"Structured SHAP: {shap_top[:5]}",
        "",
        "Return: (1) 2–3 bullet risk summary (2) why suspicious (3) recommended next steps.",
    ]
    return "\n".join(lines)


def try_narrative(prompt: str) -> tuple[str, str]:
    """
    Returns (source, text). source is 'ollama' or 'unavailable'.
    """
    text = run_copilot(prompt)
    if text.startswith("ERROR:"):
        return "unavailable", text
    return "ollama", text
