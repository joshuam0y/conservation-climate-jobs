"""
ecojobs.py

EcoJobs.com is plain server-rendered WordPress HTML (a "Content Views"-
style plugin grid, confirmed live via a bare `requests.get`). No working
keyword search was found -- the standard WordPress `?s=` query returned
zero of this plugin's own listings (it doesn't hook into core search,
and reverse-engineering its AJAX endpoint wasn't worth it for a ~25-listing
site) -- so this just scrapes the homepage's own grid and lets
categorize() do the actual relevance filtering, same as every other
source ultimately does anyway.

Each listing's own <time datetime="..."> is a real ISO timestamp, not a
relative "N days ago" string to parse -- the cleanest date source of any
scraper here.
"""

import requests
from bs4 import BeautifulSoup

from categorize import categorize, is_internship_like, is_postdoc_or_phd, is_senior_level, mentions_2027

HOME_URL = "https://ecojobs.com/"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _parse_item(item):
    link = item.select_one("h4.pt-cv-title a")
    if not link or not link.get("href"):
        return None
    title = link.get_text(strip=True)
    if not title:
        return None
    location_el = item.select_one(".pt-cv-ctf-_job_location .pt-cv-ctf-value")
    location = location_el.get_text(strip=True) if location_el else None
    content_el = item.select_one(".pt-cv-content")
    summary = ""
    if content_el:
        summary = content_el.get_text(" ", strip=True)
        # Strip the trailing "Read More" link text this element also contains.
        summary = summary.replace("Read More", "").strip()
    time_el = item.select_one(".entry-date time[datetime]")
    posted_date = time_el["datetime"][:10] if time_el and time_el.get("datetime") else None

    return {"url": link["href"], "title": title, "location": location, "summary": summary, "posted_date": posted_date}


def fetch():
    try:
        resp = requests.get(HOME_URL, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"ecojobs: fetch failed ({type(e).__name__}: {e}), skipping this source.")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    listings = []
    seen_urls = set()
    for item in soup.select(".pt-cv-content-item"):
        parsed = _parse_item(item)
        if not parsed or parsed["url"] in seen_urls:
            continue
        title = parsed["title"]
        if is_senior_level(title):
            continue
        combined = f"{parsed['location'] or ''} {parsed['summary']}"
        if is_postdoc_or_phd(title, combined):
            continue
        category = categorize(title, combined)
        if category is None:
            continue
        seen_urls.add(parsed["url"])
        listings.append(
            {
                "url": parsed["url"],
                "source": "EcoJobs",
                "title": title,
                "organization": None,  # not present in this plugin's grid view, only on the detail page
                "location": parsed["location"],
                "category": category,
                "summary": parsed["summary"][:400],
                "posted_date": parsed["posted_date"],
                "close_date": None,
                "summer_2027": mentions_2027(title, combined),
                "internship_tag": is_internship_like(title, combined),
            }
        )

    print(f"ecojobs: {len(listings)} relevant listings from the homepage grid.")
    return listings
