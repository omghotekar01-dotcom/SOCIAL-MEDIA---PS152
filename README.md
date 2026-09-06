# NEXUS — Narrative & Influence Intelligence

**Smart India Hackathon 2026 · SIH26152 · Social Media Analytics · NTRO**

> **We track ideas, not just hashtags.**

NEXUS is a cross-platform social-media intelligence prototype built for SIH26152. It collects timestamped public/authorized social content, normalizes it into one chronology, infers sentiment/stance/emotion, detects rising narratives, reconstructs their earliest observed evidence and semantic variants, maps amplification networks, and produces explainable alerts that always link back to evidence.

The system is intentionally honest about data coverage: every event is marked **LIVE**, **REPLAY**, or **IMPORT**. “Origin” always means **earliest observed in the configured/collected dataset**, never an unsupported claim about the absolute origin of a narrative on the internet.

---

## Why NEXUS is different

A normal dashboard asks:

- Which hashtag is trending?
- How many mentions exist?
- Is sentiment positive or negative?

NEXUS asks:

- What narrative is actually emerging even when wording changes?
- What is the exact observed chronology?
- How did stance/emotion change over time?
- Which accounts or communities amplified it?
- Which nodes bridge otherwise separate communities?
- How did the narrative migrate across platforms?
- What source evidence supports every alert?
- How complete is our collection coverage?

The product thesis is:

> **NEXUS turns disconnected social-media posts into an evidence-backed timeline of how a narrative emerges, spreads, changes sentiment, and moves through communities.**

---

## SIH26152 requirement coverage

| Official component | NEXUS implementation |
|---|---|
| Continuous Data Collection & Timeline Management | Official X connector, Telegram Bot API, YouTube Data API, authorized Meta connectors, replay/import layer, normalized timestamped `SocialEvent` store, optional continuous collector |
| Multi-Dimensional Sentiment Inference | polarity + stance + emotion + sarcasm estimate + confidence/method fields; timestamped sentiment timeline |
| Automated Demographic Profiling | aggregate anonymized language, broad public geography and professional-interest signals with k-anonymity suppression, coverage and confidence |
| Real-Time Trend & Topic Detection | time-bucket burst score using growth, deviation, author diversity, cross-platform presence, engagement and recency |
| Link Analysis & Network Topology | NetworkX graph; reply/mention/shared-domain/narrative edges; PageRank, betweenness, communities, bridge/high-reach explanations |

### Platform coverage

- **X — essential:** official X API v2 recent-search connector. Live access requires an X developer project/token and applicable API credits. NEXUS caps reads per run and never pretends replay data is live.
- **Telegram — essential:** live Telegram Bot API connector for a team-controlled/authorized group or channel; free and the preferred live jury source.
- **Instagram — desirable:** official Meta/Instagram professional-account connector when the app/account has the required permissions.
- **Facebook — desirable:** official Facebook Page connector when proper Page/app permissions are available.
- **YouTube — appreciative addition:** search + recent comment ingestion through YouTube Data API v3 when an API key is configured.
- **Replay/import:** deterministic resilience layer so the complete analytics pipeline remains demonstrable even when a third-party platform restricts access or quota.

---

## Architecture

```text
Official X API ────────┐
Telegram Bot API ──────┤
YouTube Data API ──────┤
Instagram / Meta ──────┤
Facebook / Meta ───────┤
CSV / JSON Replay ─────┘
          │
          ▼
   Connector Layer
          │
          ▼
   Normalized SocialEvent Store
          │
          ├── Sentiment / stance / emotion
          ├── Trend & burst engine
          ├── Narrative clustering / lineage
          ├── Network / influence engine
          ├── Aggregate demographic signals
          └── Explainable alert engine
          │
          ▼
  FastAPI Analytics API (:8000)
          │
          ├── direct demo mode
          │
          └── Spring Boot gateway (:8080)
                    │
                    ▼
          React + TypeScript Console (:5173)
```

### Hackathon-default runtime

The default demo is intentionally light and free:

- Python + FastAPI
- SQLite
- NetworkX
- scikit-learn TF-IDF/cosine narrative clustering
- VADER + transparent lexical fallbacks for sentiment/stance/emotion
- React + TypeScript + Vite
- optional Spring Boot gateway
- no Docker required

For a larger deployment, the architecture is designed to move structured/time data to PostgreSQL, graph workloads to Neo4j, and introduce Redis/Kafka only when scale requires them. Those systems are **not necessary to run the jury prototype**.

---

## Fastest way to run on Windows

### Prerequisites

- Python 3.11+
- Node.js 20+
- Internet connection for first dependency install
- Maven + Java 17 only if you want the optional Spring gateway

### One-click demo

```bat
scripts\start_demo.bat
```

The script:

1. creates `.env` from `.env.example` if missing;
2. creates a Python virtual environment;
3. installs FastAPI dependencies;
4. installs frontend dependencies;
5. starts FastAPI on `127.0.0.1:8000`;
6. loads the deterministic fictional demo dataset;
7. starts the React console on `127.0.0.1:5173`;
8. opens the browser.

