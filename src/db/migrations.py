import duckdb

DB_PATH = "risklens.duckdb"


def migrate():
    with duckdb.connect(DB_PATH) as con:
        # Existing table must exist already: scored_transactions

        # --- Cases table ---
        con.execute(
            """
        CREATE TABLE IF NOT EXISTS cases (
            case_id VARCHAR,
            transaction_id VARCHAR,
            created_ts VARCHAR,
            status VARCHAR,          -- NEW / IN_REVIEW / ESCALATED / CLOSED
            priority VARCHAR,        -- LOW / MEDIUM / HIGH
            owner VARCHAR,
            disposition VARCHAR,     -- FRAUD / NOT_FRAUD / NEEDS_INFO
            notes VARCHAR
        );
        """
        )

        # --- Case events (audit trail) ---
        con.execute(
            """
        CREATE TABLE IF NOT EXISTS case_events (
            case_id VARCHAR,
            ts VARCHAR,
            event_type VARCHAR,      -- CREATED / STATUS_CHANGED / NOTE_ADDED / CLOSED
            payload VARCHAR
        );
        """
        )

        # --- Analyst labels (feedback loop) ---
        con.execute(
            """
        CREATE TABLE IF NOT EXISTS labels (
            transaction_id VARCHAR,
            label INTEGER,           -- 1 fraud, 0 not fraud
            ts VARCHAR,
            analyst VARCHAR
        );
        """
        )

        print("✅ DB migration complete")


if __name__ == "__main__":
    migrate()
