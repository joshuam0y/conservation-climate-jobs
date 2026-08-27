"""
conservationjobboard.py

ConservationJobBoard.com is plain server-rendered HTML (confirmed live:
a bare `requests.get` returns real listings, no browser needed) with a
real keyword search endpoint (`/intermediate-search?kw=...`, found in the
page's own search form) and unusually rich per-listing markup: each
listing's own anchor carries `experience` ("entry-level"/"mid-level"/
"high-level"), `job_type`, `location`, and `company` as real HTML
attributes, not just text to guess from -- `experience="entry-level"` is
a direct, reliable internship/entry-level signal, used alongside (not
instead of) categorize.py's own internship-keyword check.

Titles from this source skew heavily toward actual field/wildlife/
fisheries biology work ("Fisheries Wildlife Biologist," "Desert
Biologist," "Land Stewardship & Restoration Ecologist") -- exactly the
Conservation Biology category Idealist's nonprofit-advocacy postings
mostly don't produce.
"""

import re
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

from categorize import categorize, is_internship_like, is_postdoc_or_phd, is_senior_level, mentions_2027

SEARCH_URL = "https://www.conservationjobboard.com/intermediate-search"

QUERIES = [
    "wildlife biologist",
    "conservation",
    "fisheries biologist",
    "ecologist",
    "environmental justice",
    "climate policy",
    "natural resources",
    "restoration",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

RELATIVE_TIME_RE = re.compile(r"(today|yesterday|(\d+)\s+days?\s+ago)", re.IGNORECASE)
DEADLINE_RE = re.compile(r"deadline", re.IGNORECASE)


def _parse_relative_time(text):
    m = RELATIVE_TIME_RE.search(text or "")
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


def _parse_deadline(text):
    """"Deadline: Sep 11, 2026" -> 2026-09-11. Falls back to None (not every
    listing has one) rather than guessing."""
    m = re.search(r"deadline\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})", text or "", re.IGNORECASE)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1).replace(",", ""), "%b %d %Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(m.group(1).replace(",", ""), "%B %d %Y").strftime("%Y-%m-%d")
        except ValueError:
            return None


def _parse_article(article):
    link = article.select_one("a.gtag-job-link")
    if not link or not link.get("href"):
        return None
    title = link.get_text(strip=True)
    if not title:
        return None
    url = link["href"].split("?")[0]  # strip tracking query params (?from=feat-1 etc.)
    company_el = article.select_one("h3")
    company = company_el.get_text(strip=True) if company_el else link.get("company", "").replace("-", " ").title()
    location_el = article.select_one("h4")
    location = location_el.get_text(strip=True) if location_el else link.get("location", "").title()

    full_text = article.get_text(" ", strip=True)
    posted_date = None
    time_el = article.select_one(".listing__job__time")
    if time_el:
        posted_date = _parse_relative_time(time_el.get_text())
    close_date = _parse_deadline(full_text)

    return {
        "url": url,
        "title": title,
        "company": company,
        "location": location,
        "posted_date": posted_date,
        "close_date": close_date,
        "experience": (link.get("experience") or "").lower(),
    }


def fetch():
    listings = []
    seen_urls = set()
    for query in QUERIES:
        try:
            resp = requests.get(
                SEARCH_URL, params={"kw": query}, headers={"User-Agent": USER_AGENT}, timeout=30
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"conservationjobboard: query {query!r} failed ({type(e).__name__}: {e}), skipping.")
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        for article in soup.select("article"):
            parsed = _parse_article(article)
            if not parsed or parsed["url"] in seen_urls:
                continue
            title, company = parsed["title"], parsed["company"]
            if is_senior_level(title):
                continue
            combined = f"{company} {parsed['location']}"
            if is_postdoc_or_phd(title, combined):
                continue
            category = categorize(title, combined)
            if category is None:
                continue
            seen_urls.add(parsed["url"])
            listings.append(
                {
                    "url": parsed["url"],
                    "source": "ConservationJobBoard",
                    "title": title,
                    "organization": company,
                    "location": parsed["location"],
                    "category": category,
                    "summary": "",
                    "posted_date": parsed["posted_date"],
                    "close_date": parsed["close_date"],
                    "summer_2027": mentions_2027(title, combined),
                    # experience="entry-level" is a direct signal from the
                    # site itself, more reliable than keyword-guessing --
                    # either one is enough to tag it.
                    "internship_tag": parsed["experience"] == "entry-level" or is_internship_like(title, combined),
                }
            )
        time.sleep(1)  # polite delay between queries

    print(f"conservationjobboard: {len(listings)} relevant listings across {len(QUERIES)} queries.")
    return listings
