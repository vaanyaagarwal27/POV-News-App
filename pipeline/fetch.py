import feedparser
import hashlib
import html
import json
import os
import re
import urllib.request
from datetime import datetime, timezone, timedelta

from feeds import FEEDS

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ARTICLES_FILE = os.path.join(DATA_DIR, "articles.json")


OPINION_URL_SEGMENTS = {
    "/opinion/", "/opinions/", "/editorial/", "/editorials/",
    "/column/", "/columns/", "/blog/", "/blogs/", "/op-ed/",
}
OPINION_HEADLINE_PREFIXES = ("Opinion:", "Editorial:")

JUNK_URL_SEGMENTS = {
    "/showtimes/", "/movie-show-timings/", "/events/",
    "/horoscope/", "/astrology/", "/photostory/", "/web-stories/",
}
JUNK_HEADLINE_TOKENS = ("Showtimes", "Show Timings")


def is_opinion(url, headline):
    url_lower = url.lower()
    if any(seg in url_lower for seg in OPINION_URL_SEGMENTS):
        return True
    return headline.startswith(OPINION_HEADLINE_PREFIXES)


def is_junk(url, headline):
    url_lower = url.lower()
    if any(seg in url_lower for seg in JUNK_URL_SEGMENTS):
        return True
    return any(tok in headline for tok in JUNK_HEADLINE_TOKENS)


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def clean_headline(title, is_google_news):
    title = html.unescape(title or "").strip()
    if is_google_news:
        # Google News appends " - Source Name" to every title
        title = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
    return title


def fetch_feed(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content = resp.read()
    return feedparser.parse(content)


def parse_published(entry, fetch_time):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t:
        try:
            return datetime(*t[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return fetch_time.isoformat()


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(ARTICLES_FILE):
        with open(ARTICLES_FILE) as f:
            articles = json.load(f)
    else:
        articles = []

    existing_ids = {a["id"] for a in articles}
    existing_headlines: dict[str, set] = {}
    for a in articles:
        existing_headlines.setdefault(a["paper"], set()).add(a["headline"])

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=4)
    total_new = 0

    for feed in FEEDS:
        is_google_news = "news.google.com" in feed["url"]
        try:
            d = fetch_feed(feed["url"])
        except Exception as e:
            print(f"{feed['name']:<20} | ERROR: {e}")
            continue

        feed_count = len(d.entries)
        feed_new = 0
        feed_skipped = 0
        feed_opinion = 0
        feed_junk = 0
        paper_headlines = existing_headlines.setdefault(feed["name"], set())

        for entry in d.entries:
            link = entry.get("link", "")
            if not link:
                feed_skipped += 1
                continue

            art_id = hashlib.md5(link.encode()).hexdigest()
            headline = clean_headline(entry.get("title", ""), is_google_news)

            if is_opinion(link, headline):
                feed_opinion += 1
                continue

            if is_junk(link, headline):
                feed_junk += 1
                continue

            pub = parse_published(entry, now)
            try:
                pub_dt = datetime.fromisoformat(pub)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    feed_skipped += 1
                    continue
            except Exception:
                pass

            if art_id in existing_ids or headline in paper_headlines:
                feed_skipped += 1
                continue

            summary = strip_html(entry.get("summary", ""))[:500]

            articles.append({
                "id": art_id,
                "paper": feed["name"],
                "headline": headline,
                "summary": summary,
                "url": link,
                "published": pub,
            })
            existing_ids.add(art_id)
            paper_headlines.add(headline)
            feed_new += 1

        total_new += feed_new
        print(f"{feed['name']:<20} | {feed_count:>3} in feed | {feed_new:>3} new | {feed_skipped:>3} skipped | {feed_opinion:>3} opinion skipped | {feed_junk:>3} junk skipped")

    prune_cutoff = now - timedelta(days=2)
    before_prune = len(articles)
    kept = []
    for a in articles:
        try:
            pub_dt = datetime.fromisoformat(a.get("published", ""))
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            if pub_dt >= prune_cutoff:
                kept.append(a)
        except Exception:
            kept.append(a)
    dropped = before_prune - len(kept)
    articles = kept

    with open(ARTICLES_FILE, "w") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    print(f"\nDropped {dropped} articles older than 2 days   Total new: {total_new}   Total in file: {len(articles)}")


if __name__ == "__main__":
    main()
