# Conservation & Climate Jobs Tracker

A live, auto-updating list of internships, fellowships, and entry-level roles in
**Conservation Biology**, **Environmental Justice**, and **Climate Policy** (plus a
catch-all **Other** category for anything environmental that doesn't fit those three) —
pulled automatically from multiple job sites, refreshed twice a day, with a highlight
for anything that mentions Summer 2027.

**Live site:** https://joshuam0y.github.io/conservation-climate-jobs/

No sign-up, no app to install — just open the link. Filter by category with the sidebar
nav, search by keyword, or check "Summer 2027 mentioned" to narrow down to postings that
explicitly say so (most Summer 2027 postings won't open until later — the site is built
to keep collecting them as they appear over the coming months, not just today).

Postdoctoral and PhD-required listings are excluded automatically, and so are literal
VP/C-suite/Executive-Director titles — this is scoped for a Master's-level candidate.

## How it works

Every row links straight to the original posting on its source site — nothing is
hosted here beyond a short summary, so always apply on the real site.

**Sources today:**
- [USAJOBS.gov](https://www.usajobs.gov/) — the federal government's official job site.
  Covers roles like Fish & Wildlife Service / National Park Service (conservation
  biology), EPA's Office of Environmental Justice, and EPA/NOAA/DOI (climate policy).
  "Pathways" is the federal government's own name for its student-internship hiring
  path. Needs a free API key, see setup section below.
- [Idealist.org](https://www.idealist.org/) — one of the largest nonprofit/mission-driven
  job boards, strong for environmental-justice and climate-advocacy organizations.
- [ConservationJobBoard.com](https://www.conservationjobboard.com/) — plain HTML, no
  browser needed, real keyword search, and the strongest source here for actual field/
  wildlife/fisheries biology roles.
- [EcoJobs.com](https://ecojobs.com/) — plain HTML, scraped from its homepage listing
  grid (no working keyword search was found on this one).

Not every legitimate-looking job board made the cut. LinkedIn and Handshake are
deliberately excluded: LinkedIn's terms of service explicitly prohibit automated
scraping and they've pursued real legal action over it (hiQ v. LinkedIn); Handshake is
authenticated, university-gated access, not a public page. A few other candidates
(environmentalcareer.com, Climatebase, the Society for Conservation Biology's career
center) were checked and turned out to be blocked or gated at the time this was built —
see the "Adding another job site" section below before trying them again.

Categorization into the 4 buckets is automatic (keyword-based), so it can occasionally
miscategorize a listing or miss one that's phrased unusually — if something looks off,
the source link always shows the real, unfiltered posting.

## One-time setup: USAJOBS API key

USAJOBS listings won't show up until this is added — everything else works without it.

1. Go to https://developer.usajobs.gov/apirequest/ and request a key (free, instant,
   just needs an email address).
2. In this repo: **Settings → Secrets and variables → Actions → New repository secret**
   and add two secrets:
   - `USAJOBS_API_KEY` — the key from step 1
   - `USAJOBS_EMAIL` — the email address you registered it with (USAJOBS requires this
     exact address on every request)
3. Re-run the workflow (**Actions → Refresh listings → Run workflow**), or just wait for
   the next scheduled refresh.

## Refresh schedule

Runs automatically twice a day (`.github/workflows/refresh.yml`) via GitHub Actions —
scrapes every source, updates `listings.db`, rebuilds `docs/index.html`, and deploys to
GitHub Pages. You can also trigger it manually any time from the **Actions** tab
("Refresh listings" → "Run workflow").

A listing that stops showing up in a source's results for 5 days straight (or whose
application deadline has passed, when a source provides one) is automatically hidden —
no manual cleanup needed.

## Adding another job site later

Each source is its own small file in `pull/` with one job: fetch listings and return
them as a list of dicts (see `pull/usajobs.py` or `pull/conservationjobboard.py` for the
exact shape). To add one:

1. Check it's actually usable first: is it public (no login), does its own
   `robots.txt`/terms of service allow this, and is the content server-rendered (a
   plain `requests.get` shows real listings) or does it need a browser (Playwright,
   like `pull/idealist.py`)?
2. Write `pull/<newsource>.py` with a `fetch()` function.
3. Reuse `pull/categorize.py`'s `categorize()` / `is_internship_like()` /
   `is_senior_level()` / `is_postdoc_or_phd()` / `mentions_2027()` so every source is
   judged by the same rules.
4. Add it to the `SOURCES` list in `pull/build.py`.

Checked and found not currently usable: LinkedIn and Handshake (see above), plus
environmentalcareer.com (blocked at the network level, at least from where this was
built), Climatebase.org (no public API; its "Open Network API" turned out to be a gated
B2B product for volunteer-matching data, not jobs), and the Society for Conservation
Biology's career center (returned an empty response, likely a bot-detection challenge
page). Worth re-checking occasionally in case that changes.

## Running it locally

```
pip install -r requirements.txt
python -m playwright install --with-deps chromium
python pull/build.py
```

Opens nothing automatically — the output is `docs/index.html`, open it directly in a
browser. `listings.db` (SQLite) is the persistent store between runs.
