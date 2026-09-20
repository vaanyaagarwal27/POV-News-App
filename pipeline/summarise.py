import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

from google import genai

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")

TOPICS = {
    "Politics", "Economy", "Jobs", "Tech", "Climate",
    "Courts", "Health", "Campus & exams", "Sport", "Culture",
}

VALID_REGIONS = {
    "national", "international",
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal", "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
}


def pick_articles(group):
    """Return at most 8 articles, prioritising widest spread of papers."""
    by_paper = {}
    for a in group["articles"]:
        by_paper.setdefault(a["paper"], []).append(a)

    selected = []
    # Round-robin one article per paper until 8 or exhausted
    rounds = max(len(v) for v in by_paper.values()) if by_paper else 0
    for _ in range(rounds):
        for paper_articles in by_paper.values():
            if paper_articles:
                selected.append(paper_articles.pop(0))
            if len(selected) == 8:
                return selected
    return selected


def build_prompt(articles):
    articles_block = "\n\n".join(
        f"SOURCE {i+1}\nPaper: {a['paper']}\nHeadline: {a['headline']}\n"
        f"URL: {a['url']}\nSummary: {a.get('summary', '')}"
        for i, a in enumerate(articles)
    )

    return f"""You are a neutral news summariser. Given the articles below, produce a single JSON story object.

ARTICLES:
{articles_block}

RULES:
- headline: neutral, max 110 characters
- agreed_facts: specific — include real names, numbers, places, dates. Drop anything you cannot state specifically. Never write vague filler like "teams are competing in various tournaments".
- Ignore any opinion columns or editorials in the articles above.
- topic: exactly one of: Politics, Economy, Jobs, Tech, Climate, Courts, Health, Campus & exams, Sport, Culture
- regions: list using only official Indian state/UT names, "national", or "international". Never use city names or country names.
- disagreement: integer 0–3. 0 only when every paper framed the story identically; then teaser must be "" and there must be exactly 1 cluster. 1 or higher means 2 or more clusters with genuinely distinct editorial choices.
- teaser: ONE line, max 120 characters, naming at least two papers by name and what each leads with, e.g. "Hindustan Times leads with the tariff threat to India; Times of India leads with China's rejection". No hedging words like "while" or "sources confirm". Empty string only when disagreement is 0.
- clusters: a cluster is a FRAMING CHOICE, not a sub-topic. Papers belong in the same cluster only when they made the same editorial decision: what they lead with, whose voice they centre, what they emphasise, what they leave out, or what they imply about who wins or loses. The "angle" must name that editorial choice and must be a sentence a reader could disagree with — good: "Frames the deal as a climbdown from Trump's original ambition"; bad: "Coverage of the US-Denmark deal." Never create a cluster whose papers have substantively the same headline — if several papers just report the same fact in the same way, that is not a framing difference; put them in one cluster and name it as the neutral wire-style framing. Prefer 2–3 sharp clusters over 4 or more weak ones; a single-paper cluster is fine when that paper framed it differently from everyone else. Each cluster has an "angle" string and a "papers" list. Each paper entry has "name", "headline", and "url". The "headline" field must be copied EXACTLY from the articles given above — never rewrite or paraphrase it.
- agreed_facts: every fact must be stated in at least 2 of the articles given. Never add background knowledge of your own. If you are not sure the articles say it, leave it out.
- jargon: each term must appear word-for-word in agreed_facts. If it doesn't, omit it. "plain": one simple sentence under 15 words, using no other difficult words. Write it for a 16-year-old.
- people: each name must appear word-for-word in agreed_facts. If it doesn't, omit it. Use the person's full name exactly as given in the articles. "who" can be left as an empty string — it will be filled in automatically.
- affects: 1–3 lowercase plain noun phrases naming GROUPS OF PEOPLE, e.g. "petrol buyers", "exporters", "students". Never a country, company, organisation or person's name.
- why_it_matters: one sentence
- Return JSON only, no commentary, no markdown fences.

OUTPUT SCHEMA:
{{
  "headline": "string, max 110 chars",
  "topic": "one of the listed topics",
  "regions": ["national" | "international" | official Indian state/UT],
  "disagreement": 0-3,
  "teaser": "e.g. 'Reuters leads with X; BBC leads with Y', or empty string if disagreement is 0",
  "why_it_matters": "one sentence",
  "affects": ["petrol buyers", "exporters"],
  "agreed_facts": ["sentence1", "sentence2"],
  "clusters": [
    {{
      "angle": "sentence naming the editorial choice; must be one a reader could disagree with",
      "papers": [
        {{"name": "Paper Name", "headline": "EXACT headline from above", "url": "url"}}
      ]
    }}
  ],
  "jargon": [{{"term": "term", "plain": "one simple sentence under 15 words for a 16-year-old"}}],
  "people": [{{"name": "Full Name", "who": "max 8 words from the articles"}}]
}}"""


def strip_fences(text):
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()


