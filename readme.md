🛡️ RiskLens AI — Real-Time Bank Fraud Detection & Investigation Platform

RiskLens AI is a real-time fraud detection and investigation system designed for modern banks.
It combines streaming ML risk scoring, model explainability (SHAP), AML heuristics, and an AI copilot to support fraud analysts in decision-making.

Built to simulate how fraud, risk, and AML teams operate in production environments.

🚀 Key Features
🔴 Real-Time Fraud Scoring

Kafka (Redpanda) streaming transaction ingestion

Gradient Boosting ML model for fraud risk scoring

Risk scores computed in milliseconds

🧠 Explainable AI (XAI)

SHAP explanations for high-risk transactions

Shows top contributing risk drivers

Analyst-friendly explanations (not black-box)

🧾 Fraud Analytics Store

DuckDB used as a fast analytical store

Stores:

Transaction metadata

Risk scores

SHAP explanations

Account-to-account flows (AML)

📊 Analyst Dashboard (Streamlit)

Live transaction monitoring

Risk filtering & drill-downs

Merchant category analytics

Risk distribution visualization

SHAP reason aggregation

🔍 AML Heuristics

Fan-in / Fan-out analysis

Mule account detection (graph-based)

Simple but realistic AML scoring logic

🤖 AI Copilot (Local LLM)

Local LLM via Ollama (Phi-3)

Generates:

Investigation summaries

Analyst notes

Recommended next steps

No cloud dependency (privacy-safe)

🧱 System Architecture
┌────────────┐
│ Producer   │  Synthetic Transactions
└─────┬──────┘
      │
      ▼
┌────────────┐
│ Kafka /    │  Redpanda
│ Streaming  │
└─────┬──────┘
      │
      ▼
┌────────────────────┐
│ ML Consumer        │
│ - Risk scoring     │
│ - SHAP explain     │
└─────┬──────────────┘
      │
      ▼
┌────────────────────┐
│ DuckDB             │
│ - Fraud analytics  │
│ - AML graph data   │
└─────┬──────────────┘
      │
      ▼
┌────────────────────┐
│ Streamlit UI       │
│ + AI Copilot       │
└────────────────────┘

🧪 Tech Stack
Layer	Technology
Streaming	Kafka (Redpanda)
ML	Scikit-learn
Explainability	SHAP
Database	DuckDB
Dashboard	Streamlit
LLM	Ollama (Phi-3)
Infra	Docker Compose
Language	Python
▶️ How to Run (Local)
1️⃣ Start Kafka (Redpanda)
docker compose up -d

2️⃣ Start Consumer (ML + DB Writer)
python -m src.stream.consumer_to_db

3️⃣ Start Producer (Synthetic Data)
python -m src.stream.producer

4️⃣ Launch Dashboard
streamlit run src/ui/dashboard.py


Open:
👉 http://localhost:8501

🤖 AI Copilot (Local LLM)

Install Ollama:

https://ollama.com/download


Pull model:

ollama pull phi3


Run example:

ollama run phi3 "Explain why gift cards are used in fraud"

📌 Example Use Case

Transaction flagged at 85% risk

SHAP shows:

High amount

Gift card merchant

Rapid transaction velocity

Copilot generates:

Investigation summary

Compliance-ready analyst note

🎯 Why This Project Matters

This project demonstrates end-to-end applied AI:

Real-time systems

Explainability (required by regulators)

Analyst tooling

AML thinking

Production-style architecture

👩‍💻 Author

Keerthana Senthil Raja
MS Data Science — Seattle University
GitHub: https://github.com/Keerthana2001-ops