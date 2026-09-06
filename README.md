# NEXUS — Narrative & Influence Intelligence

**Smart India Hackathon 2026 · SIH26152 · Social Media Analytics · NTRO**

> **We track how narratives emerge, mutate and move — then keep the evidence that proves every conclusion.**

NEXUS is a free-first, evidence-backed cross-platform social-media analytics framework built for SIH26152. It normalizes public/authorized social data into one chronology and implements the four required analytical vectors:

1. **Sentiment Analysis** — polarity, stance, emotion signals and temporal sentiment movement.
2. **Privacy-safe Audience/Demographic Profiling** — aggregate language, broad public/self-declared geography and supportable audience attributes with small-group suppression.
3. **Trend & Narrative Tracking** — semantic narrative clustering, burst/growth scoring, chronology, mutation/correction tracking and cross-platform convergence.
4. **Link / Network Analysis** — observed interaction topology, PageRank, betweenness, communities, bridge nodes and high-reach nodes.

The framework is deliberately honest about data coverage. Every normalized event is labelled:

- `LIVE` — fetched from a reachable public/authorized source during the run;
- `REPLAY` — deterministic demo/replayed evidence;
- `IMPORT` — analyst-supplied public/exported data.

NEXUS never relabels replay/import data as live, never claims private-account access, and uses **“earliest observed in our collected dataset”** rather than claiming absolute internet origin.

---

## What makes NEXUS different

A normal social dashboard asks:

- What hashtag is trending?
- How many mentions exist?
- Is sentiment positive or negative?

NEXUS asks:

- Which *narrative* is emerging even when the wording changes?
- What is its exact observed chronology?
- How did sentiment and stance change as it spread?
- Which observed accounts/communities amplified it?
- Which nodes bridge otherwise separated communities?
- How did the narrative move across platforms?
- What evidence supports the insight?
- How complete is the collection coverage?
- Is the evidence strong enough to issue a certificate, or should the system **ABSTAIN**?

---

# Platform coverage

NEXUS separates **acquisition** from **analytics**. A vendor changing its API does not require rewriting the four analytics engines.

| Platform | Official / richer path | Free / public / resilience path | Default truth |
|---|---|---|---|
| **X / Twitter** | X API v2 recent search | configurable permitted RSS/public bridge + JSON import/replay | official live search requires developer access/credits; no fake free API claim |
| **Telegram** | Telegram Bot API `getUpdates` | **zero-key public-channel preview** (`t.me/s/<channel>`) | strongest zero-cost live demo source |
| **Instagram** | Meta Graph authorized account sync + **official hashtag discovery** (`ig_hashtag_search → recent_media`) | best-effort genuinely public profile path + import/replay | official path requires applicable Meta permissions/App Review |
| **YouTube** | YouTube Data API v3 **video-first search + comments where available** | **zero-key yt-dlp public metadata** | a video is retained even when comments are disabled |
| **Bluesky** | public AT Protocol | same | zero-key public search |
| **Reddit** | OAuth when configured | public JSON search where permitted + import | endpoint/network policy may restrict anonymous access |
| **Mastodon** | instance API | public instance search / alternate instance | availability depends on instance policy |
| **Facebook** | authorized Page Graph API | import/replay | optional additional source |

### Important X/Instagram truth

NEXUS does **not** pretend that an unrestricted free live search API exists when a commercial platform does not provide one. For restricted sources, the framework uses the official connector when access exists and otherwise falls back to a permitted public bridge/public-profile path or analyst import/replay. The downstream four-vector analytics remain fully operational.

See: [`docs/FREE_SOURCE_MATRIX.md`](docs/FREE_SOURCE_MATRIX.md)

---

# Architecture

```text
 X API / bridge / import ──────┐
 Telegram Bot / public page ───┤
 YouTube API / yt-dlp ─────────┤
 Instagram Graph / public ─────┤
 Bluesky / Reddit / Mastodon ──┤
 JSON replay/import ────────────┘
                │
                ▼
       Connector / Normalizer
                │
                ▼
        Canonical SocialEvent
                │
                ├── provenance + SHA-256 hash
                ├── sentiment / stance / emotion
                ├── semantic narrative clustering
                ├── burst / trend decomposition
                ├── graph / influence topology
                ├── aggregate demographics
                └── evidence certificate / ABSTAIN
                │
                ▼
       FastAPI analytics (:8000)
                │
                ├── direct demo mode
                │
                └── optional Spring gateway (:8080)
                              │
                              ▼
               React + TypeScript console (:5173)
```

### Hackathon-default stack

