"""
migrate_to_supabase.py — Migrate PixelVault prompts from SQLite to Supabase (PostgreSQL).

Usage:
    python tools/migrate_to_supabase.py

Environment variables (or set in .env):
    DATABASE_URL   PostgreSQL DSN for Supabase, e.g.
                   postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres

The script reads every row from the `prompts` table in pixelvault.db and upserts
it into the Supabase `prompts` table.  Duplicates (matched on `name`) are skipped
silently via ON CONFLICT DO NOTHING.

Dependencies:
    pip install psycopg2-binary python-dotenv
"""

import os
import sys
import sqlite3
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    sys.exit("psycopg2 is required.  Run: pip install psycopg2-binary")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional; fall back to real env vars


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SQLITE_PATH = Path(__file__).resolve().parent.parent / "pixelvault.db"

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    sys.exit(
        "ERROR: DATABASE_URL is not set.\n"
        "Export it before running:\n"
        "  export DATABASE_URL='postgresql://postgres:<password>"
        "@db.<ref>.supabase.co:5432/postgres'"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_prompts_from_sqlite(db_path: Path) -> list[dict]:
    """Return all rows from the SQLite prompts table as a list of dicts."""
    if not db_path.exists():
        sys.exit(f"ERROR: SQLite database not found at {db_path}")

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT industry, name, prompt_text, use_case, ratios, created_at FROM prompts ORDER BY id"
        )
        rows = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

    return rows


def insert_prompts_to_supabase(rows: list[dict], dsn: str) -> int:
    """
    Insert rows into Supabase prompts table.
    Returns the number of rows actually inserted (duplicates are skipped).
    """
    if not rows:
        print("No prompts found in SQLite — nothing to migrate.")
        return 0

    insert_sql = """
        INSERT INTO prompts (industry, name, prompt_text, use_case, ratios, created_at)
        VALUES %s
        ON CONFLICT DO NOTHING
    """

    values = [
        (
            row["industry"],
            row["name"],
            row["prompt_text"],
            row.get("use_case") or "",
            row.get("ratios") or "",
            row.get("created_at"),
        )
        for row in rows
    ]

    conn = psycopg2.connect(dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                execute_values(cur, insert_sql, values)
                inserted = cur.rowcount  # -1 when execute_values uses executemany path
    finally:
        conn.close()

    # psycopg2 execute_values does not always return an accurate rowcount via
    # the cursor; query the table directly for an honest count.
    return inserted


def count_supabase_prompts(dsn: str) -> int:
    conn = psycopg2.connect(dsn)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM prompts")
            return cur.fetchone()[0]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"Reading prompts from SQLite: {SQLITE_PATH}")
    rows = read_prompts_from_sqlite(SQLITE_PATH)
    print(f"  Found {len(rows)} prompt(s) in SQLite.")

    if not rows:
        print("Nothing to do.")
        return

    print(f"\nConnecting to Supabase: {DATABASE_URL[:40]}...")

    before = count_supabase_prompts(DATABASE_URL)
    print(f"  Rows in Supabase before migration : {before}")

    print(f"\nInserting {len(rows)} prompt(s) (duplicates skipped)...")
    for i, row in enumerate(rows, 1):
        print(f"  [{i:>2}/{len(rows)}] {row['industry']:<20} {row['name'][:60]}")

    insert_prompts_to_supabase(rows, DATABASE_URL)

    after = count_supabase_prompts(DATABASE_URL)
    newly_inserted = after - before

    print(f"\nMigration complete.")
    print(f"  Rows inserted : {newly_inserted}")
    print(f"  Rows skipped  : {len(rows) - newly_inserted}")
    print(f"  Total in table: {after}")


if __name__ == "__main__":
    main()
