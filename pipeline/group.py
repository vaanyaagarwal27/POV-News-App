import json
import os
import random
import re
import string
from datetime import datetime, timezone

MIN_SHARED_WORDS = 3
MAX_DAYS_APART = 3

STOPWORDS = {
    # common English
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "has", "her",
    "was", "one", "our", "out", "its", "had", "have", "with", "this", "that",
    "from", "they", "will", "been", "who", "would", "than", "she", "his", "him",
    "into", "your", "their", "there", "when", "more", "also", "which", "then",
    "were", "some", "time", "two", "may", "get", "now", "first", "did", "man",
    "men", "could", "other", "about", "him", "just", "people", "those", "even",
    "government", "between", "while", "against", "before",
    # news filler
    "india", "indian", "says", "said", "news", "live", "updates", "latest",
    "today", "new", "amid", "over", "after", "report", "check", "watch",
    "video", "know", "here", "why", "how", "what", "year", "day",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ARTICLES_FILE = os.path.join(DATA_DIR, "articles.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")


def sig_words(headline, summary):
    text = headline + " " + summary[:200]
    text = text.lower()
    text = re.sub(r"[" + re.escape(string.punctuation) + r"]", " ", text)
    return {w for w in text.split() if len(w) >= 3 and w not in STOPWORDS}


def parse_dt(iso):
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def main():
    with open(ARTICLES_FILE) as f:
        articles = json.load(f)

    # sort newest first
    articles.sort(key=lambda a: a["published"], reverse=True)

    # precompute significant words for each article
    words = [sig_words(a["headline"], a.get("summary", "")) for a in articles]

    # each group: {newest_dt, articles: [idx, ...], words_per_article: [set, ...]}
    groups = []

    for i, article in enumerate(articles):
        art_dt = parse_dt(article["published"])
        art_words = words[i]

        best_group = None
        best_overlap = 0

        for g in groups:
            age_days = (g["newest_dt"] - art_dt).total_seconds() / 86400
            if age_days > MAX_DAYS_APART:
                continue

            # must share MIN_SHARED_WORDS with at least half the group's articles
            group_arts = g["words_per_article"]
            qualify_count = 0
            total_overlap = 0
            for gw in group_arts:
                overlap = len(art_words & gw)
                if overlap >= MIN_SHARED_WORDS:
                    qualify_count += 1
                    total_overlap += overlap

            if qualify_count >= len(group_arts) / 2:
                if total_overlap > best_overlap:
                    best_overlap = total_overlap
                    best_group = g

        if best_group is not None:
            best_group["articles"].append(i)
            best_group["words_per_article"].append(art_words)
        else:
            groups.append({
                "newest_dt": art_dt,
                "articles": [i],
                "words_per_article": [art_words],
            })

    # filter: keep only groups with 2+ different papers
    kept = []
    for g in groups:
        arts = [articles[i] for i in g["articles"]]
        papers = list({a["paper"] for a in arts})
        if len(papers) >= 2:
            kept.append({
                "group_id": len(kept),
                "paper_count": len(papers),
                "papers": papers,
                "articles": arts,
            })

    with open(GROUPS_FILE, "w") as f:
        json.dump(kept, f, ensure_ascii=False, indent=2)

    print(f"Groups kept: {len(kept)}\n")

    # 5 biggest by article count
    biggest = sorted(kept, key=lambda g: len(g["articles"]), reverse=True)[:5]
    print("=== 5 biggest groups ===")
    for g in biggest:
        arts = g["articles"]
        print(f"\n  [{len(arts)} articles, {g['paper_count']} papers: {', '.join(g['papers'])}]")
        for a in arts[:5]:
            print(f"    - {a['headline']}")

    # 5 random groups with all headlines
    sample = random.sample(kept, min(5, len(kept)))
    print("\n=== 5 random groups ===")
    for g in sample:
        arts = g["articles"]
        print(f"\n  [{len(arts)} articles, {g['paper_count']} papers: {', '.join(g['papers'])}]")
        for a in arts:
            print(f"    - {a['headline']}")


if __name__ == "__main__":
    main()
