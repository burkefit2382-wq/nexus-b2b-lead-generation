"""
Standalone database migration runner for Nexus B2B.

Usage:
    python db/migrate.py

Reads DATABASE_URL from the environment, applies schema.sql idempotently.
Safe to run on every deploy – all DDL statements use IF NOT EXISTS / IF EXISTS.
"""

import os
import sys
from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def run() -> None:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("migrate.py: DATABASE_URL is not set – skipping migration.", flush=True)
        return

    try:
        import psycopg
    except ImportError:
        print("migrate.py: psycopg not installed – skipping migration.", flush=True)
        return

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    print(f"migrate.py: applying schema from {SCHEMA_PATH} …", flush=True)
    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(schema_sql)
        print("migrate.py: migration complete.", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"migrate.py: migration failed: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
