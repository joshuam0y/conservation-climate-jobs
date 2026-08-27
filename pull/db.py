"""
db.py

SQLite is the persistent, cross-run store -- committed to git (like the
sibling news-monitor project's monitor.db) rather than rebuilt from
scratch every run, so "first seen" dates survive and a listing that
disappears from a source's search results (filled, expired, or just
paginated out) still shows in history until explicitly pruned.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "listings.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS listings (
            url TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            organization TEXT,
            location TEXT,
            category TEXT NOT NULL,
            summary TEXT,
            posted_date TEXT,
            close_date TEXT,
            summer_2027 INTEGER NOT NULL DEFAULT 0,
            internship_tag INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    # Lightweight migration for columns added after the table already
    # existed in production (this repo's own listings.db is committed to
    # git, not rebuilt from scratch) -- same pattern as monitor.db in a
    # sibling project. content_type distinguishes a job/internship
    # posting from a fellowship or a conference; event_start/event_end
    # are conference-only (a job's timeline is posted_date/close_date,
    # a conference's is when it actually happens).
    existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(listings)")}
    for col, ddl in [
        ("content_type", "TEXT NOT NULL DEFAULT 'job'"),
        ("event_start", "TEXT"),
        ("event_end", "TEXT"),
    ]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE listings ADD COLUMN {col} {ddl}")
    conn.commit()
    conn.close()
