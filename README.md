# Risklens ai

**Real-time bank fraud scoring, explainable ML (SHAP), AML-style graph signals, and a local LLM copilot—wired together with Kafka (Redpanda), DuckDB, and Streamlit.**

**Suggested GitHub About description (one line):** Real-time fraud and AML analytics: streaming risk scores, SHAP explanations, DuckDB storage, Streamlit dashboard, and Ollama copilot.

---

## What this project is

Risklens ai is a **local, end-to-end demo** of how fraud and AML teams often combine:

- **Streaming ingestion** of synthetic transactions (Kafka-compatible API via Redpanda).
- **Gradient boosting** risk scores (scikit-learn pipeline with preprocessing).
- **SHAP** explanations for high-risk events (top contributing features).
- **DuckDB** as a fast analytical store for scored transactions and AML-oriented account flows.
- **Streamlit** dashboard for alerts, AML fan-in/fan-out views, and ops notes.
- **Optional copilot** using **Ollama** (for example Phi-3) for short investigation summaries—no cloud LLM required.

It is intended for **learning and portfolio demos**, not production authorization of real transactions.

---

## Architecture

```text
Producer (synthetic txns)
        |
        v
  Redpanda (Kafka API)
        |
        v
  Consumer (score + SHAP -> DuckDB)
        |
        v
  Streamlit dashboard (+ Ollama copilot)
```

---

## Repository layout

| Path | Role |
|------|------|
| `src/stream/producer.py` | Publishes synthetic transactions to the `transactions` topic. |
| `src/stream/consumer_to_db.py` | Consumes, scores, explains (above threshold), writes to DuckDB. |
| `src/stream/consumer_score.py` | Console consumer with fraud alerts and in-memory AML graph hints. |
| `src/ml/train_model.py` | Trains pipeline and saves `artifacts/risk_model.joblib`. |
| `src/data/generate_transactions.py` | Synthetic transaction generator. |
| `src/ui/dashboard.py` | Streamlit analyst UI. |
| `src/ui/llm.py` | HTTP client for Ollama `/api/generate`. |
| `src/aml/graph_detector.py` | Simple fan-in / fan-out mule-style heuristic. |
| `docker-compose.yml` | Redpanda on `localhost:9092`. |

---

## Prerequisites

- **Python 3.10+** (recommended)
- **Docker** (for Redpanda)
- **Ollama** (optional, for the copilot tab): https://ollama.com/download

---

## Quick start

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   On Windows: `.venv\Scripts\activate`

2. **Train the model** (creates `artifacts/risk_model.joblib`)

   ```bash
   python -m src.ml.train_model
   ```

3. **Start Redpanda**

   ```bash
   docker compose up -d
   ```

4. **Run the pipeline** (separate terminals)

   ```bash
   python -m src.stream.consumer_to_db
   ```

   ```bash
   python -m src.stream.producer
   ```

5. **Open the dashboard**

   ```bash
   streamlit run src/ui/dashboard.py
   ```

   Then open http://localhost:8501

6. **Copilot (optional)**

   ```bash
   ollama pull phi3
   ```

   The app expects a model tag compatible with `src/ui/llm.py` (default: `phi3:latest`). Change `MODEL` there if your tag differs (`ollama list`).

---

## Tech stack

| Area | Technology |
|------|------------|
| Streaming | Redpanda (Kafka protocol) |
| ML | scikit-learn (Gradient Boosting) |
| Explainability | SHAP (TreeExplainer) |
| Analytics DB | DuckDB |
| UI | Streamlit |
| Local LLM | Ollama |
| Language | Python |

---

## Example narrative

1. A synthetic transaction streams in and receives a **risk percentage**.
2. Above the alert threshold, **SHAP** surfaces a few top drivers (amount, category, velocity, and so on).
3. The **dashboard** filters alerts and aggregates common reason tokens.
4. The **copilot** drafts a concise analyst-style summary when Ollama is running.

---

## Author

**Keerthana Senthil Raja** — MS Data Science, Seattle University  
GitHub: https://github.com/Keerthana2001-ops

---

## License

Add a `LICENSE` file in this repository if you plan to open-source under explicit terms.
