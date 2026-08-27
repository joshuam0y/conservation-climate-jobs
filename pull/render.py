"""
render.py

Renders listings.db into a single static docs/index.html -- plain f-string
templating (no Jinja/build step), inline CSS/JS, client-side filtering
only (no server calls), same overall approach as render_dashboard.py in a
sibling project. Deployed via GitHub Pages straight from docs/.

Category palette is the dataviz skill's own validated categorical theme
(references/palette.md), narrowed to 4 slots and re-validated for this
exact set: blue/orange/aqua/violet passes CVD separation under the
strictest all-pairs check in both light and dark mode. The one WARN
(aqua's contrast against a light surface) is mitigated the way the skill
requires -- every badge always carries its own text label, never a bare
color swatch.
"""

import html
import json
from datetime import datetime, timezone

from categorize import CATEGORY_LABELS
from db import get_conn

CATEGORY_COLORS = {
    "conservation_biology": {"light": "#1baf7a", "dark": "#199e70"},
    "environmental_justice": {"light": "#eb6834", "dark": "#d95926"},
    "climate_policy": {"light": "#2a78d6", "dark": "#3987e5"},
    "other": {"light": "#4a3aa7", "dark": "#9085e9"},
}

SOURCE_LABELS = {"USAJOBS": "USAJOBS.gov", "Idealist": "Idealist.org"}


def _fmt_date(iso_str):
    if not iso_str:
        return None
    try:
        d = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return d.strftime("%b %-d, %Y")
    except Exception:
        return iso_str[:10]


def _card_html(row):
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
    meta_line = " &middot; ".join(meta_bits)

    footer_bits = [f'<span class="src-badge">{html.escape(source_label)}</span>']
    if posted:
        footer_bits.append(f"Posted {posted}")
    if close:
        footer_bits.append(f"Closes {close}")
    footer_line = " &middot; ".join(footer_bits)

    summer_badge = '<span class="badge badge-2027">SUMMER 2027 MENTIONED</span>' if row["summer_2027"] else ""
    intern_badge = '<span class="badge badge-intern">INTERNSHIP / ENTRY-LEVEL</span>' if row["internship_tag"] else ""
    summary_html = f'<p class="card-summary">{html.escape(row["summary"])}</p>' if row["summary"] else ""

    return f"""
    <a class="card" href="{html.escape(row['url'])}" target="_blank" rel="noopener"
       data-category="{cat}" data-search="{html.escape((row['title'] + ' ' + (row['organization'] or '') + ' ' + (row['location'] or '')).lower())}"
       data-2027="{'1' if row['summer_2027'] else '0'}" data-intern="{'1' if row['internship_tag'] else '0'}">
      <div class="card-top">
        <span class="badge badge-cat" style="background:var(--cat-{cat})">{html.escape(cat_label)}</span>
        {intern_badge}
        {summer_badge}
      </div>
      <h3 class="card-title">{html.escape(row['title'])}</h3>
      <div class="card-meta">{meta_line}</div>
      {summary_html}
      <div class="card-footer">{footer_line}</div>
    </a>
    """


