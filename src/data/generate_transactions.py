import random
import time
import uuid
from datetime import datetime, timezone

MERCHANTS = ["GROCERY", "GAS", "ONLINE_RETAIL", "ELECTRONICS", "CRYPTO_EXCHANGE", "GIFT_CARDS", "WIRE_SERVICE"]
STATES = ["CA", "NY", "TX", "FL", "WA", "IL", "NJ", "MA"]

# For AML graph edges (from_acct -> to_acct)
N_ACCOUNTS = 2000

def gen_txn(customer_id: int) -> dict:
    merchant = random.choice(MERCHANTS)
    base_amt = random.choice([12, 25, 60, 120, 350, 900, 2500])
    amount = float(base_amt + random.random() * base_amt)

    is_new_device = random.random() < 0.18
    is_international = random.random() < 0.06
    hour = random.randint(0, 23)
    velocity_1h = random.choice([0, 1, 2, 3, 6, 10])

    # ---- AML transfer fields ----
    from_acct = customer_id  # simple mapping: customer_id as account id
    to_acct = random.randint(1, N_ACCOUNTS)
    while to_acct == from_acct:
        to_acct = random.randint(1, N_ACCOUNTS)

    return {
        "transaction_id": str(uuid.uuid4()),
        "ts": datetime.now(timezone.utc).isoformat(),
        "customer_id": customer_id,

        # AML graph edge
        "from_acct": from_acct,
        "to_acct": to_acct,

        "amount": round(amount, 2),
        "merchant_category": merchant,
        "state": random.choice(STATES),
        "hour": hour,
        "is_new_device": int(is_new_device),
        "is_international": int(is_international),
        "velocity_1h": velocity_1h,
    }

def stream_batch(n_customers=200, n_txns=50):
    for _ in range(n_txns):
        cid = random.randint(1, n_customers)
        yield gen_txn(cid)
        time.sleep(0.01)

if __name__ == "__main__":
    for t in stream_batch():
        print(t)
