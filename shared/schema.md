# stories.json schema

## Top level

| Field | Type | Description |
|---|---|---|
| `edition_date` | string | YYYY-MM-DD, date the pipeline ran |
| `generated_at` | string | ISO 8601 timestamp, e.g. `2026-09-18T06:30:00+05:30` |
| `stories` | list | List of story objects (see below) |

---

## Each story

| Field | Type | Description |
|---|---|---|
| `id` | string | Short unique identifier |
| `headline` | string | Neutral headline, max 110 characters |
| `topic` | string | One of: `Politics`, `Economy`, `Jobs`, `Tech`, `Climate`, `Courts`, `Health`, `Campus & exams`, `Sport`, `Culture` |
| `regions` | list | At least 1 entry. Values: `"national"`, `"international"`, or an official Indian state/UT name (see full list below) |
| `published` | string | YYYY-MM-DD |
| `read_seconds` | number | Estimated reading time in seconds |
| `source_count` | number | Number of papers covered; at least 2 |
| `disagreement` | number | 0–3, how much papers diverge |
| `teaser` | string | One line naming the sharpest difference between sources; empty string if `disagreement` is 0 |
| `why_it_matters` | string | One sentence explaining the story's significance |
| `affects` | list | 1–3 short groups affected, e.g. `"commuters"` |
| `agreed_facts` | list | Sentences all sources agree on |
| `clusters` | list | List of angle objects (see below). 1 cluster if `disagreement` is 0, else 2 or more |
| `jargon` | list | List of `{ term, plain }` objects. Each `term` appears verbatim in `agreed_facts`. Can be empty |
| `people` | list | List of `{ name, who }` objects. Each `name` appears verbatim in `agreed_facts`. Can be empty |

### Each cluster

| Field | Type | Description |
|---|---|---|
| `angle` | string | The editorial angle or framing of this group of papers |
| `papers` | list | List of `{ name, headline, url }` objects. `headline` is the paper's real RSS headline — never rewritten |

---

## Official Indian states and UTs (all 36)

Andhra Pradesh, Arunachal Pradesh, Assam, Bihar, Chhattisgarh, Goa, Gujarat, Haryana, Himachal Pradesh, Jharkhand, Karnataka, Kerala, Madhya Pradesh, Maharashtra, Manipur, Meghalaya, Mizoram, Nagaland, Odisha, Punjab, Rajasthan, Sikkim, Tamil Nadu, Telangana, Tripura, Uttar Pradesh, Uttarakhand, West Bengal, Andaman and Nicobar Islands, Chandigarh, Dadra and Nagar Haveli and Daman and Diu, Delhi, Jammu and Kashmir, Ladakh, Lakshadweep, Puducherry

---

## Rules the app follows

- Topic and region choices last for the session only.
- Show a story only if its `topic` was picked by the user.
- Show a story if `regions` includes the user's state, `"national"`, or `"international"`.
- **Ordering:** `disagreement` 0 last; then user's state first; then highest `disagreement`; then newest `published`.
- Add stories until the user's chosen reading time is used up; always show at least 1 story.
