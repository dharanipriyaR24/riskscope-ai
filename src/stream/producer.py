import json
from kafka import KafkaProducer
from src.data.generate_transactions import stream_batch

TOPIC = "transactions"
BOOTSTRAP = "localhost:9092"

def main():
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print("Producing transactions...")
    for txn in stream_batch(n_customers=300, n_txns=200):
        producer.send(TOPIC, txn)

    producer.flush()
    print("Done producing transactions.")

if __name__ == "__main__":
    main()
