"""
render.py

Renders listings.db into a single static docs/index.html -- plain f-string
templating (no Jinja/build step), inline CSS/JS, client-side filtering
only (no server calls). Deployed via GitHub Pages straight from docs/.

Layout is a sidebar + list, not a stat-tile-row + pill-filter-bar +
card-grid -- deliberately, per explicit feedback that the earlier version
looked like a reskinned sports dashboard (a pattern reused across several
unrelated projects this session) rather than its own thing. A sidebar
category nav (plain list items with a left-accent bar, not rounded pill
buttons) plus a single scannable list of rows is also just a better fit
for a jobs list specifically -- closer to how a real job board reads than
a grid of stat cards.

Category palette is the dataviz skill's own validated categorical theme
(references/palette.md), narrowed to 4 slots and re-validated for this
exact set: blue/orange/aqua/violet passes CVD separation under the
strictest all-pairs check in both light and dark mode. The one WARN
(aqua's contrast against a light surface) is mitigated the way the skill
requires -- every badge always carries its own text label, never a bare
color swatch.
"""

import html
from datetime import datetime, timezone

from categorize import CATEGORY_LABELS
from db import get_conn

CATEGORY_COLORS = {
    "conservation_biology": {"light": "#1baf7a", "dark": "#199e70"},
    "environmental_justice": {"light": "#eb6834", "dark": "#d95926"},
    "climate_policy": {"light": "#2a78d6", "dark": "#3987e5"},
    "other": {"light": "#4a3aa7", "dark": "#9085e9"},
}

SOURCE_LABELS = {
    "USAJOBS": "USAJOBS.gov",
    "Idealist": "Idealist.org",
    "ConservationJobBoard": "ConservationJobBoard.com",
    "EcoJobs": "EcoJobs.com",
}

# Built from basic primitives (circle/line/polygon/ellipse), not hand-drawn
# bezier paths -- easy to reason about correctness without a design tool,
# and rendering was checked with a real screenshot before shipping.
CATEGORY_ICONS = {
    "conservation_biology": (
        '<svg viewBox="0 0 24 24"><path d="M12 21c-4-1-7-5-7-10a9 9 0 0 1 9-8c5 0 9 3 9 8 0 6-6 9-6 9" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
        '<path d="M12 21V9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>'
    ),
    "environmental_justice": (
        '<svg viewBox="0 0 24 24"><line x1="12" y1="3" x2="12" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
        '<line x1="5" y1="6" x2="19" y2="6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
        '<line x1="8" y1="19" x2="16" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>'
        '<circle cx="5" cy="10" r="3" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<circle cx="19" cy="10" r="3" fill="none" stroke="currentColor" stroke-width="2"/></svg>'
    ),
    "climate_policy": (
        '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<ellipse cx="12" cy="12" rx="4" ry="9" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<line x1="3" y1="12" x2="21" y2="12" stroke="currentColor" stroke-width="2"/></svg>'
    ),
    "other": (
        '<svg viewBox="0 0 24 24"><polygon points="12,3 15,9 21,10 16.5,14.5 18,21 12,17.5 6,21 7.5,14.5 3,10 9,9" '
        'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>'
    ),
    "all": '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="7" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="2"/><rect x="13" y="4" width="7" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="2"/><rect x="4" y="13" width="7" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="2"/><rect x="13" y="13" width="7" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="2"/></svg>',
}


def _fmt_date(iso_str):
    if not iso_str:
        return None
    try:
        d = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return d.strftime("%b %-d, %Y")
    except Exception:
        return iso_str[:10]


def _row_html(row):
    cat = row["category"]
    cat_label = CATEGORY_LABELS.get(cat, "Other Environmental")
    source_label = SOURCE_LABELS.get(row["source"], row["source"])
    posted = _fmt_date(row["posted_date"])
    close = _fmt_date(row["close_date"])

    meta_bits = []
    if row["organization"]:
        meta_bits.append(html.escape(row["organization"]))
    if row["location"]:
        meta_bits.append(html.escape(row["location"]))
    meta_bits.append(source_label)
    meta_line = " &middot; ".join(meta_bits)

    date_bits = []
    if posted:
        date_bits.append(f"Posted {posted}")
    if close:
        date_bits.append(f"Closes {close}")
    date_line = " &middot; ".join(date_bits)

    tags_html = ""
    if row["internship_tag"]:
        tags_html += '<span class="tag tag-intern">Internship / entry-level</span>'
    if row["summer_2027"]:
        tags_html += '<span class="tag tag-2027">Summer 2027 mentioned</span>'

    search_blob = html.escape((row["title"] + " " + (row["organization"] or "") + " " + (row["location"] or "")).lower())

    return f"""
    <a class="job-row" href="{html.escape(row['url'])}" target="_blank" rel="noopener"
       data-category="{cat}" data-search="{search_blob}"
       data-2027="{'1' if row['summer_2027'] else '0'}" data-intern="{'1' if row['internship_tag'] else '0'}">
      <span class="job-row-icon" style="color:var(--cat-{cat})" title="{html.escape(cat_label)}">{CATEGORY_ICONS.get(cat, "")}</span>
      <span class="job-row-body">
        <span class="job-row-title">{html.escape(row['title'])}</span>
        <span class="job-row-meta">{meta_line}</span>
        {f'<span class="job-row-tags">{tags_html}</span>' if tags_html else ""}
      </span>
      <span class="job-row-date">{date_line}</span>
    </a>
    """


