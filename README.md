# POV — A Daily News Brief That Shows You How Different Papers Told the Same Story

[![AWS Amplify](https://img.shields.io/badge/AWS_Amplify-Hosting-FF9900?logo=awsamplify&logoColor=white)](https://main.d1qvq9xkp1k5gm.amplifyapp.com)
[![Amazon Polly](https://img.shields.io/badge/Amazon_Polly-Neural_TTS-232F3E?logo=amazonaws&logoColor=white)](https://aws.amazon.com/polly/)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![HTML5](https://img.shields.io/badge/Frontend-Static_HTML-E34F26?logo=html5&logoColor=white)](frontend/)
[![Sources](https://img.shields.io/badge/RSS_Sources-21-9E4A57)](pipeline/feeds.py)
[![Build](https://img.shields.io/badge/Build_Step-None-4E9A06)](frontend/)

> **A news app for people who only ever see one framing.**
> Reads 21 newspaper RSS feeds, clusters articles into real events, drops anything only one paper covered, and shows you what every outlet agrees on — then exactly where they diverge, in each paper's own words.

Built in four days for the **WeMakeDevs × AWS Bharat Builds Tour, Stop 1: First Commit**.

**Live app → [main.d1qvq9xkp1k5gm.amplifyapp.com](https://main.d1qvq9xkp1k5gm.amplifyapp.com)**

---

## Table of Contents

1. [The Problem](#the-problem)
2. [Positioning: We Make Bias Visible, Not Absent](#positioning-we-make-bias-visible-not-absent)
3. [System Architecture](#system-architecture)
4. [Key Capabilities & Features](#key-capabilities--features)
5. [AWS Services Used](#aws-services-used)
6. [Supported News Sources](#supported-news-sources)
7. [Quickstart](#quickstart)
8. [Local Development & Run Guide](#local-development--run-guide)
9. [Core Workflows](#core-workflows)
10. [Pipeline Stage Reference](#pipeline-stage-reference)
11. [Data Contract](#data-contract)
12. [Copyright Policy](#copyright-policy)
13. [Project Directory Layout](#project-directory-layout)
14. [Known Limitations](#known-limitations)
15. [Roadmap](#roadmap)
16. [Team](#team)

---

## The Problem

Gen Z is disengaged from current affairs. The ones who do follow the news mostly get it from Instagram — a single account, a single framing, presented as the whole picture.

The problem isn't that the framing is wrong. The problem is that you don't know it's *a* framing. You're only ever shown one.

---

## Positioning: We Make Bias Visible, Not Absent

POV does **not** claim to remove bias.

"AI removes bias from the news" invites an unanswerable question: *who decided what counts as biased?* There is no good answer, and any product that claims otherwise is one prompt away from being wrong in public.

POV makes bias **visible** instead. Seven papers, seven headlines, grouped by the editorial choice each one made, side by side on a single screen. The reader forms their own view.

### The Product Rule

**Only stories covered by 2 or more distinct papers are shown.** Single-source stories are dropped by the pipeline before they reach the app. A story with one source has no "where the papers differ" — and that screen is the entire product. This is a feature, not a limitation.

---

## System Architecture

**There is no live backend.** The pipeline precomputes everything ahead of time and writes one file. The app downloads that file. Nothing runs on the user's device, nothing sits in the request path, and nothing can be slow or fail mid-demo.

```
                          +--------------------------------+
                          |   21 Newspaper RSS Feeds       |
                          | National / Karnataka / UP /    |
                          |   Sports / International       |
                          +--------------------------------+
                                          |
                                          v
                          +--------------------------------+
                          |   1. fetch.py                  |
                          | MD5 link dedupe, 2-day prune,  |
                          | per-source ingest report       |
                          +--------------------------------+
                                          | articles.json
                                          v
                          +--------------------------------+
                          |   2. group.py                  |
                          | Keyword clustering: >= 3 shared|
                          | significant words, 3-day window|
                          +--------------------------------+
                                          | groups.json
                                          v
                          +--------------------------------+
                          |   3. run_all.py   (Gemini)     |
                          | Headline / agreed facts /      |
                          | framing clusters / jargon /    |
                          | people / affects / read time   |
                          | Parallel calls, circuit breaker|
                          +--------------------------------+
                                          |
                                          v
                          +--------------------------------+
                          |   4. people_lookup.py          |
                          | Wikipedia REST: photo, short   |
                          | description, article link      |
                          | Cached in people_cache.json    |
                          +--------------------------------+
                                          | stories.json
                                          v
                          +--------------------------------+
                          |   5. make_audio.py             |
                          |   >>>  AMAZON POLLY  <<<       |
                          | SSML pacing, neural engine,    |
                          | one mp3 per story id           |
                          +--------------------------------+
                                          |
                                          v
              +--------------------------------------------------+
              |          >>>  AWS AMPLIFY HOSTING  <<<           |
              |  frontend/index.html        landing page         |
              |  frontend/app/index.html    the app              |
              |  frontend/app/stories.json  today's brief        |
              |  frontend/app/audio/*.mp3   narration            |
              |  Auto-deploys on every push to main. No build.   |
              +--------------------------------------------------+
                                          |
                                          v
                          +--------------------------------+
                          |   Reader's phone               |
                          | Downloads one JSON file.       |
                          | Zero server round-trips after. |
                          +--------------------------------+
```

Like a newspaper: printed once, in one place, and every reader gets the same copy. The pipeline is the printing press. `stories.json` is the paper. Every phone just reads it.

---

## Key Capabilities & Features

- **Framing-Aware Clustering** — Papers are grouped by the *editorial decision* they made, not by sub-topic. Two papers belong in the same cluster only if they led with the same thing, centred the same voice, or implied the same winner. A cluster whose headlines are substantively identical is not a difference and does not count.
- **Verbatim Headline Preservation** — Every paper's headline is reproduced exactly as published. The precise wording *is* the evidence of framing; paraphrasing it would destroy the thing the app exists to show.
- **Multi-Source Enforcement** — The pipeline drops any event with fewer than two distinct outlets, guaranteeing every story in the brief is comparable.
- **Inline Jargon Expansion** — Unfamiliar terms carry a dotted underline and expand in place on tap. No dictionary trip, no context loss.
- **Person Context Cards** — Named individuals are enriched from the Wikipedia REST API with a photo, a one-line description, and a link out. Single-word names are deliberately skipped: a missing card beats a confidently wrong one.
- **Neural Narration** — Every story is pre-rendered to speech by Amazon Polly with SSML pacing, so the brief is listenable while getting ready.
- **Read-Time Budgeting** — Stories carry a `read_seconds` field; the app fills the reader's chosen time budget and stops, with a floor of two stories so the brief is never empty.
- **Interest-Weighted Ordering** — Chosen topics surface first without filtering anything out, so personalisation never produces a two-story brief.
- **Always Links Out** — Every paper card opens the original article. POV sends readers to the papers; it does not replace them.
- **Zero-Latency Read Path** — Static files only. No API gateway, no cold start, no database in the request path.

---

## AWS Services Used

| Service | Role | Why This Way |
|---|---|---|
| **AWS Amplify Hosting** | Serves the entire application. Connected directly to this repository — every push to `main` triggers an automatic redeploy. | The app is static HTML, so there is no build command and no build container. `baseDirectory: frontend`. |
| **Amazon Polly** | Generates story narration. Neural engine, Indian English voice, SSML markup for prosody rate and inter-sentence pauses. | Called **in the pipeline, not in the browser**. A static page cannot hold AWS credentials safely, so the MP3s are precomputed and committed. Same principle as `stories.json`. |

Both services follow one rule: **precompute everything, so the read path is static files.**

---

## Supported News Sources

21 feeds across five buckets.

| Bucket | Sources |
|---|---|
| **National (8)** | The Hindu · Indian Express · Hindustan Times · Times of India · NDTV · Business Standard · Mint · The Print |
| **Karnataka (3)** | The Hindu (Karnataka) · Deccan Herald · Times of India (Karnataka) |
| **Uttar Pradesh (3)** | Indian Express (Lucknow) · Hindustan Times (Lucknow) · Times of India (Lucknow) |
| **Sports (3)** | ESPNcricinfo · Times of India Sports · Hindustan Times Sports |
| **International (4)** | Reuters · AP · BBC News · Al Jazeera |

Reuters and AP no longer publish public RSS, so their articles arrive via Google News site-scoped feeds. Feed definitions live in [`pipeline/feeds.py`](pipeline/feeds.py) — adding a source is adding one dictionary entry; no pipeline code changes.

### Topic Taxonomy

Stories are classified into exactly one of:

`Politics` · `Economy`  · `Health` · `Campus & exams` · `Sport` 

Any story returned with a topic outside this list is rejected by the validator.

---

## Quickstart

The frontend has **no build step**. Clone and serve.

```bash
git clone https://github.com/vaanyaagarwal27/POV-News-App.git
cd POV-News-App/frontend
python3 -m http.server 8080
```

Open `http://localhost:8080`.

> **Note:** opening `index.html` directly from disk will not work. Browsers block `fetch` on `file://` URLs, so `stories.json` will never load. Always serve over HTTP.

---

## Local Development & Run Guide

### 1. Frontend

The app is a single self-contained HTML file with inline styles. There is no framework, no bundler, and no `node_modules`.

```bash
cd frontend
python3 -m http.server 8080
```

| File | Purpose |
|---|---|
| `frontend/index.html` | Landing page |
| `frontend/app/index.html` | The entire application |
| `frontend/app/stories.json` | Today's brief |
| `frontend/app/audio/` | Polly narration, one MP3 per story ID |

After editing, hard-refresh with `Cmd+Shift+R` — Chrome caches aggressively.

### 2. Pipeline

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r pipeline/requirements.txt

export GEMINI_API_KEY="your-key-here"   # never commit this

cd pipeline
python3 fetch.py        # RSS -> articles.json
python3 group.py        # articles -> groups.json
python3 run_all.py      # groups -> stories.json (Gemini + Wikipedia)
```

Then publish the output to the app:

```bash
cp pipeline/data/stories.json frontend/app/stories.json
```

### 3. Audio Generation

Requires AWS credentials with Polly access.

```bash
aws login
aws sts get-caller-identity     # confirm the account
python3 pipeline/make_audio.py
```

Existing MP3s are skipped, so re-running is cheap. To regenerate everything after changing voice or pacing:

```bash
rm frontend/app/audio/*.mp3
python3 pipeline/make_audio.py
```

### 4. Deploy

Amplify is already connected to this repository. Deployment is a `git push`.

| Setting | Value |
|---|---|
| Source | GitHub, branch `main` |
| Build command | *(empty)* |
| Build output directory | `frontend` |

A build takes 1–3 minutes. The live URL updates automatically.

---

## Core Workflows

### Workflow 1: Daily Brief Generation

1. `fetch.py` pulls all 21 feeds, hashes each link, discards duplicates and anything older than two days, and prints a per-source report (`in feed / new / skipped / opinion skipped / junk skipped`).
2. `group.py` extracts significant keywords fresh from the day's headlines — nothing about topics is hardcoded, only the stopword list is fixed — and clusters articles sharing three or more of them within a three-day window.
3. `run_all.py` sends each group to Gemini in parallel, with retries and a circuit breaker that halts after consecutive quota errors so a partial run is never corrupted. Groups already summarised in a previous run are skipped by stable ID.
4. The validator rejects invalid topics, trims over-length headlines at a word boundary, and discards any group with fewer than two distinct papers.
5. `make_audio.py` renders narration for each surviving story.

### Workflow 2: Reading a Brief

1. **Setup** — name, state, daily read time, topics of interest. Stored locally, asked once.
2. **The brief** — one story per card. Progress bar, story count, impact tags, "covered by *N* papers". Swipe or tap for the next.
3. **Inside a story** — agreed facts in plain sentences. Dotted-underlined jargon expands on tap; highlighted names open a person card with photo and Wikipedia link.
4. **Listen** — tap to play the Polly narration. Playback pauses, resumes, and stops automatically on navigation.
5. **Where the papers differ** — numbered editorial angles, each with the papers that took it and their exact headlines. Any card opens the original article.
6. **Done** — "You're caught up."

### Workflow 3: Adding a News Source

1. Add one entry to the list in `pipeline/feeds.py`:
   ```python
   {"name": "The Telegraph", "url": "https://www.telegraphindia.com/feeds/rss.jsp"},
   ```
2. Run `python3 fetch.py` and check the per-source report shows a non-zero article count.
3. Run the rest of the pipeline. No other file changes.

### Workflow 4: Tuning the Framing Prompt

The clustering prompt in `run_all.py` is the product. Its current rules:

- A cluster is a **framing choice**, not a sub-topic.
- The `angle` must be a sentence a reader could *disagree with* — "Frames the deal as a climbdown from the original ambition", not "Coverage of the deal".
- Never create a cluster whose papers have substantively identical headlines.
- Prefer 2–3 sharp clusters over 4+ weak ones. A single-paper cluster is valid and often the most interesting.
- `headline` is copied **exactly** from the source article, never rewritten.

Change the prompt, re-run against a single group first, inspect the output, and only then run the full batch.

---

## Pipeline Stage Reference

| Stage | Script | Input | Output | External Calls |
|---|---|---|---|---|
| 1 | `fetch.py` | 21 RSS URLs | `data/articles.json` | HTTP (RSS) |
| 2 | `group.py` | `articles.json` | `data/groups.json` | — |
| 3 | `run_all.py` | `groups.json` | `data/stories.json` | Gemini 2.5 Flash |
| 3b | `people_lookup.py` | person names | enriched `people[]` | Wikipedia REST |
| 4 | `make_audio.py` | `stories.json` | `frontend/app/audio/*.mp3` | Amazon Polly |

### Engineering Notes

- **Gemini model string:** `models/gemini-2.5-flash`. The short form `gemini-2.5-flash` maps to a tiny 20-requests-per-day quota — a trap worth documenting.
- **Fenced JSON:** Gemini occasionally wraps responses in code fences despite instructions not to. The parser strips fences before decoding and prints the raw response on failure.
- **Article cap:** at most ~8 articles per group are sent to the model. More never improves the framing comparison and costs latency.
- **Secrets:** `GEMINI_API_KEY` lives in an environment variable and is never committed. `.env` is gitignored.
- **Person matching:** Wikipedia lookups require a multi-word name. A single-word first name matched an unrelated public figure during testing; the guard eliminates the entire failure class.
- **Idempotency:** both `run_all.py` and `make_audio.py` skip work already done, so interrupted runs resume cleanly.

---

## Data Contract

`stories.json` is the single interface between the pipeline and the app. Change it here first.

```jsonc
{
  "edition_date": "2026-09-20",
  "generated_at": "2026-09-20T17:04:00+05:30",
  "stories": [
    {
      "id": "6364d3f0",                    // stable hash; also the audio filename
      "headline": "...",                   // <= 110 chars, cut at a word boundary
      "topic": "Sport",                    // one of the 10 allowed topics
      "source_count": 7,
      "read_seconds": 79,                  // drives read-time budgeting
      "disagreement": 2,                   // 0 = all papers framed it identically
      "teaser": "...",
      "why_it_matters": "...",
      "published": "2026-09-20",           // date only, no time

      "agreed_facts": [                    // plain strings, no attribution
        "India's men's hockey team defeated Indonesia 13-1 in their Pool A match.",
        "Dilpreet Singh scored four goals."
      ],

      "clusters": [                        // the product
        {
          "angle": "Frames the result as a rebound after a poor World Cup.",
          "papers": [
            {
              "name": "Hindustan Times Sports",
              "headline": "After World Cup low, India start afresh with 13-1 demolition",
              "url": "https://..."
            }
          ]
        }
      ],

      "people": [
        {
          "name": "Elavenil Valarivan",
          "who": "Indian sport shooter (born 1999)",
          "detail": "...",
          "image": "https://upload.wikimedia.org/...",
          "wiki_url": "https://en.wikipedia.org/wiki/..."
        }
      ],

      "jargon":  [{ "term": "tariffs", "meaning": "Taxes charged on imported goods." }],
      "affects": ["athletes", "sports fans"],
      "regions": ["national", "international"]
    }
  ]
}
```

---

## Copyright Policy

POV never reproduces article body text.

- **Headlines and RSS summaries only.** Nothing beyond what the feed publishes.
- **Headlines are verbatim.** Reproducing a paper's exact wording is the point — a paraphrase would erase the framing evidence.
- **Every card links out.** All attribution is on-screen with a direct link to the original.
- **We send readers to the papers.** POV is a way in to journalism, not a substitute for it.

---

## Project Directory Layout

```text
POV-News-App/
├── README.md                       # This document
├── .gitignore                      # venv, .env, __pycache__, pipeline/data/
│
├── frontend/                       # Static app — no build step, no dependencies
│   ├── index.html                  # Landing page
│   ├── support.js                  # Design-canvas runtime
│   ├── img/                        # Landing page imagery
│   ├── screens/                    # Design reference screens
│   └── app/
│       ├── index.html              # The entire application, one self-contained file
│       ├── extras.html             # Secondary screens
│       ├── stories.json            # Today's brief — the read path
│       ├── mock-stories.json       # Hand-written fixture, kept as a fallback
│       ├── stateOptions.js         # Indian state list for onboarding
│       ├── audio/                  # Polly narration, <story-id>.mp3
│       └── assets/                 # Illustrations and logo
│
├── pipeline/                       # Precompute layer
│   ├── feeds.py                    # The 21 RSS sources
│   ├── fetch.py                    # Fetch, dedupe, prune
│   ├── group.py                    # Keyword clustering into events
│   ├── run_all.py                  # Gemini summarisation, parallel + circuit breaker
│   ├── people_lookup.py            # Wikipedia enrichment with local cache
│   ├── make_audio.py               # Amazon Polly SSML narration
│   ├── requirements.txt            # Python dependencies
│   └── data/                       # Intermediate output (gitignored)
│       ├── articles.json
│       ├── groups.json
│       ├── stories.json
│       └── people_cache.json
│
└── shared/
    └── stories.json                # Canonical pipeline output
```

---

## Known Limitations

We would rather state these than have them found.

- **Keyword grouping over-merges.** Articles sharing a prominent proper noun can be clustered into one loose "story" even when they cover unrelated events. Embeddings would fix this properly.
- **Local coverage is two states.** Karnataka and Uttar Pradesh have dedicated feeds; every other state sees national coverage only. Adding a state is two RSS URLs.
- **Low-volume topics are sparse.** Entertainment and Culture rarely clear the two-paper bar on a given day. The 2+ rule is doing its job, but it means some topics are thin.
- **Single-word names are skipped entirely** in person lookups. Deliberate: a wrong card is worse than no card.
- **Interests order the brief, they do not filter it.** At current daily volume, filtering to one topic would produce a two-story brief.
- **The pipeline runs on a developer machine**, not on a schedule in the cloud. See roadmap.

---

## Roadmap

| Next | What it involves |
|---|---|
| **Pipeline on AWS Lambda** | EventBridge fires on an hourly timer, Lambda runs the pipeline, output writes to S3. Because the pipeline already writes exactly one file, this is a deployment change rather than an architecture change. |
| **Embedding-based grouping** | Replace keyword matching with semantic similarity so "truce" and "ceasefire" cluster together and unrelated stories about the same person do not. |
| **Bedrock instead of Gemini** | Consolidates the AI layer onto AWS and removes the external quota dependency. |
| **True interest filtering** | Viable once daily story volume supports a full brief within a single topic. |
| **State expansion** | Two RSS URLs per state. The pipeline does not change. |
| **Seen-story tracking** | Track read story IDs locally and suppress fully-read stories on the next visit, while keeping ongoing stories in view. |

---

## Team

Built over four days by two second-year Computer Science students at BMS College of Engineering, Bengaluru.

| | |
|---|---|
| **Vaanya Agarwal** ([@vaanyaagarwal27](https://github.com/vaanyaagarwal27)) | Pipeline, data, AWS |
| **Hamsini Velugoti** ([@Hamsini-Velugoti](https://github.com/Hamsini-Velugoti)) | Frontend, design, interaction |

Neither of us writes code unaided. POV was built entirely through AI-assisted development — which turns out to be its own discipline: knowing what to ask for, in what order, how small to make each step, and being able to recognise when the answer that comes back is wrong.
