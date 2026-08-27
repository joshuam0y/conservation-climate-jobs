"""
idealist.py

Idealist.org has no self-service API or RSS feed (its "Open Network API"
is a gated B2B sales product for volunteering data only -- checked
directly, not assumed) and its search results are rendered client-side --
confirmed live: the raw page source has zero listings, only an app shell.
Playwright renders the page like a real browser so the same results a
person would see are what gets scraped. robots.txt only disallows
third-party-login pages and blocks the AI-training-specific
Google-Extended bot from /en/careers/ -- general job search/listing pages
aren't disallowed for a normal crawler.

Two verified, separate sections/URL families, NOT one filtered search --
confirmed live (a `type=INTERNSHIP` query param on /en/jobs silently does
nothing; every result still comes back "Full Time"):
  - /en/internships?q=... -> individual postings at /en/nonprofit-internship/...
  - /en/jobs?q=...        -> individual postings at /en/nonprofit-job/...
Both are searched; is_internship_like() is a TAG (shown as a badge), not a
hard filter -- an earlier version dropped anything not literally titled
"intern"/"fellow"/etc, which threw away real, junior-appropriate roles at
the right kind of organization (confirmed live: 83 raw results for these
6 terms on /en/jobs alone, titles like "Conservation Organizer" at
$39-46k/year -- clearly an early-career nonprofit role, just not spelled
"internship"). categorize() is what actually gates relevance; the
internship tag just flags which of those relevant results are more likely
to literally be internship/fellowship-tier for someone filtering for that.

Selectors deliberately key off the URL PATH pattern
(/en/nonprofit-internship/, /en/nonprofit-job/), not CSS classes -- the
classes on this page are build-generated (styled-components hashes, e.g.
"sc-h2o8w6-5 wnNFX") and will change on Idealist's next deploy; the URL
routing scheme is far more stable. Each result anchor's own innerText
already contains title + org + location + posted-date on separate lines
(verified live), so no DOM-walking is needed to assemble a listing.

Kept deliberately narrow -- a handful of category searches, one page of
results per query, a capped wait for network idle -- this is a personal
aggregator checked once or twice a day, not a bulk index of the site.
"""

import re
import time
from datetime import datetime, timedelta, timezone

from categorize import categorize, is_fellowship_title, is_internship_like, is_postdoc_or_phd, is_senior_level, mentions_2027

SEARCH_TERMS = [
    "conservation",
    "wildlife",
    "environmental justice",
    "climate policy",
    "environmental",
    "climate",
]

SECTIONS = [
    ("https://www.idealist.org/en/internships?q={q}", "/en/nonprofit-internship/"),
    ("https://www.idealist.org/en/jobs?q={q}", "/en/nonprofit-job/"),
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


POSTED_RE = re.compile(r"posted\s+(today|yesterday|(\d+)\s+days?\s+ago)", re.IGNORECASE)


def _parse_card_text(text):
    """Splits an anchor's innerText into (title, organization, detail_line).
    Line count varies (salary line is sometimes absent), so only the first
    two lines (always title, then organization -- verified across many
    live samples) are trusted positionally; everything else is folded into
    one free-text detail line for display rather than parsed further. The
    "Posted N days ago" line is dropped here -- _parse_posted_date() turns
    it into a real date shown separately, so keeping it in detail too just
    duplicated the same information on every card."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return None, None, ""
    title = lines[0]
    org = lines[1] if len(lines) > 1 else None
    rest = [l for l in lines[2:] if not POSTED_RE.search(l)]
    detail = " · ".join(rest)
    return title, org, detail


def _parse_posted_date(detail):
    """Idealist shows a relative "Posted N days ago" string, not a real
    date -- converts it to an actual ISO date (as of scrape time) so it
    displays the same way as USAJOBS' own real PublicationStartDate."""
    m = POSTED_RE.search(detail or "")
    if not m:
        return None
    token = m.group(1).lower()
    if token == "today":
        days = 0
    elif token == "yesterday":
        days = 1
    else:
        days = int(m.group(2))
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def fetch():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("idealist: playwright not installed, skipping this source.")
        return []

    listings = []
    seen_urls = set()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(user_agent=USER_AGENT)
            for url_tmpl, path_marker in SECTIONS:
                for term in SEARCH_TERMS:
                    url = url_tmpl.format(q=term.replace(" ", "+"))
                    try:
                        page.goto(url, timeout=45000, wait_until="networkidle")
                        page.wait_for_timeout(1500)  # let the results list finish painting
                        anchors = page.query_selector_all(f'a[href*="{path_marker}"]')
                        for a in anchors:
                            href = a.get_attribute("href") or ""
                            if path_marker not in href:
                                continue
                            full_url = href if href.startswith("http") else "https://www.idealist.org" + href
                            if full_url in seen_urls:
                                continue
                            raw_text = a.inner_text() or ""
                            title, org, detail = _parse_card_text(raw_text)
                            if not title:
                                continue
                            if is_senior_level(title):
                                continue
                            # The organization name carries the actual keyword for a
                            # lot of real postings (e.g. "The Conservation Law
                            # Foundation", "World Wildlife Fund") when the title
                            # itself is generic ("Legal Fellow", "Program
                            # Coordinator") -- dropping org from this check silently
                            # threw those listings away entirely (caught live: a
                            # real "Charlotte E. Ray Legal Fellowship" at The
                            # Conservation Law Foundation categorized as None and
                            # vanished until org was included here).
                            combined = f"{org or ''} {detail}"
                            if is_postdoc_or_phd(title, combined):
                                continue
                            category = categorize(title, combined)
                            if category is None:
                                continue
                            seen_urls.add(full_url)
                            listings.append(
                                {
                                    "url": full_url,
                                    "source": "Idealist",
                                    "title": title,
                                    "organization": org,
                                    "location": detail or None,
                                    "category": category,
                                    "summary": "",
                                    "posted_date": _parse_posted_date(raw_text),
                                    "close_date": None,
                                    "summer_2027": mentions_2027(title, combined),
                                    "internship_tag": is_internship_like(title, combined),
                    "content_type": "fellowship" if is_fellowship_title(title) else "job",
                                }
                            )
                    except Exception as e:
                        print(f"idealist: {url} failed ({type(e).__name__}: {e}), skipping.")
                    time.sleep(2)  # polite delay between page loads
            browser.close()
    except Exception as e:
        print(f"idealist: browser launch failed ({type(e).__name__}: {e}), skipping this source entirely.")
        return []

    print(f"idealist: {len(listings)} relevant listings across {len(SEARCH_TERMS)} terms x {len(SECTIONS)} sections.")
    return listings
