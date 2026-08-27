"""
categorize.py

Keyword-based classification shared by every source scraper, so a listing
from USAJOBS and a listing from Idealist are judged by the exact same
rules. Modeled on the is_relevant()/keyword-regex pattern from a sibling
project's news scraper -- proven there to need real-world tuning, so
expect to widen/narrow these patterns as false positives/negatives show
up in practice.

Four buckets, checked in order (first match wins) -- Conservation Biology,
Environmental Justice, and Climate Policy are the three named categories;
"other" is a deliberate catch-all for anything environmental/sustainability
-adjacent that doesn't fit those three, rather than silently dropping it.
Returns None (not "other") only when a listing isn't environmental at all,
which is the caller's signal to drop it as irrelevant noise.
"""

import re

CONSERVATION_BIOLOGY = re.compile(
    r"\b("
    r"conservation biolog\w*|wildlife biolog\w*|wildlife (management|technician|refuge|ecolog\w*)|"
    r"fisheries|ecolog(y|ist|ical)|endangered species|habitat restoration|field biolog\w*|"
    r"natural resource\w*|forestry|forester|botan(y|ist)|zoolog\w*|marine biolog\w*|"
    r"avian|herpetolog\w*|ornitholog\w*|entomolog\w*|national wildlife refuge|"
    r"national park service|fish and wildlife|biodiversity|game warden|park ranger\w*|"
    r"restoration ecolog\w*|species recovery|wetland\w* (restoration|monitoring)|"
    # Broader, org-organizing-style phrasing for the same subject matter --
    # a real, common gap: general nonprofit job boards (Idealist) mostly
    # post advocacy/organizing roles, not literal "wildlife biologist"
    # titles, even at conservation-focused orgs. "Conservation" alone is
    # too broad (would swallow finance/HR roles at any org with
    # "Conservation" in its name), so this requires it alongside a
    # conservation-specific object.
    r"(ocean|land|marine|wildlife|habitat|watershed|coastal) conservation|"
    r"conservation (organizer|associate|coordinator|corps)|land steward\w*|"
    r"land trust|conservation district"
    r")\b",
    re.IGNORECASE,
)

ENVIRONMENTAL_JUSTICE = re.compile(
    r"\b("
    r"environmental justice|ejscreen|frontline communit\w*|environmental equity|"
    r"disadvantaged communit\w*|environmental racism|just transition|climate justice|"
    r"environmental health dispar\w*|community engagement.{0,20}environment\w*|"
    r"equity.{0,20}(environment|climate)|environmental injustice"
    r")\b",
    re.IGNORECASE,
)

CLIMATE_POLICY = re.compile(
    r"\b("
    r"climate polic\w*|climate change polic\w*|climate legislat\w*|climate adaptation|"
    r"climate mitigation|carbon polic\w*|emissions polic\w*|clean energy polic\w*|"
    r"climate resilien\w*|greenhouse gas polic\w*|climate action plan|energy polic\w*|"
    r"climate advocacy|climate governance|carbon market\w*|climate finance|"
    r"climate risk (assessment|management)|"
    # Same broadening as CONSERVATION_BIOLOGY above -- these are how
    # climate-policy-adjacent advocacy roles are actually titled on
    # nonprofit job boards, not "policy analyst."
    r"(global warming|climate) campaign\w*|clean energy campaign\w*|"
    r"climate (organizer|advocate)"
    r")\b",
    re.IGNORECASE,
)

# Broad "is this environmental/sustainability-adjacent at all" gate -- a
# listing matching only this (not one of the three specific buckets above)
# lands in "Other" instead of being dropped as irrelevant.
ENVIRONMENTAL_GENERAL = re.compile(
    r"\b("
    r"environment\w*|sustainab\w*|conservation|climate|wildlife|ecolog\w*|"
    r"natural resource\w*|renewable energy|clean energy|green (job|career)\w*|"
    r"land management|watershed|coastal|ocean|marine|forest\w*|"
    r"pollution|recycl\w*|solar|epa\b|noaa\b|environmental science"
    r")\b",
    re.IGNORECASE,
)

# Loose on purpose: a fellowship, seasonal field position, or "student
# trainee" (the federal Pathways title for an intern) is exactly as
# relevant to a student as something literally titled "intern".
INTERNSHIP_LIKE = re.compile(
    r"\b(intern(ship)?s?|pathways|student trainee|seasonal|summer (position|job|program|associate)|"
    r"fellow(ship)?s?|entry.level|early career|recent graduate\w*)\b",
    re.IGNORECASE,
)

# Deliberately narrow, unlike INTERNSHIP_LIKE -- nonprofit/advocacy titles
# inflate ("Senior Campaign Director" at $42-60k is a real early-career
# salary, confirmed live) so title alone is an unreliable senior-level
# signal in this sector and isn't used for exclusion here. Only the small
# set of titles that are essentially NEVER entry-level regardless of
# organization (a literal VP, C-suite, or org president) are excluded
# outright -- everything else stays, tagged or not, per
# is_internship_like() above.
SENIOR_LEVEL = re.compile(
    r"\b(vice president|chief \w+ officer|ceo|cfo|coo|executive director)\b",
    re.IGNORECASE,
)


def is_senior_level(title):
    return bool(SENIOR_LEVEL.search(title or ""))


def categorize(title, summary=""):
    """Returns 'conservation_biology', 'environmental_justice',
    'climate_policy', 'other', or None (not environmental -- drop it)."""
    text = f"{title} {summary}"
    if CONSERVATION_BIOLOGY.search(text):
        return "conservation_biology"
    if ENVIRONMENTAL_JUSTICE.search(text):
        return "environmental_justice"
    if CLIMATE_POLICY.search(text):
        return "climate_policy"
    if ENVIRONMENTAL_GENERAL.search(text):
        return "other"
    return None


def is_internship_like(title, summary=""):
    return bool(INTERNSHIP_LIKE.search(f"{title} {summary}"))


def mentions_2027(title, summary=""):
    return "2027" in f"{title} {summary}"


CATEGORY_LABELS = {
    "conservation_biology": "Conservation Biology",
    "environmental_justice": "Environmental Justice",
    "climate_policy": "Climate Policy",
    "other": "Other Environmental",
}