- Python 3.11+
- FastAPI
- SQLite
- NetworkX
- scikit-learn TF-IDF / cosine similarity
- VADER + transparent lexical fallbacks
- React + TypeScript + Vite
- optional Spring Boot gateway
- BeautifulSoup public-page parser
- yt-dlp zero-key YouTube metadata fallback
- Instaloader best-effort public Instagram fallback

**No Docker and no paid LLM are required for the core demo.**

---

# Fastest way to run — Windows

Prerequisites:

- Python 3.11+
- Node.js 20+
- internet connection for the first dependency install
- Maven + Java 17 only if you want the optional Spring gateway

Run:

```bat
scripts\start_demo.bat
```

The launcher now performs a hard preflight before the UI opens:

1. creates `.env` from `.env.example` if required;
2. creates `.venv`;
3. installs backend dependencies + pytest;
4. installs frontend dependencies;
5. checks required project files/configuration;
6. parses Python source/tests;
7. runs the backend pytest suite;
8. runs the strict TypeScript production build;
9. starts FastAPI;
10. seeds the deterministic fictional jury dataset;
11. starts the React analyst console;
12. opens the browser.

Open manually if required:

- Analyst console: `http://127.0.0.1:5173`
- FastAPI docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`
- Evidence certificates: `http://127.0.0.1:8000/api/certificates`

---

# Preflight only

From repository root:

```bat
python scripts\preflight.py
```

For the strongest validation, run it through the project venv after dependencies are installed:

```bat
.venv\Scripts\python scripts\preflight.py
```

The preflight checks source structure, Python syntax, environment configuration, pytest and the frontend production build when dependencies are available.

---

# Manual run

## Backend

```bat
copy .env.example .env
python -m venv .venv
.venv\Scripts\pip install -r backend-ai\requirements.txt pytest
cd backend-ai
..\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Frontend

In a second terminal:

```bat
cd frontend
npm install
npm run dev
```

## Seed deterministic demo

Use the UI **Seed Demo** button or:

```http
POST http://127.0.0.1:8000/api/demo/seed
Content-Type: application/json

{"reset": true}
```

---

# FREE SOURCE LAB

The bar above the analyst console gives the team fast, judge-friendly acquisition controls.

### `Collect Free Mix`

Runs independent public/zero-key sources concurrently and uses `Promise.allSettled`, so one vendor failure does not kill the whole collection attempt:

- YouTube zero-key metadata
- Bluesky public search
- Reddit public JSON search
- Mastodon public instance search
- Telegram public channel if a target is supplied
- Instagram public profile if a target is supplied

The UI reports which sources succeeded and which were unavailable.

### Individual controls

- **Telegram Public** — zero-key public channel preview.
- **YouTube ₹0** — yt-dlp public search metadata.
- **Bluesky** — public AT Protocol search.
- **Reddit** — low-volume public JSON search where permitted.
- **Mastodon** — public instance search.
- **IG Hashtag API** — official Meta hashtag discovery when authorized.
- **Instagram Public** — best-effort public-profile fallback.
- **X Public Bridge** — configured permitted RSS/public bridge.
- **Verify Evidence** — summarizes `CERTIFIED` vs `ABSTAIN` narrative certificates.

---

# Live connector configuration

Copy:

```bat
copy .env.example .env
```

Fill only the integrations you actually have permission to use.

## Telegram Bot API — free

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_CHAT_IDS=
```

NEXUS uses `getUpdates`, serializes concurrent polls and advances the update offset so continuous collection does not reread a fixed queue forever. If a webhook conflicts with polling, NEXUS surfaces an explicit error instead of silently failing.

For a zero-key public channel, no token is needed; use **Telegram Public** in the FREE SOURCE LAB.

## YouTube Data API v3

```env
YOUTUBE_API_KEY=
```

Official search is **video-first**. Each matching video becomes evidence before comment retrieval is attempted. If comments are disabled/restricted, the video still remains in the dataset.

The zero-key path needs no key and uses public video metadata only.

## X API v2

```env
X_BEARER_TOKEN=
X_MAX_RESULTS_PER_RUN=50
X_MAX_PAGES_PER_RUN=2
```

Optional permitted bridge:

```env
X_PUBLIC_RSS_URL_TEMPLATE=
```

The bridge template may use `{query}` and/or `{target}` placeholders. NEXUS does not ship a hard-coded third-party mirror because availability and permission can change.

## Instagram / Meta Graph

```env
META_GRAPH_VERSION=v23.0
META_ACCESS_TOKEN=
META_INSTAGRAM_ACCOUNT_ID=
META_FACEBOOK_PAGE_ID=
```

With applicable permissions, NEXUS supports:

- authorized Instagram professional-account media/comments;
- official hashtag discovery via `ig_hashtag_search` and `recent_media`;
- authorized Facebook Page feed/comments.

