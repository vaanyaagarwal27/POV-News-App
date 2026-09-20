import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_FILE = os.path.join(DATA_DIR, "people_cache.json")

USER_AGENT = "POV-News-App/1.0"
TIMEOUT = 10


def _load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def _save_cache(cache):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def _first_sentences(text, n):
    """Return first n sentences of text, truncated to fit their natural end."""
    # Split on sentence-ending punctuation followed by whitespace or end
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n])


def _cap(text, limit):
    if len(text) <= limit:
        return text
    return text[:limit - 1].rstrip() + "…"


def lookup_person(name):
    cache = _load_cache()
    if name in cache:
        return cache[name]

    result = _lookup_uncached(name)
    cache[name] = result
    _save_cache(cache)
    return result


def _lookup_uncached(name):
    if " " not in name.strip():
        return None
    try:
        # 1. Search
        params = urllib.parse.urlencode({"q": name, "limit": 3})
        search_url = f"https://en.wikipedia.org/w/rest.php/v1/search/page?{params}"
        search_data = _get(search_url)

        # 2. First result whose title contains all words of the name
        name_words = [w.lower() for w in name.split()]
        matched_title = None
        for page in search_data.get("pages", []):
            title_lower = page.get("title", "").lower()
            if all(w in title_lower for w in name_words):
                matched_title = page["title"]
                break

        if matched_title is None:
            return None

        # 3. Fetch summary
        encoded_title = urllib.parse.quote(matched_title.replace(" ", "_"))
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        summary = _get(summary_url)

        # 4. Skip disambiguation pages
        if summary.get("type") == "disambiguation":
            return None

        # 5. Build result
        description = summary.get("description", "")
        extract = summary.get("extract", "")

        if description:
            who = _cap(description, 100)
        else:
            who = _cap(_first_sentences(extract, 1), 100)

        detail = _cap(_first_sentences(extract, 2), 220)

        thumbnail = summary.get("thumbnail")
        image = thumbnail["source"] if thumbnail else None

        wiki_url = (
            summary.get("content_urls", {})
            .get("desktop", {})
            .get("page")
        )

        return {
            "name": summary.get("title", matched_title),
            "who": who,
            "detail": detail,
            "image": image,
            "wiki_url": wiki_url,
        }

    except Exception:
        return None


if __name__ == "__main__":
    test_names = [
        "Narendra Modi",
        "Donald Trump",
        "Siddaramaiah",
        "Rahul Gandhi",
        "Jorbin Faxley",
    ]
    for name in test_names:
        print(f"--- {name} ---")
        result = lookup_person(name)
        if result is None:
            print("  Not found")
        else:
            for k, v in result.items():
                print(f"  {k}: {v}")
        print()
