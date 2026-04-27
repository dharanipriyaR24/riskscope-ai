import json
import joblib
import duckdb
import pandas as pd
import shap
from kafka import KafkaConsumer

MODEL_PATH = "artifacts/risk_model.joblib"
TOPIC = "transactions"
BOOTSTRAP = "localhost:9092"
DB_PATH = "risklens.duckdb"

ALERT_THRESHOLD = 80.0


def init_db():
    # Create table once
    with duckdb.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS scored_transactions (
                transaction_id VARCHAR,
                ts VARCHAR,
                customer_id BIGINT,
                amount DOUBLE,
                merchant_category VARCHAR,
                state VARCHAR,
                hour INTEGER,
                is_new_device INTEGER,
                is_international INTEGER,
                velocity_1h INTEGER,
                from_acct BIGINT,
                to_acct BIGINT,
                risk_score DOUBLE,
                reasons VARCHAR
            );
        """
        )


def main():
    init_db()

    print("Loading model...")
    pipe = joblib.load(MODEL_PATH)
    pre = pipe.named_steps["pre"]
    model = pipe.named_steps["model"]

    # SHAP explainer (tree model)
    explainer = shap.TreeExplainer(model)
    feature_names = list(pre.get_feature_names_out())

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="risklens-db",
    )

    print("Listening and writing to DB...")

    for msg in consumer:
        txn = msg.value

        # Pull account fields if present; safe fallbacks if not
        customer_id = int(txn.get("customer_id", 0))
        from_acct = int(txn.get("from_acct", customer_id))  # fallback: customer_id
        to_acct = int(txn.get("to_acct", 0))  # fallback: 0 (unknown)

        # IMPORTANT: model should not see non-feature cols
        X = pd.DataFrame([txn]).drop(
            columns=["transaction_id", "ts", "from_acct", "to_acct"], errors="ignore"
        )

        risk = float(pipe.predict_proba(X)[0, 1] * 100)

        reasons = ""
        if risk >= ALERT_THRESHOLD:
            X_trans = pre.transform(X)
            shap_vals = explainer.shap_values(X_trans)

            sv = shap_vals[0] if isinstance(shap_vals, list) else shap_vals
            sv_row = sv[0]

            top_idx = sorted(range(len(sv_row)), key=lambda i: abs(sv_row[i]), reverse=True)[:3]

            reasons = ", ".join([f"{feature_names[i]}({sv_row[i]:+.3f})" for i in top_idx])

        # Open -> insert -> close (prevents Windows file lock)
        with duckdb.connect(DB_PATH) as con:
            con.execute(
                """
                INSERT INTO scored_transactions (
                    transaction_id, ts, customer_id, amount, merchant_category, state, hour,
                    is_new_device, is_international, velocity_1h, from_acct, to_acct,
                    risk_score, reasons
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    txn.get("transaction_id"),
                    txn.get("ts"),
                    customer_id,
                    float(txn.get("amount", 0.0)),
                    txn.get("merchant_category"),
                    txn.get("state"),
                    int(txn.get("hour", 0)),
                    int(txn.get("is_new_device", 0)),
                    int(txn.get("is_international", 0)),
                    int(txn.get("velocity_1h", 0)),
                    from_acct,
                    to_acct,
                    risk,
                    reasons,
                ),
            )


if __name__ == "__main__":
    main()