The public-profile fallback never bypasses private-account/login controls.

## Mastodon

```env
MASTODON_BASE_URL=https://mastodon.social
```

Switch to another instance if the selected instance does not permit anonymous status search.

---

# Canonical event contract

All acquisition paths normalize to one event model containing, where available:

- platform
- original platform event ID
- event type
- public author identity + privacy-preserving pseudonymous ID
- original text
- language
- `created_at`
- separate `ingested_at`
- source URL
- parent / conversation IDs
- mentions
- hashtags
- URLs/domains
- engagement counters
- minimal public profile signals
- explicit `LIVE | REPLAY | IMPORT`
- connector run ID
- SHA-256 provenance hash
- sentiment / stance / emotion values
- topic terms
- narrative cluster ID
- trend / quality metadata

Duplicate `(platform, source_event_id)` records are suppressed.

---

# Vector 1 — Sentiment

NEXUS provides:

- positive / neutral / negative label;
- continuous sentiment score;
- stance signal;
- emotion indicators;
- sarcasm probability as a secondary signal;
- timeline-level sentiment movement;
- alert-level sentiment shift explanations.

The default lightweight path is intentionally local and deterministic enough for a hackathon. Transformer models can be added later without changing the event/API contracts.

---

# Vector 2 — Privacy-safe demographic / audience signals

The demographic endpoint returns **aggregate distributions only**.

Current support includes:

- language;
- broad geography only from explicit/public source fields;
- professional-interest fields only where supportable;
- age bracket only when explicitly/supportably supplied, otherwise unknown;
- k-anonymity-style suppression of small groups;
- coverage and confidence.

NEXUS does not generate sensitive protected-trait guesses for named individuals.

---

# Vector 3 — Trends & narrative lineage

NEXUS groups semantically related messages using:

- TF-IDF unigrams/bigrams;
- cosine similarity;
- time proximity;
- shared hashtag evidence;
- shared URL/domain evidence;
- connected components.

The explainable trend score combines:

```text
0.30 × normalized volume growth
0.20 × burst deviation
0.15 × unique-author diversity
0.15 × cross-platform presence
0.10 × engagement signal
0.10 × recency
```

Statuses include:

- `EMERGING`
- `RISING`
- `VIRAL`
- `STABLE`
- `DECLINING`

The UI exposes the components rather than returning a black-box trend number.

---

# Vector 4 — Link & network analysis

Observed edges can include:

- replies;
- mentions;
- shared domains/URLs;
- time-bounded narrative co-amplification.

NEXUS calculates:

- PageRank;
- betweenness centrality;
- degree centrality;
- communities/components.

Roles:

- **High Reach Node** — ranks highly by weighted interaction centrality in the observed graph.
- **Bridge Node** — has high betweenness between observed communities.
- **Participant** — participates in the observed network without crossing role thresholds.

These are structural labels, **not accusations of maliciousness, bot status, ideology, or intent**.

---

# Evidence Certificate / ABSTAIN layer

A central NEXUS differentiator is the replayable evidence certificate.

Endpoints:

```text
GET /api/certificates
GET /api/certificates/narrative/{narrative_id}
GET /api/certificates/alert/{alert_id}
```

A certificate can contain:

- narrative claim scope;
- witness posts;
- witness graph nodes/edges;
- snapshot SHA-256;
- witness SHA-256;
- algorithm/configuration SHA-256;
- coverage/source-mode distribution;
- confidence;
- replay result.

Minimum requirements include provenance, timestamps, evidence volume/diversity and a confidence floor. If those conditions fail, the result is:

```text
ABSTAIN
```

rather than an unsupported high-impact conclusion.

---

# API highlights

### System / collection

```text
GET  /health
GET  /api/connectors/status
GET  /api/collector/status
POST /api/collector/start
POST /api/collector/stop
POST /api/demo/seed
POST /api/ingest/replay
```

### Required/core platforms

```text
POST /api/connectors/x/search
POST /api/connectors/x/public
POST /api/connectors/telegram/poll
POST /api/connectors/telegram/public
POST /api/connectors/youtube/search
POST /api/connectors/youtube/free
POST /api/connectors/meta/sync
POST /api/connectors/instagram/hashtag
POST /api/connectors/instagram/public
```

### Additional public sources

```text
POST /api/connectors/bluesky/search
POST /api/connectors/reddit/search
POST /api/connectors/mastodon/search
```

### Analytics

```text
GET /api/overview
GET /api/timeline
GET /api/trends
GET /api/narratives
GET /api/narratives/{id}
GET /api/network
GET /api/demographics
GET /api/alerts
GET /api/events
```

### Export / trust

