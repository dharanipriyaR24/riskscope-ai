# =========================
# PATH FIX FOR STREAMLIT
# =========================
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# =========================
# IMPORTS
# =========================
import duckdb
import pandas as pd
import streamlit as st
from datetime import datetime

from src.ui.llm import run_copilot

# =========================
# CONFIG
# =========================
DB_PATH = "risklens.duckdb"

st.set_page_config(page_title="RiskLens AI Dashboard", layout="wide")
st.title("RiskLens AI — Bank Fraud Analyst Dashboard")

# Read-only DB connection (avoids Windows lock issues)
con = duckdb.connect(DB_PATH, read_only=True)

# =========================
# HELPERS
# =========================
def table_columns(conn, table_name: str) -> set:
    cols = conn.execute(f"PRAGMA table_info('{table_name}')").df()
    return set(cols["name"].tolist())

def get_latest_rows(min_risk: int, limit: int) -> pd.DataFrame:
    return con.execute(
        """
        SELECT *
        FROM scored_transactions
        WHERE risk_score >= ?
        ORDER BY ts DESC
        LIMIT ?
        """,
        [min_risk, limit]
    ).df()

def get_overview():
    try:
        total = con.execute("SELECT COUNT(*) c FROM scored_transactions").df().iloc[0]["c"]
        latest = con.execute("SELECT MAX(ts) mx FROM scored_transactions").df().iloc[0]["mx"]
        return total, latest
    except Exception:
        return 0, None

# =========================
# TABS
# =========================
tab1, tab2, tab3, tab4 = st.tabs(
    ["🚨 Fraud Alerts", "🧠 AML Signals", "🤖 Copilot", "⚙️ Ops"]
)

# =========================
# TAB 1: FRAUD ALERTS
# =========================
with tab1:
    min_risk = st.slider("Minimum risk score", 0, 100, 70)
    limit = st.selectbox("Rows to show", [50, 100, 200, 500], index=1)

    df = get_latest_rows(min_risk, limit)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Alerts / Transactions")
        st.dataframe(df, use_container_width=True, hide_index=True)

        if len(df) > 0:
            st.markdown("### Inspect a transaction")
            txn_id = st.selectbox("Select transaction_id", df["transaction_id"].tolist())
            row = df[df["transaction_id"] == txn_id].iloc[0]
            st.json(row.to_dict())

    with col2:
        st.subheader("Counts by Merchant Category")
        if len(df) > 0:
            st.bar_chart(df["merchant_category"].value_counts())

        st.subheader("Risk Score Distribution")
        if len(df) > 0:
            st.bar_chart(df["risk_score"].round().value_counts().sort_index())

        st.subheader("Top Risk Drivers (SHAP)")
        tokens = []
        for r in df["reasons"].fillna(""):
            for part in r.split(","):
                p = part.strip()
                if p:
                    tokens.append(p.split("(")[0])
        if tokens:
            top = pd.Series(tokens).value_counts().head(10)
            st.dataframe(top.reset_index().rename(columns={"index": "feature", 0: "count"}), hide_index=True)

# =========================
# TAB 2: AML SIGNALS
# =========================
with tab2:
    st.subheader("AML Mule Detection (Fan-In / Fan-Out)")

    cols = table_columns(con, "scored_transactions")
    if "from_acct" not in cols or "to_acct" not in cols:
        st.error("AML columns not found. Ensure from_acct and to_acct are stored.")
    else:
        n = st.slider("Analyze last N transactions", 200, 10000, 1500, step=100)

        edges = con.execute(
            """
            SELECT from_acct, to_acct
            FROM scored_transactions
            WHERE to_acct != 0
            ORDER BY ts DESC
            LIMIT ?
            """,
            [n]
        ).df()

        if len(edges) == 0:
            st.warning("No transfer data yet.")
        else:
            fan_out = edges.groupby("from_acct").size().reset_index(name="fan_out")
            fan_in = edges.groupby("to_acct").size().reset_index(name="fan_in")

            merged = fan_out.merge(
                fan_in, left_on="from_acct", right_on="to_acct", how="outer"
            ).fillna(0)

            merged["acct"] = merged["from_acct"].fillna(merged["to_acct"])
            merged["mule_score"] = merged["fan_in"] * merged["fan_out"]
            merged = merged.sort_values("mule_score", ascending=False)

            threshold = st.slider(
                "Mule score threshold", 0.0, float(max(merged["mule_score"].max(), 1.0)), 10.0
            )

            st.dataframe(
                merged[merged["mule_score"] >= threshold]
                .head(100)[["acct", "fan_in", "fan_out", "mule_score"]],
                use_container_width=True,
                hide_index=True,
            )

# =========================
# TAB 3: COPILOT (OLLAMA)
# =========================
with tab3:
    st.subheader("Copilot — AI Fraud Investigation Assistant")

    df_alerts = con.execute(
        """
        SELECT transaction_id, ts, customer_id, amount,
               merchant_category, state, risk_score, reasons
        FROM scored_transactions
        WHERE risk_score >= 70
        ORDER BY ts DESC
        LIMIT 200
        """
    ).df()

    if df_alerts.empty:
        st.warning("No high-risk transactions yet.")
    else:
        pick = st.selectbox("Select an alert", df_alerts["transaction_id"].tolist())
        r = df_alerts[df_alerts["transaction_id"] == pick].iloc[0]

        st.json(r.to_dict())

        prompt = f"""
You are a bank fraud analyst assistant.

Transaction:
- ID: {r['transaction_id']}
- Time: {r['ts']}
- Customer: {r['customer_id']}
- Amount: ${float(r['amount']):.2f}
- Merchant: {r['merchant_category']}
- State: {r['state']}
- Risk Score: {float(r['risk_score']):.2f}%
- Model Reasons: {r.reasons if r.reasons else "Risk score is elevated but below explanation threshold. Consider behavioral context."}
Write:
1) Risk summary (2-3 bullets)
2) Why it is suspicious (bullets)
3) Recommended next steps (bullets)
Use professional banking language. Keep it concise.
"""

        if st.button("🧠 Generate Copilot Summary"):
            with st.spinner("Copilot analyzing..."):
                response = run_copilot(prompt)  # returns a string
            st.markdown("### Copilot Output")
            st.text_area("Copilot Output", response, height=320)

# =========================
# TAB 4: OPS
# =========================
with tab4:
    st.subheader("System Health")

    total, latest = get_overview()

    c1, c2, c3 = st.columns(3)
    c1.metric("Rows in DB", total)
    c2.metric("Latest Timestamp", str(latest))
    c3.metric("Dashboard Time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    st.code(
        "docker compose up -d\n"
        "python -m src.stream.consumer_to_db\n"
        "python -m src.stream.producer\n"
        "streamlit run src/ui/dashboard.py",
        language="powershell",
    )

    st.caption("Keep consumer running. Dashboard is read-only to avoid DB locks.")