STYLE = """
<style>
  :root {
    color-scheme: light;
    --bg: #F7F6F1; --surface: #ffffff; --surface-2: #EFEDE4;
    --ink: #20241E; --ink-dim: #565C50; --ink-muted: #8B9084;
    --border: rgba(32,36,30,0.11); --shadow: 0 1px 2px rgba(32,36,30,.05), 0 8px 20px rgba(32,36,30,.05);
    --accent: #21603F; --accent-bg: rgba(33,96,63,0.10);
    --cat-conservation_biology: #128a5c; --cat-environmental_justice: #c85526;
    --cat-climate_policy: #1f63b3; --cat-other: #4a3aa7; --cat-all: #565C50;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --bg: #14170F; --surface: #1B1F17; --surface-2: #23281E;
      --ink: #EEF0E8; --ink-dim: #B7BEAC; --ink-muted: #7C8571;
      --border: rgba(255,255,255,0.09); --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 20px rgba(0,0,0,.35);
      --accent: #4FB287; --accent-bg: rgba(79,178,135,0.16);
      --cat-conservation_biology: #199e70; --cat-environmental_justice: #d97a4a;
      --cat-climate_policy: #5b9bdb; --cat-other: #9085e9; --cat-all: #B7BEAC;
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #14170F; --surface: #1B1F17; --surface-2: #23281E;
    --ink: #EEF0E8; --ink-dim: #B7BEAC; --ink-muted: #7C8571;
    --border: rgba(255,255,255,0.09); --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 20px rgba(0,0,0,.35);
    --accent: #4FB287; --accent-bg: rgba(79,178,135,0.16);
    --cat-conservation_biology: #199e70; --cat-environmental_justice: #d97a4a;
    --cat-climate_policy: #5b9bdb; --cat-other: #9085e9; --cat-all: #B7BEAC;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--ink); font-family: -apple-system, "Segoe UI", system-ui, sans-serif; }
  h1, h2, .brand { font-family: Georgia, "Iowan Old Style", "Times New Roman", serif; }

  header.site {
    display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap;
    max-width: 1180px; margin: 0 auto; padding: 28px 24px 18px; border-bottom: 1px solid var(--border);
  }
  .brand { font-size: 26px; font-weight: 700; letter-spacing: -0.01em; margin: 0; }
  .tagline { margin: 6px 0 0; color: var(--ink-dim); font-size: 13.5px; max-width: 62ch; line-height: 1.55; }
  .header-meta { font-size: 12px; color: var(--ink-muted); margin-top: 6px; }
  .theme-toggle {
    background: var(--surface-2); color: var(--ink); border: 1px solid var(--border);
    border-radius: 7px; padding: 7px 13px; font-size: 12.5px; font-weight: 600; cursor: pointer; font-family: inherit;
  }
  .theme-toggle:hover { background: var(--surface); }

  .layout { max-width: 1180px; margin: 0 auto; padding: 22px 24px 60px; display: flex; gap: 28px; align-items: flex-start; }

  .sidebar { width: 250px; flex: none; position: sticky; top: 20px; }
  .sidebar h2 { font-size: 13px; font-weight: 700; letter-spacing: 0.02em; margin: 0 0 8px; color: var(--ink-dim); }
  .nav-list { list-style: none; margin: 0 0 20px; padding: 0; }
  .nav-item {
    display: flex; align-items: center; gap: 9px; width: 100%; background: none; border: none;
    border-left: 3px solid transparent; text-align: left; padding: 8px 10px; font-size: 13.5px;
    font-weight: 600; color: var(--ink-dim); cursor: pointer; font-family: inherit; border-radius: 0 6px 6px 0;
  }
  .nav-item:hover { background: var(--surface-2); }
  .nav-item.on { border-left-color: var(--nav-color, var(--accent)); background: var(--surface-2); color: var(--ink); }
  .nav-item svg { width: 15px; height: 15px; flex: none; color: var(--nav-color, var(--ink-muted)); }
  .nav-item .count { margin-left: auto; font-size: 11.5px; color: var(--ink-muted); font-weight: 700; }

  .side-search {
    width: 100%; padding: 8px 10px; border: none; border-bottom: 2px solid var(--border);
    background: transparent; color: var(--ink); font-size: 13.5px; font-family: inherit; margin-bottom: 14px;
  }
  .side-search:focus { outline: none; border-bottom-color: var(--accent); }
  .side-toggle { display: flex; align-items: center; gap: 7px; font-size: 12.5px; color: var(--ink-dim); margin-bottom: 8px; }
  .sidebar-footer { font-size: 11.5px; color: var(--ink-muted); margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--border); line-height: 1.6; }

  .main { flex: 1; min-width: 0; }
  #resultCount { font-size: 12.5px; color: var(--ink-muted); margin-bottom: 10px; }

  .job-list { display: flex; flex-direction: column; }
  .job-row {
    display: flex; align-items: flex-start; gap: 12px; padding: 13px 4px; border-bottom: 1px solid var(--border);
    text-decoration: none; color: inherit;
  }
  .job-row:hover { background: var(--surface-2); }
  .job-row-icon {
    flex: none; width: 30px; height: 30px; border-radius: 8px; background: var(--surface-2);
    display: flex; align-items: center; justify-content: center; margin-top: 1px;
  }
  .job-row-icon svg { width: 16px; height: 16px; }
  .job-row-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
  .job-row-title { font-size: 14.5px; font-weight: 700; color: var(--ink); }
  .job-row-meta { font-size: 12.5px; color: var(--ink-dim); }
  .job-row-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 2px; }
  .tag { font-size: 10.5px; font-weight: 700; border-radius: 5px; padding: 2px 7px; }
  .tag-intern { background: var(--surface-2); color: var(--ink-dim); border: 1px solid var(--border); }
  .tag-2027 { background: var(--accent-bg); color: var(--accent); }
  .job-row-date { flex: none; font-size: 11.5px; color: var(--ink-muted); text-align: right; white-space: nowrap; padding-top: 2px; }

  .empty-state { text-align: center; padding: 60px 20px; color: var(--ink-muted); }
  footer.site-footer {
    max-width: 1180px; margin: 10px auto 0; padding: 16px 24px 30px; font-size: 12px; color: var(--ink-muted); line-height: 1.6;
  }
  footer.site-footer a { color: var(--accent); }

  @media (max-width: 760px) {
    .layout { flex-direction: column; }
    .sidebar { width: 100%; position: static; }
    .nav-list { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 12px; }
    .nav-item { width: auto; border-left: none; border-bottom: 3px solid transparent; border-radius: 6px 6px 0 0; }
    .nav-item.on { border-bottom-color: var(--nav-color, var(--accent)); }
    .job-row-date { display: none; }
  }
</style>
"""