```text
GET /api/certificates
GET /api/certificates/narrative/{id}
GET /api/certificates/alert/{id}
GET /api/export/narrative/{id}.json
GET /api/export/narrative/{id}.csv
```

---

# Continuous collection

Current scheduler endpoints:

```text
GET  /api/collector/status
POST /api/collector/start
POST /api/collector/stop
```

Example:

```json
{
  "query": "#RiverLinkUpdate",
  "interval_seconds": 60,
  "enable_telegram": true,
  "enable_x": false,
  "enable_youtube": false
}
```

X and YouTube are opt-in in continuous mode to protect credits/quota. Telegram is the free-first default.

---

# Optional Spring Boot gateway

For a fuller enterprise-shaped demonstration:

```bat
scripts\start_full.bat
```

The Spring gateway proxies:

- core analytics;
- old official connector endpoints;
- all new free/public connector endpoints;
- official Instagram hashtag discovery;
- evidence-certificate endpoints.

The FastAPI direct mode remains the recommended simplest jury runtime.

---

# Tests

Backend:

```bat
cd backend-ai
..\.venv\Scripts\python -m pytest -q
..\.venv\Scripts\python -m compileall -q app
```

Coverage includes:

- text enrichment;
- deduplication;
- narrative clustering;
- network construction;
- privacy-safe demographics;
- Telegram public-page parsing;
- RSS bridge parsing;
- Telegram Bot API offset advancement;
- YouTube video retention when comments are disabled;
- Instagram official hashtag two-step flow;
- evidence certificates;
- API contracts.

Frontend:

```bat
cd frontend
npm install
npm run build
```

Spring gateway:

```bat
cd backend-java
mvn -B test package
```

---

# 5-minute jury flow

Use [`docs/JURY_DEMO_5_MIN.md`](docs/JURY_DEMO_5_MIN.md).

The recommended flow is:

1. open seeded Overview;
2. run one zero-key live source such as Telegram Public or Bluesky;
3. show source-mode truthfulness;
4. show Timeline sentiment movement;
5. open a rising narrative and its explainable trend decomposition;
6. show the network bridge/high-reach nodes;
7. show privacy-safe demographic aggregates;
8. click **Verify Evidence** or open the certificate endpoint;
9. finish with the source matrix / zero-cost architecture story.

**Do not test every external platform live on stage.** One or two live connectors prove acquisition; deterministic replay proves the full analytics reliably if venue internet/vendor APIs fail.

---

# Judge / implementation references

- [`docs/PS26152_TRACEABILITY.md`](docs/PS26152_TRACEABILITY.md) — requirement → code → API → UI → demo proof.
- [`docs/FREE_SOURCE_MATRIX.md`](docs/FREE_SOURCE_MATRIX.md) — official/free/fallback access strategy.
- [`docs/JURY_DEMO_5_MIN.md`](docs/JURY_DEMO_5_MIN.md) — exact presentation sequence and likely Q&A.
- [`docs/FINAL_READINESS_CHECKLIST.md`](docs/FINAL_READINESS_CHECKLIST.md) — final laptop checklist.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — deeper architecture notes.
- [`prompts/MASTER_SUPER_PROMPT.md`](prompts/MASTER_SUPER_PROMPT.md) — master autonomous build prompt.

---

# Cost model

Core deterministic demo:

**₹0 software/API cost**

Free/public live demo paths:

- Telegram public preview — ₹0
- Telegram Bot API — ₹0
- Bluesky public protocol — ₹0
- YouTube yt-dlp metadata — ₹0
- YouTube Data API — free quota when configured
- Mastodon public instance — ₹0 where permitted
- Reddit public JSON — ₹0 where permitted

Potentially restricted/paid/approval-dependent:

- X recent-search API access/credits
- Meta permissions/App Review for richer Instagram/Facebook discovery

The project never requires a paid LLM for the core SIH demonstration.

---

# Security, privacy and analytical integrity

NEXUS is designed around these rules:

- public or explicitly authorized data only;
- no credential theft;
- no private-account bypass;
- no CAPTCHA/login evasion;
- no stealth proxy rotation designed to defeat platform controls;
- no secret values committed to Git;
- source failures are visible, not hidden;
- protected/sensitive personal traits are not guessed for named users;
- graph structure is not treated as proof of intent;
- coordination signals, where added, are indicators rather than definitive bot attribution;
- earliest-observed evidence is not called absolute origin;
- insufficient evidence can produce **ABSTAIN**.

---

## Project thesis

> **NEXUS turns disconnected public social-media evidence into a replayable explanation of what narrative emerged, when it accelerated, how sentiment changed, which observed communities amplified it, and exactly what source evidence supports the conclusion.**
