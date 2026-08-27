"""
conferences.py

Conferences are handled differently from every other source here: this is
a small, manually curated, periodically-updated list, not a live scraper.
Three reasons:

1. They're infrequent, mostly-annual events announced months ahead --
   there's no need to re-discover them hourly the way job postings churn.
2. A wrong date here is much worse than a stale job listing (someone
   could plan travel around it), so accuracy matters more than
   automation for this content type.
3. General-purpose conference directories (checked Clocate.com live) mix
   real, relevant results with a lot of noise from unrelated academic
   fields sharing the same acronyms (its own "conservation biology"
   category surfaced an "International Conference on Cell Biology" under
   the same ICCB acronym) -- not reliable enough to trust unsupervised.

Every entry below was verified via a live search at the time it was
added, not guessed. Re-verify dates periodically (conferences do
occasionally shift) and add more here directly -- this list is the
entire "database," there's no separate admin UI.
"""

from datetime import datetime, timezone

CONFERENCES = [
    {
        "url": "https://conbio.org/mini-sites/iccb-2027/",
        "title": "ICCB 2027: International Congress for Conservation Biology",
        "organization": "Society for Conservation Biology",
        "location": "Puebla, Mexico",
        "category": "conservation_biology",
        "event_start": "2027-06-27",
        "event_end": "2027-07-01",
        "summary": "SCB's flagship global conservation science congress, co-hosted by the Latin America & Caribbean and North America regions this cycle.",
    },
    {
        "url": "https://wildlife.org/annual-conference/",
        "title": "The Wildlife Society Annual Conference 2027",
        "organization": "The Wildlife Society",
        "location": "Sacramento, CA",
        "category": "conservation_biology",
        "event_start": "2027-10-17",
        "event_end": "2027-10-21",
        "summary": "The largest annual gathering of wildlife professionals in North America -- strong for networking into field/agency wildlife biology roles.",
    },
    {
        "url": "https://conference.naaee.org/",
        "title": "NAAEE 2026 Annual Conference",
        "organization": "North American Association for Environmental Education",
        "location": "Portland, OR",
        "category": "other",
        "event_start": "2026-10-06",
        "event_end": "2026-10-09",
        "summary": "The main annual conference for environmental education practitioners and researchers. 2027 dates not yet announced as of when this was added.",
    },
    {
        "url": "https://www.climateweeknyc.org/",
        "title": "Climate Week NYC 2026",
        "organization": "Climate Group",
        "location": "New York, NY",
        "category": "climate_policy",
        "event_start": "2026-09-20",
        "event_end": "2026-09-27",
        "summary": "One of the largest annual climate policy/advocacy convenings in the world, run alongside the UN General Assembly -- heavy on policy panels and networking.",
    },
    {
        "url": "https://conference.bioneers.org/",
        "title": "Bioneers Conference 2026",
        "organization": "Bioneers",
        "location": "Berkeley, CA",
        "category": "other",
        "event_start": "2026-03-26",
        "event_end": "2026-03-28",
        "summary": "A broad environmental/sustainability leadership conference spanning conservation, climate, and environmental justice tracks.",
    },
]


def fetch():
    today = datetime.now(timezone.utc).date().isoformat()
    listings = []
    for c in CONFERENCES:
        if c["event_end"] < today:
            continue  # a past conference isn't useful to show, even if still in this list
        listings.append(
            {
                "url": c["url"],
                "source": "Curated",
                "title": c["title"],
                "organization": c["organization"],
                "location": c["location"],
                "category": c["category"],
                "summary": c["summary"],
                "posted_date": None,
                "close_date": None,
                "event_start": c["event_start"],
                "event_end": c["event_end"],
                "summer_2027": "2027" in c["event_start"] or "2027" in c["event_end"],
                "internship_tag": False,
                "content_type": "conference",
            }
        )
    print(f"conferences: {len(listings)} upcoming (of {len(CONFERENCES)} curated total).")
    return listings