SCRIPT = """
<script>
function initTheme() {
  const saved = localStorage.getItem('theme');
  if (saved) document.documentElement.setAttribute('data-theme', saved);
  const btn = document.getElementById('themeToggle');
  function label() {
    const cur = document.documentElement.getAttribute('data-theme');
    const dark = cur ? cur === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    btn.textContent = dark ? 'Switch to light' : 'Switch to dark';
  }
  btn.addEventListener('click', function () {
    const cur = document.documentElement.getAttribute('data-theme');
    const dark = cur ? cur === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    const next = dark ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    label();
  });
  label();
}

let activeCategory = 'all';
function applyFilters() {
  const search = document.getElementById('searchBox').value.trim().toLowerCase();
  const only2027 = document.getElementById('only2027').checked;
  const onlyIntern = document.getElementById('onlyIntern').checked;
  let visible = 0;
  document.querySelectorAll('.job-row').forEach(function (row) {
    let show = true;
    if (activeCategory !== 'all' && row.dataset.category !== activeCategory) show = false;
    if (only2027 && row.dataset['2027'] !== '1') show = false;
    if (onlyIntern && row.dataset.intern !== '1') show = false;
    if (search && row.dataset.search.indexOf(search) === -1) show = false;
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  document.getElementById('resultCount').textContent = visible + ' listing' + (visible === 1 ? '' : 's') + ' shown';
  const empty = document.getElementById('emptyState');
  if (empty) empty.style.display = visible === 0 ? 'block' : 'none';
}

document.addEventListener('DOMContentLoaded', function () {
  initTheme();
  document.querySelectorAll('.nav-item').forEach(function (item) {
    item.addEventListener('click', function () {
      document.querySelectorAll('.nav-item').forEach(function (p) { p.classList.remove('on'); });
      item.classList.add('on');
      activeCategory = item.dataset.category;
      applyFilters();
    });
  });
  document.getElementById('searchBox').addEventListener('input', applyFilters);
  document.getElementById('only2027').addEventListener('change', applyFilters);
  document.getElementById('onlyIntern').addEventListener('change', applyFilters);
  applyFilters();
});
</script>
"""


