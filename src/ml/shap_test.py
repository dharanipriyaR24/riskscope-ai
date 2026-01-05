import joblib
import pandas as pd
import shap

from src.data.generate_transactions import gen_txn

MODEL_PATH = "artifacts/risk_model.joblib"

def main():
    pipe = joblib.load(MODEL_PATH)

    pre = pipe.named_steps["pre"]
    model = pipe.named_steps["model"]

    # One sample transaction (like a bank event)
    txn = gen_txn(customer_id=101)
    X = pd.DataFrame([txn]).drop(columns=["transaction_id", "ts"])

    # Transform features
    X_trans = pre.transform(X)

    # SHAP TreeExplainer for tree-based model
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_trans)

    # Feature names from preprocessing
    feature_names = list(pre.get_feature_names_out())

    # shap_vals can be array or list depending on binary/versions
    sv = shap_vals[0] if isinstance(shap_vals, list) else shap_vals
    sv_row = sv[0]

    # Top 5 reasons (largest absolute SHAP impact)
    top_idx = sorted(range(len(sv_row)), key=lambda i: abs(sv_row[i]), reverse=True)[:5]
    print("Sample risk drivers (top 5):")
    for i in top_idx:
        print(f" - {feature_names[i]}: {sv_row[i]:+.4f}")

if __name__ == "__main__":
    main()
