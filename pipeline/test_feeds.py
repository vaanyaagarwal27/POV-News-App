import feedparser
from feeds import FEEDS

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

for feed in FEEDS:
    try:
        d = feedparser.parse(feed["url"], request_headers={"User-Agent": USER_AGENT})
        count = len(d.entries)
        if d.bozo and count == 0:
            raise ValueError(d.bozo_exception)
        status = count if count > 0 else "FAILED (0 articles)"
        print(f"{feed['name']:<20} {count:>3} articles   {feed['url']}")
    except Exception as e:
        print(f"{feed['name']:<20} FAILED        {feed['url']}")
