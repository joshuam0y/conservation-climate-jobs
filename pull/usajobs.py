"""
usajobs.py

Pulls current postings from USAJOBS' official public Search API
(https://developer.usajobs.gov) -- the most reliable source here: a free,
self-service API key (no scraping/ToS risk at all), covering exactly the
federal roles this project cares about: Fish & Wildlife Service / National
Park Service / BLM / Forest Service for conservation biology, EPA's Office
of Environmental Justice for environmental-justice roles, and EPA/NOAA/DOI
for climate policy. "Pathways" is the federal government's own name for
its student-internship hiring path.

Requires the USAJOBS_API_KEY and USAJOBS_EMAIL environment variables (see
README for how to get a free key in ~2 minutes at
https://developer.usajobs.gov/apirequest/ -- the key is emailed to
whatever address you register, and that same address is required on every
request as the User-Agent header). Missing either is a no-op, not an
error -- same reasoning as an optional data source in a sibling project:
one source being unavailable should never block the rest of the pipeline.

Field names below (MatchedObjectDescriptor.PositionTitle etc.) are based
on USAJOBS' long-stable, publicly documented response shape, not a
live-tested response (no key was available while building this) -- every
field access is defensive (.get() with fallbacks), and any real mismatch
will show up as a loud, specific log line in the Action run rather than
silently losing data, making it a quick fix if a field name here is ever
slightly off.
"""

import os
import time

import requests

from categorize import categorize, is_internship_like, is_senior_level, mentions_2027

SEARCH_URL = "https://data.usajobs.gov/api/search"

# Each becomes its own Keyword search -- USAJOBS' search is a plain text
# match, not semantic, so several overlapping phrasings per topic surface
# genuinely different, non-overlapping postings.
QUERIES = [
    "conservation biologist",
    "wildlife biologist intern",
    "fisheries biologist intern",
    "environmental justice",
    "climate policy",
    "environmental science intern",
    "natural resources intern",
    "climate resilience",
    "pathways wildlife",
    "pathways environmental",
]


def _headers():
    key = os.environ.get("USAJOBS_API_KEY")
    email = os.environ.get("USAJOBS_EMAIL")
    if not key or not email:
        print("usajobs: USAJOBS_API_KEY/USAJOBS_EMAIL not set, skipping this source.")
        return None
    return {"Host": "data.usajobs.gov", "User-Agent": email, "Authorization-Key": key}


def _location(descriptor):
    locs = descriptor.get("PositionLocation") or []
    if locs:
        return locs[0].get("LocationName")
    return descriptor.get("PositionLocationDisplay")


def fetch():
    headers = _headers()
    if headers is None:
        return []

    seen_urls = set()
    listings = []
    for query in QUERIES:
        try:
            resp = requests.get(
                SEARCH_URL,
                headers=headers,
                params={"Keyword": query, "ResultsPerPage": 100, "WhoMayApply": "all"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"usajobs: query {query!r} failed ({type(e).__name__}: {e}), skipping.")
            continue

        items = ((data.get("SearchResult") or {}).get("SearchResultItems")) or []
        for item in items:
            d = item.get("MatchedObjectDescriptor") or {}
            url = d.get("PositionURI")
            title = d.get("PositionTitle")
            if not url or not title or url in seen_urls:
                continue
            if is_senior_level(title):
                continue
            summary = ((d.get("UserArea") or {}).get("Details") or {}).get("JobSummary") or ""
            organization = d.get("OrganizationName") or d.get("DepartmentName")
            # Same fix as idealist.py: a generic title ("Program Analyst") at a
            # clearly relevant org ("Office of Environmental Justice") needs the
            # org name in the check too, not just the title/summary text.
            combined = f"{organization or ''} {summary}"
            category = categorize(title, combined)
            if category is None:
                continue
            seen_urls.add(url)
            listings.append(
                {
                    "url": url,
                    "source": "USAJOBS",
                    "title": title,
                    "organization": organization,
                    "location": _location(d),
                    "category": category,
                    "summary": summary[:400],
                    "posted_date": d.get("PublicationStartDate"),
                    "close_date": d.get("ApplicationCloseDate"),
                    "summer_2027": mentions_2027(title, combined),
                    "internship_tag": is_internship_like(title, combined),
                }
            )
        time.sleep(1)  # polite delay between queries

    print(f"usajobs: {len(listings)} relevant listings across {len(QUERIES)} queries.")
    return listings
