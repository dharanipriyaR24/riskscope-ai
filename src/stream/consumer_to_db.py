import json
import duckdb
from kafka import KafkaConsumer

from src.services.risk_engine import RiskEngine

TOPIC = "transactions"
BOOTSTRAP = "localhost:9092"
DB_PATH = "risklens.duckdb"

"""
SQL analytics visibility (DuckDB)

The Streamlit dashboard and ad-hoc analyst workflows typically query the same table
written by this consumer: `scored_transactions`.

Common examples analysts run:

1) Latest high-risk alerts
   SELECT transaction_id, ts, customer_id, amount, merchant_category, state, risk_score, reasons
   FROM scored_transactions
   WHERE risk_score >= 70
   ORDER BY ts DESC
   LIMIT 200;

2) Risk distribution (bucket by rounded score)
   SELECT ROUND(risk_score) AS risk_bucket, COUNT(*) AS n
   FROM scored_transactions
   GROUP BY 1
   ORDER BY 1;

3) Top merchant categories among risky alerts
   SELECT merchant_category, COUNT(*) AS n
   FROM scored_transactions
   WHERE risk_score >= 70
   GROUP BY 1
   ORDER BY n DESC
   LIMIT 10;
"""


def init_db():
    # Create table once
    with duckdb.connect(DB_PATH) as con:
        con.execute("""
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
        """)


def main():
    init_db()

    print("Loading model...")
    engine = RiskEngine()

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

        customer_id = int(txn.get("customer_id", 0))
        from_acct = int(txn.get("from_acct", customer_id))
        to_acct = int(txn.get("to_acct", 0))

        result = engine.score(txn, shap_mode="auto")
        risk = result.risk_score
        reasons = result.reasons_str

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
