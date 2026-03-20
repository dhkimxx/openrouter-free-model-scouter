import sqlite3
import psycopg2
import sys
import os

# Source DB path
SQLITE_DB = sys.argv[1] if len(sys.argv) > 1 else "../results/scouter.db"

# Destination DB connect string
# For local migration: postgresql://postgres:postgrespassword@localhost:5432/scouter
PG_URI = os.environ.get(
    "OPENROUTER_SCOUT_DB_URI", 
    "postgresql://postgres:postgrespassword@localhost:5432/scouter"
)

def migrate():
    print(f"Source SQLite DB: {SQLITE_DB}")
    print(f"Destination PG URI: {PG_URI}")

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()
    
    # Connect to Postgres
    try:
        pg_conn = psycopg2.connect(PG_URI)
        pg_cur = pg_conn.cursor()
    except Exception as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        return

    # Migrate runs
    sqlite_cur.execute("SELECT * FROM runs")
    runs = sqlite_cur.fetchall()
    print(f"Migrating {len(runs)} runs...")
    
    for row in runs:
        pg_cur.execute("SELECT 1 FROM runs WHERE id = %s", (row['id'],))
        if not pg_cur.fetchone():
            pg_cur.execute(
                "INSERT INTO runs (id, run_datetime) VALUES (%s, %s)",
                (row['id'], row['run_datetime'])
            )
            
    # Update sequence for runs
    pg_cur.execute("SELECT MAX(id) FROM runs")
    max_run_id = pg_cur.fetchone()[0]
    if max_run_id:
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('runs', 'id'), %s)", (max_run_id,))

    # Migrate healthchecks
    sqlite_cur.execute("SELECT * FROM healthchecks")
    hcs = sqlite_cur.fetchall()
    print(f"Migrating {len(hcs)} healthchecks...")
    
    for row in hcs:
        ok_val = bool(row['ok'])
        pg_cur.execute("SELECT 1 FROM healthchecks WHERE id = %s", (row['id'],))
        if not pg_cur.fetchone():
            pg_cur.execute(
                """INSERT INTO healthchecks (id, run_id, model_id, ok, http_status, error_category, latency_ms)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (row['id'], row['run_id'], row['model_id'], ok_val, row['http_status'], row['error_category'], row['latency_ms'])
            )

    # Update sequence for healthchecks
    pg_cur.execute("SELECT MAX(id) FROM healthchecks")
    max_hc_id = pg_cur.fetchone()[0]
    if max_hc_id:
        pg_cur.execute("SELECT setval(pg_get_serial_sequence('healthchecks', 'id'), %s)", (max_hc_id,))

    pg_conn.commit()
    print("Migration complete!")
    
    pg_cur.close()
    pg_conn.close()
    sqlite_conn.close()

if __name__ == "__main__":
    if not os.path.exists(SQLITE_DB):
        print(f"SQLite DB not found at: {SQLITE_DB}")
        sys.exit(1)
    migrate()