def render():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM listings WHERE active = 1 ORDER BY (posted_date IS NULL), posted_date DESC, first_seen DESC"
    ).fetchall()
    conn.close()

    counts = {"conservation_biology": 0, "environmental_justice": 0, "climate_policy": 0, "other": 0}
    sources = set()
    summer_2027_count = 0
    internship_count = 0
    for r in rows:
        counts[r["category"]] = counts.get(r["category"], 0) + 1
        sources.add(r["source"])
        if r["summer_2027"]:
            summer_2027_count += 1
        if r["internship_tag"]:
            internship_count += 1

    nav_items = [
        f'<li><button type="button" class="nav-item on" data-category="all" style="--nav-color:var(--cat-all)">'
        f'{CATEGORY_ICONS["all"]}All<span class="count">{len(rows)}</span></button></li>'
    ]
    for cat, label in CATEGORY_LABELS.items():
        nav_items.append(
            f'<li><button type="button" class="nav-item" data-category="{cat}" style="--nav-color:var(--cat-{cat})">'
            f'{CATEGORY_ICONS.get(cat, "")}{html.escape(label)}<span class="count">{counts.get(cat, 0)}</span></button></li>'
        )
    nav_html = "".join(nav_items)

    rows_html = "".join(_row_html(r) for r in rows)
    empty_state = (
        '<div class="empty-state" id="emptyState" style="display:none">'
        "No listings match these filters right now &mdash; try clearing the search or picking a different category."
        "</div>"
    )
    if not rows:
        empty_state = (
            '<div class="empty-state" id="emptyState">'
            "No listings found yet. This usually means the scraper hasn't had a source configured "
            "(see the README) or hasn't run yet &mdash; check back after the next scheduled refresh."
            "</div>"
        )

    generated_at = datetime.now(timezone.utc).strftime("%B %-d, %Y at %-I:%M %p UTC")
    source_list = ", ".join(sorted(SOURCE_LABELS.get(s, s) for s in sources)) or "no sources configured yet"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>Conservation & Climate Jobs Tracker</title>
{STYLE}
</head>
<body>
  <header class="site">
    <div>
      <h1 class="brand">Conservation &amp; Climate Jobs</h1>
      <p class="tagline">Internships, fellowships, and entry-level roles in conservation biology, environmental
         justice, and climate policy, pulled automatically from multiple job sites and refreshed on a schedule.</p>
      <div class="header-meta">Sources checked: {html.escape(source_list)} &middot; Last updated {generated_at}</div>
    </div>
    <button type="button" class="theme-toggle" id="themeToggle">Switch to dark</button>
  </header>
  <div class="layout">
    <aside class="sidebar">
      <h2>Category</h2>
      <ul class="nav-list">{nav_html}</ul>
      <input type="text" id="searchBox" class="side-search" placeholder="Search title, org, location...">
      <label class="side-toggle"><input type="checkbox" id="only2027"> Summer 2027 mentioned</label>
      <label class="side-toggle"><input type="checkbox" id="onlyIntern"> Internship / entry-level tagged</label>
      <div class="sidebar-footer">
        Every row links straight to the original posting &mdash; nothing is hosted here beyond a short summary.
        Categorization is automatic and can occasionally miscategorize or miss a listing; check the source
        site directly when in doubt.
      </div>
    </aside>
    <main class="main">
      <div id="resultCount"></div>
      <div class="job-list">{rows_html}</div>
      {empty_state}
    </main>
  </div>
  <footer class="site-footer">
    Refreshes automatically on a schedule &mdash; see the
    <a href="https://github.com/joshuam0y/conservation-climate-jobs" target="_blank" rel="noopener">README</a>
    for how this works and how to add more sources.
  </footer>
{SCRIPT}
</body></html>
"""


def write():
    """render() only builds the HTML string (easy to unit-test/import) --
    this does the actual file write, shared by this module's own __main__
    (for standalone runs) and build.py (which imports and calls this, not
    render() directly)."""
    import os

    out_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    os.makedirs(out_dir, exist_ok=True)
    html_out = render()
    with open(os.path.join(out_dir, "index.html"), "w") as f:
        f.write(html_out)
    open(os.path.join(out_dir, ".nojekyll"), "w").close()
    print(f"Wrote {os.path.join(out_dir, 'index.html')} ({len(html_out)} chars)")


if __name__ == "__main__":
    write()