STYLE = """
<style>
  :root {
    color-scheme: light;
    --bg: #FAF9F5; --surface: #ffffff; --surface-2: #F2F1EA;
    --ink: #1C231F; --ink-dim: #55605A; --ink-muted: #8A9289;
    --border: rgba(28,35,31,0.10); --shadow: 0 1px 2px rgba(28,35,31,.06), 0 8px 20px rgba(28,35,31,.06);
    --accent: #1F6F4A; --accent-bg: rgba(31,111,74,0.10);
    --cat-conservation_biology: #1baf7a; --cat-environmental_justice: #eb6834;
    --cat-climate_policy: #2a78d6; --cat-other: #4a3aa7;
    --header-grad: linear-gradient(135deg, #123B2A, #1F6F4A);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --bg: #101511; --surface: #171D18; --surface-2: #1E2620;
      --ink: #F2F4F1; --ink-dim: #B7C0BA; --ink-muted: #7C8880;
      --border: rgba(255,255,255,0.09); --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 20px rgba(0,0,0,.35);
      --accent: #3FAE7C; --accent-bg: rgba(63,174,124,0.16);
      --cat-conservation_biology: #199e70; --cat-environmental_justice: #d95926;
      --cat-climate_policy: #3987e5; --cat-other: #9085e9;
      --header-grad: linear-gradient(135deg, #08150F, #113322);
    }
  }
  :root[data-theme="dark"] {
    color-scheme: dark;
    --bg: #101511; --surface: #171D18; --surface-2: #1E2620;
    --ink: #F2F4F1; --ink-dim: #B7C0BA; --ink-muted: #7C8880;
    --border: rgba(255,255,255,0.09); --shadow: 0 1px 2px rgba(0,0,0,.3), 0 8px 20px rgba(0,0,0,.35);
    --accent: #3FAE7C; --accent-bg: rgba(63,174,124,0.16);
    --cat-conservation_biology: #199e70; --cat-environmental_justice: #d95926;
    --cat-climate_policy: #3987e5; --cat-other: #9085e9;
    --header-grad: linear-gradient(135deg, #08150F, #113322);
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--ink); font-family: -apple-system, "Segoe UI", system-ui, sans-serif; }
  .page { max-width: 1080px; margin: 0 auto; padding: 0 20px 60px; }

  .header-band { background: var(--header-grad); color: #fff; padding: 28px 24px; border-radius: 0 0 20px 20px; margin-bottom: 20px; }
  .header-inner { max-width: 1080px; margin: 0 auto; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; }
  .header-band h1 { margin: 0 0 6px; font-size: 24px; letter-spacing: -0.01em; }
  .header-band p { margin: 0; color: rgba(255,255,255,0.82); font-size: 14px; max-width: 60ch; line-height: 1.5; }
  .meta-line { margin-top: 8px; font-size: 12.5px; color: rgba(255,255,255,0.7); }
  .theme-toggle {
    background: rgba(255,255,255,0.15); color: #fff; border: 1px solid rgba(255,255,255,0.3);
    border-radius: 999px; padding: 7px 14px; font-size: 12.5px; font-weight: 600; cursor: pointer; font-family: inherit;
  }
  .theme-toggle:hover { background: rgba(255,255,255,0.25); }

  .stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 18px; }
  .stat-tile { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px; box-shadow: var(--shadow); border-top: 3px solid var(--accent); }
  .stat-value { font-size: 21px; font-weight: 700; }
  .stat-label { font-size: 11.5px; color: var(--ink-muted); margin-top: 2px; }

  .toolbar {
    position: sticky; top: 0; z-index: 5; background: var(--bg); padding: 10px 0 12px;
    display: flex; flex-wrap: wrap; gap: 8px; align-items: center; border-bottom: 1px solid var(--border); margin-bottom: 16px;
  }
  .filter-pill {
    background: var(--surface); border: 1px solid var(--border); color: var(--ink-dim);
    border-radius: 999px; padding: 7px 14px; font-size: 13px; font-weight: 600; cursor: pointer; font-family: inherit;
  }
  .filter-pill.on { background: var(--accent); border-color: var(--accent); color: #fff; }
  .search-box {
    flex: 1; min-width: 160px; padding: 8px 12px; border-radius: 999px; border: 1px solid var(--border);
    background: var(--surface); color: var(--ink); font-size: 13px; font-family: inherit;
  }
  .toggle-2027, .toggle-intern { display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--ink-dim); }
  #resultCount { font-size: 12.5px; color: var(--ink-muted); width: 100%; margin-top: 2px; }

  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
  .card {
    display: block; background: var(--surface); border: 1px solid var(--border); border-radius: 14px;
    padding: 14px 16px; box-shadow: var(--shadow); text-decoration: none; color: inherit;
    transition: transform .08s, box-shadow .08s;
  }
  .card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,.08), 0 14px 26px rgba(0,0,0,.10); }
  .card-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 6px; margin-bottom: 8px; flex-wrap: wrap; }
  .badge { font-size: 10.5px; font-weight: 700; letter-spacing: .02em; border-radius: 999px; padding: 3px 9px; color: #fff; white-space: nowrap; }
  .badge-2027 { background: var(--accent-bg); color: var(--accent); }
  .badge-intern { background: var(--surface-2); color: var(--ink-dim); border: 1px solid var(--border); }
  .card-title { font-size: 15.5px; font-weight: 700; margin: 0 0 4px; line-height: 1.3; color: var(--ink); }
  .card-meta { font-size: 12.5px; color: var(--ink-dim); margin-bottom: 6px; }
  .card-summary { font-size: 12.5px; color: var(--ink-dim); line-height: 1.5; margin: 0 0 8px; }
  .card-footer { font-size: 11.5px; color: var(--ink-muted); border-top: 1px dashed var(--border); padding-top: 8px; }
  .src-badge { background: var(--surface-2); border-radius: 6px; padding: 1px 6px; font-weight: 600; }

  .empty-state { text-align: center; padding: 60px 20px; color: var(--ink-muted); }
  footer.site-footer { margin-top: 30px; padding-top: 16px; border-top: 1px solid var(--border); font-size: 12px; color: var(--ink-muted); line-height: 1.6; }
  footer.site-footer a { color: var(--accent); }

  @media (max-width: 560px) {
    .header-inner { flex-direction: column; }
    .grid { grid-template-columns: 1fr; }
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
  document.querySelectorAll('.card').forEach(function (card) {
    let show = true;
    if (activeCategory !== 'all' && card.dataset.category !== activeCategory) show = false;
    if (only2027 && card.dataset['2027'] !== '1') show = false;
    if (onlyIntern && card.dataset.intern !== '1') show = false;
    if (search && card.dataset.search.indexOf(search) === -1) show = false;
    card.style.display = show ? '' : 'none';
    if (show) visible++;
  });
  document.getElementById('resultCount').textContent = visible + ' listing' + (visible === 1 ? '' : 's') + ' shown';
  const empty = document.getElementById('emptyState');
  if (empty) empty.style.display = visible === 0 ? 'block' : 'none';
}

document.addEventListener('DOMContentLoaded', function () {
  initTheme();
  document.querySelectorAll('.filter-pill').forEach(function (pill) {
    pill.addEventListener('click', function () {
      document.querySelectorAll('.filter-pill').forEach(function (p) { p.classList.remove('on'); });
      pill.classList.add('on');
      activeCategory = pill.dataset.category;
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

    stat_tiles = "".join(
        f'<div class="stat-tile"><div class="stat-value">{v}</div><div class="stat-label">{html.escape(l)}</div></div>'
        for v, l in [
            (len(rows), "Total listings"),
            (counts["conservation_biology"], "Conservation Biology"),
            (counts["environmental_justice"], "Environmental Justice"),
            (counts["climate_policy"], "Climate Policy"),
            (internship_count, "Internship / entry-level tagged"),
            (summer_2027_count, "Mention Summer 2027"),
        ]
    )

    filter_pills = '<button type="button" class="filter-pill on" data-category="all">All</button>'
    for cat, label in CATEGORY_LABELS.items():
        filter_pills += f'<button type="button" class="filter-pill" data-category="{cat}">{html.escape(label)}</button>'

    cards_html = "".join(_card_html(r) for r in rows)
    if not rows:
        cards_html = ""
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
  <div class="header-band">
    <div class="header-inner">
      <div>
        <h1>Conservation &amp; Climate Jobs Tracker</h1>
        <p>Internships, fellowships, and entry-level roles in conservation biology, environmental justice,
           and climate policy &mdash; pulled automatically from multiple job sites and refreshed on a schedule,
           with a highlight for anything that mentions Summer 2027.</p>
        <div class="meta-line">Sources checked: {html.escape(source_list)} &middot; Last updated {generated_at}</div>
      </div>
      <button type="button" class="theme-toggle" id="themeToggle">Switch to dark</button>
    </div>
  </div>
  <div class="page">
    <div class="stats-row">{stat_tiles}</div>
    <div class="toolbar">
      {filter_pills}
      <input type="text" id="searchBox" class="search-box" placeholder="Search title, organization, location...">
      <label class="toggle-2027"><input type="checkbox" id="only2027"> Only show Summer 2027 mentions</label>
      <label class="toggle-intern"><input type="checkbox" id="onlyIntern"> Only show internship/entry-level tagged</label>
      <div id="resultCount"></div>
    </div>
    <div class="grid">{cards_html}</div>
    {empty_state}
    <footer class="site-footer">
      Built as a personal aggregator &mdash; every card links straight to the original posting on its source
      site, nothing is hosted here beyond a short summary. Categorization is automatic (keyword-based) and
      can occasionally miscategorize or miss a listing; when in doubt, check the source site directly.
      Refreshes automatically on a schedule &mdash; see the
      <a href="https://github.com/joshuam0y/conservation-climate-jobs" target="_blank" rel="noopener">README</a>
      for how this works and how to add more sources.
    </footer>
  </div>
{SCRIPT}
</body></html>
"""


def write():
    """render() only builds the HTML string (easy to unit-test/import) --
    this does the actual file write, shared by this module's own __main__
    (for standalone runs) and build.py (which imports and calls this, not
    render() directly -- calling render() alone silently computes the page
    and throws it away, which is exactly the bug that shipped here once:
    build.py called render() for its side effects that didn't exist,
    so docs/index.html just never updated across several real runs)."""
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