def validate(story, articles):
    fixes = []

    # topic
    if story.get("topic") not in TOPICS:
        return None, [f"rejected: invalid topic '{story.get('topic')}'"]

    # regions
    raw_regions = story.get("regions", [])
    clean_regions = [r for r in raw_regions if r in VALID_REGIONS]
    if len(clean_regions) < len(raw_regions):
        dropped = set(raw_regions) - set(clean_regions)
        fixes.append(f"dropped invalid regions: {dropped}")
    if not clean_regions:
        clean_regions = ["national"]
        fixes.append("regions was empty after filtering, defaulted to ['national']")
    story["regions"] = clean_regions

    # clusters: drop papers whose headline isn't exactly in the input set;
    # replace url with the input article's url (never trust the model's url)
    headline_to_url = {a["headline"]: a["url"] for a in articles}
    clean_clusters = []
    for cluster in story.get("clusters", []):
        clean_papers = []
        for p in cluster.get("papers", []):
            if p.get("headline") in headline_to_url:
                p["url"] = headline_to_url[p["headline"]]
                clean_papers.append(p)
        dropped = len(cluster.get("papers", [])) - len(clean_papers)
        if dropped:
            fixes.append(f"dropped {dropped} paper(s) with rewritten headlines from cluster '{cluster.get('angle','')[:40]}'")
        if clean_papers:
            cluster["papers"] = clean_papers
            clean_clusters.append(cluster)
        else:
            fixes.append(f"dropped cluster with no valid papers: '{cluster.get('angle','')[:40]}'")
    story["clusters"] = clean_clusters

    # source_count
    paper_names = {p["name"] for c in story["clusters"] for p in c["papers"]}
    source_count = len(paper_names)
    if source_count < 2:
        return None, fixes + [f"rejected: only {source_count} paper(s) left in clusters"]
    story["source_count"] = source_count

    # disagreement / teaser / cluster count consistency
    num_clusters = len(story["clusters"])
    disagreement = int(story.get("disagreement", 0))

    if disagreement == 0:
        if story.get("teaser", "") != "":
            fixes.append("forced teaser to '' because disagreement is 0")
        story["teaser"] = ""
        if num_clusters >= 2:
            disagreement = 1
            story["disagreement"] = disagreement
            fixes.append(f"set disagreement to 1 because there are {num_clusters} clusters")
    else:
        if num_clusters < 2:
            # Can't have disagreement with 1 cluster — downgrade
            disagreement = 0
            story["disagreement"] = 0
            story["teaser"] = ""
            fixes.append("set disagreement to 0 and cleared teaser: only 1 cluster")

    # jargon: keep only terms that appear verbatim in agreed_facts
    agreed_text = " ".join(story.get("agreed_facts", []))
    clean_jargon = [j for j in story.get("jargon", []) if j.get("term", "") in agreed_text]
    if len(clean_jargon) < len(story.get("jargon", [])):
        fixes.append(f"dropped {len(story.get('jargon',[])) - len(clean_jargon)} jargon term(s) not in agreed_facts")
    story["jargon"] = clean_jargon

    # people: keep only names that appear verbatim in agreed_facts, then enrich via Wikipedia
    from people_lookup import lookup_person
    clean_people = []
    for p in story.get("people", []):
        name = p.get("name", "")
        if name not in agreed_text:
            fixes.append(f"dropped person not in agreed_facts: '{name}'")
            continue
        wiki = lookup_person(name)
        if wiki is None:
            fixes.append(f"dropped person not found on Wikipedia: '{name}'")
            continue
        clean_people.append({
            "name": name,
            "who": wiki["who"],
            "detail": wiki["detail"],
            "image": wiki["image"],
            "wiki_url": wiki["wiki_url"],
        })
    story["people"] = clean_people

    # affects: lowercase, drop entries longer than 4 words
    raw_affects = story.get("affects", [])
    clean_affects = [e.lower() for e in raw_affects if len(e.split()) <= 4]
    if len(clean_affects) < len(raw_affects):
        dropped_affects = [e for e in raw_affects if len(e.split()) > 4]
        fixes.append(f"dropped affects entries over 4 words: {dropped_affects}")
    story["affects"] = clean_affects

    # headline length
    if len(story.get("headline", "")) > 110:
        story["headline"] = story["headline"][:110]
        fixes.append("truncated headline to 110 characters")

    # read_seconds
    word_sources = list(story.get("agreed_facts", [])) + [story.get("why_it_matters", "")]
    word_sources += [c.get("angle", "") for c in story["clusters"]]
    total_words = sum(len(s.split()) for s in word_sources)
    read_seconds = round((total_words / 200) * 60 + 10 * len(story["clusters"]))
    read_seconds = max(45, read_seconds)
    story["read_seconds"] = read_seconds

    return story, fixes


def summarise_group(group):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable not set")

    articles = pick_articles(group)
    prompt = build_prompt(articles)

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt,
    )
    raw = response.text

    cleaned = strip_fences(raw)
    try:
        story = json.loads(cleaned)
    except json.JSONDecodeError:
        print("RAW RESPONSE:\n", raw)
        return None

    # Attach stable id and published date
    most_recent = max(group["articles"], key=lambda a: a["published"])
    pub_date = most_recent["published"][:10]
    story["published"] = pub_date
    story["id"] = hashlib.md5(
        (story.get("headline", "") + pub_date).encode()
    ).hexdigest()[:8]

    story, fixes = validate(story, articles)
    return story, fixes


if __name__ == "__main__":
    with open(GROUPS_FILE) as f:
        groups = json.load(f)

    best = max(groups, key=lambda g: g["paper_count"])
    print(f"Summarising group {best['group_id']} ({best['paper_count']} papers: {', '.join(best['papers'])})\n")

    result = summarise_group(best)
    if result is None:
        print("summarise_group returned None (fatal error before validate)")
        sys.exit(1)

    story, fixes = result
    if story is None:
        print("Story rejected by validate.")
        print("Fixes/reasons:", fixes)
        sys.exit(1)

    print(json.dumps(story, indent=2, ensure_ascii=False))
    print()
    if fixes:
        print("Validation fixes applied:")
        for f in fixes:
            print(f"  - {f}")
    else:
        print("No validation fixes needed.")