Open manually if needed:

- Analyst console: `http://127.0.0.1:5173`
- FastAPI docs: `http://127.0.0.1:8000/docs`

### Full stack with Spring Boot

```bat
scripts\start_full.bat
```

This additionally starts the Spring gateway at `http://127.0.0.1:8080` and tells the frontend to route requests through it.

---

## Manual run

### 1. Environment

```bat
copy .env.example .env
```

Leave all API tokens blank if you only want the deterministic demo.

### 2. FastAPI

```bat
python -m venv .venv
.venv\Scripts\pip install -r backend-ai\requirements.txt
cd backend-ai
..\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend

In another terminal:

```bat
cd frontend
npm install
npm run dev
```

### 4. Seed demo

Use the UI **Seed Demo** button or POST:

```text
POST http://127.0.0.1:8000/api/demo/seed
{"reset": true}
```

---

## Live API setup

Copy `.env.example` to `.env` and fill only the connectors you can legally/officially use.

### Telegram — recommended zero-cost live demo

1. Create a bot using Telegram’s official BotFather.
2. Put its token in `TELEGRAM_BOT_TOKEN`.
3. Add the bot to a team-controlled/authorized demo group/channel.
4. If desired, set `TELEGRAM_ALLOWED_CHAT_IDS` to comma-separated allowed IDs.
5. Send a few messages in the group.
6. Click **Telegram** or start **Continuous** collection in NEXUS.

NEXUS uses the official Bot API `getUpdates` path. Duplicate updates are harmless because the event store deduplicates platform/source IDs.

### X — official connector with cost guardrails

Set:

```env
X_BEARER_TOKEN=...
X_MAX_RESULTS_PER_RUN=50
X_MAX_PAGES_PER_RUN=2
```

Then enter a query in the analyst bar and press **X Live**.

NEXUS does not scrape behind login or bypass X access controls. If the account has no credits/access, the connector returns an explicit `NO_CREDITS`, `PERMISSION_REQUIRED`, or credential state. For the jury, use the deterministic X-style **REPLAY** records if credits are not available.

### YouTube

Set:

```env
YOUTUBE_API_KEY=...
```

Enter the topic and press **YouTube**. The connector searches a small number of recent videos and ingests accessible top-level comments while respecting configured limits and quota.

### Instagram

Set the authorized Meta credentials:

```env
META_ACCESS_TOKEN=...
META_INSTAGRAM_ACCOUNT_ID=...
```

Press **Instagram** on the Overview page. This connector is intentionally scoped to authorized professional-account access and documented fields/permissions.

### Facebook

Set:

```env
META_ACCESS_TOKEN=...
META_FACEBOOK_PAGE_ID=...
```

Press **Facebook** on the Overview page. The connector is scoped to an authorized Facebook Page and applicable app/Page permissions.

---

## Continuous collection

The backend provides:

- `GET /api/collector/status`
- `POST /api/collector/start`
- `POST /api/collector/stop`

Example:

```json
{
  "query": "#ExampleTopic",
  "interval_seconds": 60,
  "enable_telegram": true,
  "enable_x": false,
  "enable_youtube": false
}
```

**Why X is off by default:** continuous X reads can consume paid API credits. **Why YouTube is off by default:** continuous searches consume quota. Telegram is the free-first live collection path.

---

## Normalized event contract

All connectors normalize to one `SocialEvent` model with:

- platform + original platform event ID
- event type
- public author identity where permitted + privacy-preserving pseudonymous ID
- original text
- language
- `created_at` and separate `ingested_at`
- source URL where possible
- parent/conversation relationships
- mentions / hashtags / URLs
- public engagement counters where available
- minimal public profile signals
- explicit `LIVE | REPLAY | IMPORT` source mode
- sentiment / emotion / stance / sarcasm estimate
- topic terms
- narrative cluster ID
- trend score
- method/confidence fields

Platform/source IDs are deduplicated before analytical use.

---

## Narrative engine

The current stable demo implementation uses:

- TF-IDF unigrams/bigrams
- cosine similarity
- time proximity
- shared hashtag bonus
- shared URL/domain bonus
- connected components for explainable narrative clusters

This deliberately avoids requiring a multi-gigabyte model download during a hackathon. A transformer profile can be added without changing the event/API contract.

**Origin language in the UI is strict:** “earliest observed in our collected dataset.”

---

## Trend engine

The transparent demo score combines:

```text
0.30 × normalized volume growth
0.20 × burst deviation
0.15 × unique-author diversity
0.15 × cross-platform presence
0.10 × engagement growth
0.10 × recency
```

Outputs include:

- `EMERGING`
- `RISING`
- `VIRAL`
- `STABLE`
- `DECLINING`

Every component is returned so the jury can see **why** a trend ranked highly.

---

## Network engine

Observed account nodes are linked by available evidence such as:

- replies
- mentions
- shared URL/domain
- time-bounded narrative co-amplification

NEXUS computes:

- weighted degree/degree centrality
- PageRank
- betweenness centrality
- connected communities/components

Labels:

- **High Reach Node** — high interaction centrality in the observed graph
- **Bridge Node** — high betweenness between observed communities

These are structural labels, **not accusations of intent or maliciousness**.

---

## Aggregate demographic signals

NEXUS never shows inferred demographic labels on individual user cards.

The endpoint returns group-level:

- language distribution
- broad geography only from explicit/public source fields when present
- professional-interest categories from configured public-profile signals
- age brackets only when a source explicitly/supportably supplies such a cue; otherwise unknown

Small groups are suppressed using `K_ANON_MIN_GROUP` (default 10). Each panel shows coverage and confidence, including unknown/suppressed buckets.

---

## Explainable alerts

An alert contains:

- narrative + severity
- trend score
- trigger reasons
- evidence event IDs
- earliest observed evidence
- top observed amplifiers
- platform mix
- sentiment shift
- confidence
- explicit coverage warning

The analyst can click from the alert directly into the chronological evidence trail.

---

## Deterministic jury dataset

`POST /api/demo/seed` generates a fictional dataset containing:

- a `#RiverLinkUpdate` narrative that starts quietly and accelerates;
- wording mutation across Telegram/X-style replay/YouTube-style comments;
- negative/anxious sentiment growth;
- shared-domain and mention links;
- a correction/counter-narrative;
- a stable TechFest background topic;
- a declining monsoon background topic.

