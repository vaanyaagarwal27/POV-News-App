import concurrent.futures
import hashlib
import json
import os
import queue as queue_module
import threading
import time
from collections import Counter
from datetime import datetime, timezone, timedelta

from summarise import summarise_group

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
STORIES_FILE = os.path.join(DATA_DIR, "stories.json")

MAX_GROUPS = 40
MAX_WORKERS = 2
SUBMIT_DELAY = 20            # seconds between starting each group
RETRY_WAITS = [30, 60, 90]  # seconds before retry 1, 2, 3 on quota error
CIRCUIT_BREAKER_THRESHOLD = 2

IST = timezone(timedelta(hours=5, minutes=30))
QUOTA_KEYWORDS = {"quota", "rate limit", "429", "resource_exhausted", "resourceexhausted", "too many"}

print_lock = threading.Lock()


def is_quota_error(text):
    t = text.lower()
    return any(kw in t for kw in QUOTA_KEYWORDS)


def story_id_for_group(group_id):
    """Stable story ID derived from group_id so reruns can skip already-done groups."""
    return hashlib.md5(str(group_id).encode()).hexdigest()[:8]


def run_group(group, stop_event):
    gid = group["group_id"]
    last_err = None

    for attempt in range(len(RETRY_WAITS) + 1):  # initial + up to 3 retries
        if stop_event.is_set():
            return gid, "cancelled", None, []

        if attempt > 0:
            wait = RETRY_WAITS[attempt - 1]
            with print_lock:
                print(f"  group {gid:>3} | quota retry {attempt}/{len(RETRY_WAITS)}, "
                      f"waiting {wait}s...")
            for _ in range(wait):
                if stop_event.is_set():
                    return gid, "cancelled", None, []
                time.sleep(1)

        try:
            result = summarise_group(group)
        except Exception as e:
            err = str(e)
            if is_quota_error(err):
                last_err = err
                continue  # try again (or fall through if last attempt)
            return gid, "error", None, [err]

        if result is None:
            return gid, "none", None, []
        story, fixes = result
        if story is None:
            return gid, "rejected", None, fixes
        return gid, "ok", story, fixes

    # all retries exhausted on quota error
    return gid, "quota", None, [last_err or "all retries exhausted"]


def main():
    with open(GROUPS_FILE) as f:
        groups = json.load(f)

    # load existing stories; skip groups already summarised
    existing_stories = []
    existing_ids = set()
    if os.path.exists(STORIES_FILE):
        with open(STORIES_FILE) as f:
            prev = json.load(f)
        existing_stories = prev.get("stories", [])
        existing_ids = {s["id"] for s in existing_stories}
        print(f"Loaded {len(existing_stories)} existing stories from stories.json")

    top_groups = sorted(groups, key=lambda g: g["paper_count"], reverse=True)[:MAX_GROUPS]
    to_run = [g for g in top_groups if story_id_for_group(g["group_id"]) not in existing_ids]
    skipped = len(top_groups) - len(to_run)
    if skipped:
        print(f"Skipping {skipped} already-summarised group(s).")

    total = len(to_run)
    print(f"Processing {total} group(s) ({MAX_WORKERS} at a time, {SUBMIT_DELAY}s between starts)...\n")

    stop_event = threading.Event()
    result_queue = queue_module.Queue()
    stories = list(existing_stories)
    all_results = []
    consecutive_quota = 0
    done = 0
    pending = 0

    def handle_result(gid, status, story, fixes):
        nonlocal consecutive_quota, done, pending
        done += 1
        pending -= 1
        all_results.append((gid, status, story, fixes))

        prefix = f"[{done}/{total}] group {gid:>3}"
        if status == "ok":
            story["id"] = story_id_for_group(gid)
            headline = story.get("headline", "")[:60]
            fix_note = f" | {len(fixes)} fix(es)" if fixes else ""
            print(f"{prefix} | OK: \"{headline}\"{fix_note}")
            consecutive_quota = 0
            stories.append(story)
        elif status == "quota":
            msg = fixes[0][:100] if fixes else ""
            print(f"{prefix} | QUOTA ERROR (all retries failed): {msg}")
            consecutive_quota += 1
            if consecutive_quota >= CIRCUIT_BREAKER_THRESHOLD:
                print(f"\n*** Circuit breaker: {consecutive_quota} quota errors in a row. Stopping. ***")
                stop_event.set()
        elif status == "cancelled":
            print(f"{prefix} | cancelled")
        elif status == "rejected":
            reason = "; ".join(fixes[:2]) if fixes else "unknown"
            print(f"{prefix} | rejected: {reason}")
            consecutive_quota = 0
        elif status == "none":
            print(f"{prefix} | returned None (JSON parse error)")
            consecutive_quota = 0
        else:
            msg = fixes[0][:100] if fixes else status
            print(f"{prefix} | ERROR: {msg}")
            consecutive_quota = 0

    def drain(max_seconds=None):
        """Read from result_queue for up to max_seconds (None = until pending == 0)."""
        deadline = (time.monotonic() + max_seconds) if max_seconds else None
        while pending > 0:
            if stop_event.is_set() and max_seconds is not None:
                break
            remaining = (deadline - time.monotonic()) if deadline else 2.0
            if remaining <= 0:
                break
            try:
                item = result_queue.get(timeout=min(1.0, remaining))
                with print_lock:
                    handle_result(*item)
            except queue_module.Empty:
                pass

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for i, g in enumerate(to_run):
            if stop_event.is_set():
                break

            # sleep between submissions, processing results during the gap
            if i > 0:
                drain(max_seconds=SUBMIT_DELAY)
                if stop_event.is_set():
                    break

            f = executor.submit(run_group, g, stop_event)
            pending += 1
            f.add_done_callback(lambda fut: result_queue.put(fut.result()))

        # drain all remaining results after last submission
        drain(max_seconds=None)

    # write output
    stories.sort(key=lambda s: s.get("published", ""), reverse=True)
    now_ist = datetime.now(IST)
    output = {
        "edition_date": now_ist.strftime("%Y-%m-%d"),
        "generated_at": now_ist.isoformat(),
        "stories": stories,
    }
    with open(STORIES_FILE, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # summary
    succeeded = [r for r in all_results if r[1] == "ok"]
    failed = [r for r in all_results if r[1] not in ("ok", "cancelled")]
    cancelled = [r for r in all_results if r[1] == "cancelled"]

    print(f"\n{'=' * 52}")
    print(f"Done: {len(succeeded)} new  |  {len(failed)} failed  |  {len(cancelled)} cancelled  |  {len(existing_stories)} already had")

    if failed:
        by_kind = Counter(r[1] for r in failed)
        print("\nFailures:")
        for kind, count in by_kind.most_common():
            print(f"  {kind}: {count}")
            for gid, s, _, fixes in failed:
                if s == kind and fixes:
                    print(f"    group {gid}: {fixes[0][:120]}")

    topic_counts = Counter(s.get("topic", "?") for s in stories)
    print("\nStories by topic:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1]):
        print(f"  {topic:<20} {count}")

    print(f"\nWrote {len(stories)} total stories → {STORIES_FILE}")


if __name__ == "__main__":
    main()
