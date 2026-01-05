import json
import joblib
import pandas as pd
import shap
from kafka import KafkaConsumer

from src.aml.graph_detector import AMLGraphDetector

MODEL_PATH = "artifacts/risk_model.joblib"
TOPIC = "transactions"
BOOTSTRAP = "localhost:9092"

ALERT_THRESHOLD = 80.0  # fraud risk %

def main():
    print("Loading model...")
    pipe = joblib.load(MODEL_PATH)

    pre = pipe.named_steps["pre"]
    model = pipe.named_steps["model"]

    # SHAP explainer (tree model)
    explainer = shap.TreeExplainer(model)
    feature_names = list(pre.get_feature_names_out())

    # AML detector (graph)
    aml_detector = AMLGraphDetector(
        window_size=500,
        fan_threshold=8,
        degree_threshold=12
    )
    counter = 0

    consumer = KafkaConsumer(
        TOPIC,
        bootstrap_servers=BOOTSTRAP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="risklens",
    )

    print("Listening for transactions...")
    for msg in consumer:
        txn = msg.value

        # --- AML graph feed (requires from_acct/to_acct in producer data) ---
        if "from_acct" in txn and "to_acct" in txn:
            aml_detector.add_transaction(
                from_acct=int(txn["from_acct"]),
                to_acct=int(txn["to_acct"])
            )

            aml_alerts = aml_detector.detect_mule()
            for alert in aml_alerts:
                print(
                    f"🧠 AML ALERT | suspected mule "
                    f"acct={alert['node']} fan_in={alert['fan_in']} "
                    f"fan_out={alert['fan_out']} total_degree={alert['total_degree']}"
                )

        # --- Fraud model scoring (drop non-feature cols) ---
        X = pd.DataFrame([txn]).drop(
            columns=["transaction_id", "ts", "from_acct", "to_acct"],
            errors="ignore"
        )

        risk = float(pipe.predict_proba(X)[0, 1] * 100)

        if risk >= ALERT_THRESHOLD:
            # SHAP explanation
            X_trans = pre.transform(X)
            shap_vals = explainer.shap_values(X_trans)

            sv = shap_vals[0] if isinstance(shap_vals, list) else shap_vals
            sv_row = sv[0]

            top_idx = sorted(
                range(len(sv_row)),
                key=lambda i: abs(sv_row[i]),
                reverse=True
            )[:3]

            reasons = ", ".join(
                [f"{feature_names[i]}({sv_row[i]:+.3f})" for i in top_idx]
            )

            print(
                f"🚨 FRAUD ALERT | txn={txn.get('transaction_id')} customer={txn.get('customer_id')} "
                f"risk={risk:.2f}% amount=${txn.get('amount')} | reasons: {reasons}"
            )
        else:
            print(f"OK | txn={txn.get('transaction_id')} risk={risk:.2f}%")

        # Reset AML window counts every 100 txns (keeps alerts meaningful)
        counter += 1
        if counter % 100 == 0:
            aml_detector.reset_window()

if __name__ == "__main__":
    main()