No real person is accused of anything. Synthetic X-style events are marked `REPLAY`.

---

## 2–3 minute jury demo

1. Start with connector status: **Telegram ready/live; X official connector available but replay may be used if credits are absent.**
2. Press **Seed Demo**.
3. Open **Timeline** and show the conversation burst + sentiment movement.
4. Open the top **Trend** and say: “NEXUS is clustering the idea, not only matching the hashtag.”
5. Open **Narrative** and show earliest observed evidence + variants across platforms.
6. Open **Network** and show a High Reach / Bridge node with explanation.
7. Open **Alerts** and show exactly why the alert fired.
8. Open **Evidence** and point to LIVE/REPLAY/IMPORT labels.
9. If Telegram is configured, send a fresh team message and poll/start continuous collection to prove live ingestion.

Finish with:

> “The judge can move from a summary claim back to the exact observed evidence, while seeing what is live, replayed, imported, uncertain or unavailable.”

---

## Tests

Python unit tests:

```bat
cd backend-ai
..\.venv\Scripts\python -m pytest -q
```

API smoke test (backend must already be running):

```bat
python scripts\smoke_test.py
```

Frontend production build:

```bat
cd frontend
npm run build
```

Spring build:

```bat
cd backend-java
mvn test package
```

A GitHub Actions workflow is included at `.github/workflows/ci.yml` for automated validation when Actions are enabled for the repository.

---

## Project structure

```text
SOCIAL-MEDIA---PS152/
├─ prompts/
│  ├─ MASTER_SUPER_ULTRA_BUILD_PROMPT.md
│  └─ README.md
├─ backend-ai/
│  ├─ app/
│  │  ├─ analytics.py
│  │  ├─ collector.py
│  │  ├─ config.py
│  │  ├─ connectors.py
│  │  ├─ db.py
│  │  ├─ main.py
│  │  └─ schemas.py
│  ├─ tests/
│  └─ requirements.txt
├─ backend-java/
│  ├─ pom.xml
│  └─ src/main/...
├─ frontend/
│  ├─ src/
│  │  ├─ api.ts
│  │  ├─ App.tsx
│  │  ├─ main.tsx
│  │  └─ styles.css
│  └─ package.json
├─ scripts/
│  ├─ start_demo.bat
│  ├─ start_full.bat
│  └─ smoke_test.py
├─ docs/
├─ .env.example
├─ .gitignore
└─ README.md
```

---

## Hard limitations we intentionally disclose

- X live access depends on the official X API account/credits available to the team. NEXUS does not bypass this.
- Telegram Bot API sees only messages the configured bot is allowed to receive; it is not a universal Telegram archive.
- Instagram/Facebook coverage is bounded by Meta app/account permissions and review/access rules.
- YouTube coverage is bounded by search/comment availability and API quota.
- “Earliest observed” is bounded by configured platform/query/window coverage.
- Sentiment, sarcasm, stance and demographic signals are probabilistic and must never be treated as ground truth.
- Graph centrality indicates observed network position, not intent, guilt or truthfulness.

These limitations are part of the evidence model rather than hidden from the analyst.

---

## Security & privacy

- secrets only in `.env`
- `.env` is ignored by Git
- no hard-coded tokens
- pseudonymous analytical IDs
- aggregate demographics only
- small-group suppression
- public/authorized data only
- no de-anonymization
- no access-control bypass
- no sensitive-trait individual inference
- source-mode + confidence/coverage disclosures

See `docs/PRIVACY_AND_ETHICS.md` for the complete guardrail model.

---

## Team message

NEXUS is not designed to “judge” social-media users. It is designed to help an authorized analyst understand **observed public/authorized information flow** with chronology, uncertainty, network context and evidence.
