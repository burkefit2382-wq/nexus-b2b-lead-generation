from pathlib import Path


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def run_migrations(database_url: str) -> None:
    if not database_url:
        return

    import psycopg

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(schema_sql)
