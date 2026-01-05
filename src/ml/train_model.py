import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import roc_auc_score
from sklearn.ensemble import GradientBoostingClassifier

from src.data.generate_transactions import gen_txn

def make_label(df: pd.DataFrame) -> pd.Series:
    """
    Synthetic risk label:
    1 = risky transaction
    0 = normal
    """
    score = (
        (df["amount"] > 900).astype(int) +
        (df["merchant_category"].isin(["CRYPTO_EXCHANGE", "GIFT_CARDS", "WIRE_SERVICE"])).astype(int) +
        (df["is_new_device"] == 1).astype(int) +
        (df["is_international"] == 1).astype(int) +
        (df["velocity_1h"] >= 6).astype(int) +
        ((df["hour"] <= 4) | (df["hour"] >= 23)).astype(int)
    )
    return (score >= 3).astype(int)

def main():
    print("Generating synthetic training data...")
    rows = [gen_txn(int(np.random.randint(1, 500))) for _ in range(20000)]
    df = pd.DataFrame(rows)

    y = make_label(df)

    # ✅ IMPORTANT FIX: drop AML transfer fields so model input stays stable
    X = df.drop(columns=["transaction_id", "ts", "from_acct", "to_acct"])

    cat_features = ["merchant_category", "state"]
    num_features = [
        "amount", "hour", "is_new_device",
        "is_international", "velocity_1h", "customer_id"
    ]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_features),
            ("num", "passthrough", num_features),
        ]
    )

    model = GradientBoostingClassifier(random_state=42)

    pipeline = Pipeline([
        ("pre", preprocessor),
        ("model", model)
    ])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    print("Training model...")
    pipeline.fit(X_train, y_train)

    preds = pipeline.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, preds)

    print(f"Model AUC: {auc:.4f}")

    joblib.dump(pipeline, "artifacts/risk_model.joblib")
    print("Saved model to artifacts/risk_model.joblib")

if __name__ == "__main__":
    main()
