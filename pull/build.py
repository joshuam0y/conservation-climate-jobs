"""
build.py

Orchestrates one full refresh cycle: run every source scraper, upsert
results into the persistent SQLite store (preserving first_seen across
runs, bumping last_seen), age out anything not seen recently or past its
own application deadline, then render docs/index.html.

Adding a new source later is exactly: write a module with its own
fetch() -> list[dict] (see usajobs.py/idealist.py for the dict shape),
import it, and add it to SOURCES below.
"""

from datetime import datetime, timezone

import idealist
import usajobs
from db import get_conn, init_db
from render import write as render_write

# Not seen in this many days -> assume filled/expired/delisted and hide it.
# A source having an off day (rate-limited, a query returning fewer
# results than usual) shouldn't make a real posting flicker in and out,
# so this is deliberately more forgiving than "missing from today's run".
STALE_AFTER_DAYS = 5

SOURCES = [usajobs.fetch, idealist.fetch]


def upsert(conn, listings):
    now = datetime.now(timezone.utc).isoformat()
    for item in listings:
        conn.execute(
            """
            INSERT INTO listings (url, source, title, organization, location, category, summary,
                                   posted_date, close_date, summer_2027, internship_tag,
                                   first_seen, last_seen, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(url) DO UPDATE SET
                title=excluded.title, organization=excluded.organization, location=excluded.location,
                category=excluded.category, summary=excluded.summary, posted_date=excluded.posted_date,
                close_date=excluded.close_date, summer_2027=excluded.summer_2027,
                internship_tag=excluded.internship_tag, last_seen=excluded.last_seen, active=1
            """,
            (
                item["url"], item["source"], item["title"], item.get("organization"), item.get("location"),
                item["category"], item.get("summary") or "", item.get("posted_date"), item.get("close_date"),
                1 if item.get("summer_2027") else 0, 1 if item.get("internship_tag") else 0, now, now,
            ),
        )
    conn.commit()


def age_out_stale(conn):
    conn.execute(
        f"""
        UPDATE listings SET active = 0
        WHERE active = 1
          AND (
            julianday('now') - julianday(last_seen) > {STALE_AFTER_DAYS}
            OR (close_date IS NOT NULL AND close_date < date('now'))
          )
        """
    )
    conn.commit()


def run():
    init_db()
    conn = get_conn()

    all_listings = []
    for fetch in SOURCES:
        try:
            all_listings.extend(fetch())
        except Exception as e:
            # One source's total failure (a network issue, a site layout
            # change) must never block the others or leave the site
            # un-rebuilt -- same reasoning as every optional-source guard
            # elsewhere in these sibling projects.
            print(f"build: source {fetch.__module__} failed entirely ({type(e).__name__}: {e}), skipping.")

    upsert(conn, all_listings)
    age_out_stale(conn)

    active_count = conn.execute("SELECT COUNT(*) FROM listings WHERE active = 1").fetchone()[0]
    conn.close()

    render_write()
    print(f"build: {active_count} active listings after this run.")


if __name__ == "__main__":
    run()
