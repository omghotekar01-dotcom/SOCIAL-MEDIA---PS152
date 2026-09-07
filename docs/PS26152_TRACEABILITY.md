# SIH26152 — Requirement Traceability Matrix

This is the judge/audit map for **NEXUS — Narrative & Influence Intelligence**. It connects the problem statement's four required analytical vectors to executable code, API endpoints, UI surfaces, evidence, and the demo sequence.

## 1. Sentiment Analysis

**What NEXUS implements**

- Event-level polarity (`positive`, `neutral`, `negative`).
- Sentiment score and method metadata.
- Stance (`for`, `against`, `unclear`) where supportable.
- Lightweight emotion/sarcasm signals as secondary indicators, never treated as ground truth.
- Temporal sentiment movement across the observed narrative timeline.

**Backend**

- `backend-ai/app/analytics.py`
  - event enrichment
  - sentiment/stance/emotion inference
  - timeline aggregation
  - alert sentiment-shift explanation

**API**

- `GET /api/timeline`
- `GET /api/events`
- `GET /api/narratives/{narrative_id}`
- `GET /api/alerts`

**UI**

- Timeline tab
- Narrative lineage cards
- Evidence ledger
- Alert explanation cards

**Jury proof**

Open **Timeline**, show positive/neutral/negative movement, then open a narrative/evidence item and show that the aggregate is backed by event-level inference.

---

## 2. Automated / Aggregate Demographic Profiling

**What NEXUS implements**

NEXUS intentionally implements privacy-safe, defensible audience profiling rather than guessing sensitive traits for named users:

- language distribution;
- broad geography only when publicly/self-declared;
- public professional-interest categories when the source supports them;
- age bracket only if a source explicitly/supportably supplies it; otherwise `unknown`;
- pseudonymous aggregation;
- k-anonymity-style suppression of small groups;
- coverage + confidence values.

**Backend**

- `backend-ai/app/analytics.py` → `demographics(...)`
- `backend-ai/app/db.py` → pseudonymous event persistence

**API**

- `GET /api/demographics`

**UI**

- Demographics tab

**Jury proof**

Show language / broad geography / professional-interest cards, the minimum group size, and the privacy note. Explain that small groups are suppressed and the project does not invent protected personal traits.

---

## 3. Real-Time Trend & Narrative Detection

**What NEXUS implements**

- semantic narrative clustering rather than exact hashtag-only counting;
- chronology and earliest-observed evidence;
- growth rate;
- burst deviation;
- unique-author diversity;
- cross-platform presence;
- engagement signal;
- recency;
- explainable trend status (`EMERGING`, `RISING`, `VIRAL`, `STABLE`, `DECLINING`);
- correction / mutation lineage through source events.

**Backend**

- `backend-ai/app/analytics.py`
  - clustering / narrative assignment
  - `trend_metrics(...)`
  - `narrative_summaries(...)`
  - timeline and alerts

**API**

- `GET /api/trends`
- `GET /api/narratives`
- `GET /api/narratives/{narrative_id}`
- `GET /api/alerts`

**UI**

- Overview priority narratives
- Trends tab
- Narrative lineage tab
- Alerts tab

**Jury proof**

Open **Trends**, choose the top narrative, show the score decomposition and lineage. State: **earliest observed means earliest inside our collected dataset, not absolute internet origin.**

---

## 4. Link Analysis & Network Topology

**What NEXUS implements**

Observed graph edges can arise from:

- replies;
- mentions;
- shared domains / URLs;
- time-bounded narrative co-amplification.

Graph outputs include:

- PageRank;
- betweenness centrality;
- degree centrality;
- communities/components;
- `High Reach Node` structural role;
- `Bridge Node` structural role.

These describe **observed graph position**, not guilt, intent, ideology, bot identity, or maliciousness.

**Backend**

- `backend-ai/app/analytics.py` → `build_network(...)`
- NetworkX graph algorithms

**API**

- `GET /api/network`
- `GET /api/network?narrative_id=...`
- network embedded in `GET /api/narratives/{id}`

**UI**

- Network tab
- Narrative network section

**Jury proof**

Show one High Reach Node and one Bridge Node, then explain what PageRank/betweenness mean in the observed dataset.

---

# Platform Acquisition Traceability

The four analytics vectors are independent of a single vendor API. All successful connectors normalize to `SocialEventIn` / `SocialEvent`.

| Source | Primary/official path | Free/public/fallback path | Backend | API |
|---|---|---|---|---|
| X | X API v2 recent search | configured permitted RSS/public bridge + JSON import/replay | `connectors.py`, `free_connectors.py` | `POST /api/connectors/x/search`, `POST /api/connectors/x/public` |
| Telegram | Bot API `getUpdates` with persistent in-process offset | zero-key public channel preview | `connectors.py`, `free_connectors.py` | `POST /api/connectors/telegram/poll`, `POST /api/connectors/telegram/public` |
| Instagram | Meta Graph authorized account sync + official hashtag discovery (`ig_hashtag_search → recent_media`) | best-effort genuinely public profile path + import/replay | `connectors.py`, `meta_discovery.py`, `free_connectors.py` | `POST /api/connectors/meta/sync`, `POST /api/connectors/instagram/hashtag`, `POST /api/connectors/instagram/public` |
| YouTube | YouTube Data API v3 video-first search + comments where available | zero-key `yt-dlp` public video metadata | `youtube_official.py`, `free_connectors.py` | `POST /api/connectors/youtube/search`, `POST /api/connectors/youtube/free` |
| Bluesky | public AT Protocol | same | `free_connectors.py` | `POST /api/connectors/bluesky/search` |
| Reddit | public JSON where allowed | OAuth/import fallback | `free_connectors.py` | `POST /api/connectors/reddit/search` |
| Mastodon | public instance API | alternate instance/import | `free_connectors.py` | `POST /api/connectors/mastodon/search` |
| Facebook | authorized Page Graph API | import/replay | `connectors.py` | `POST /api/connectors/meta/sync` |

## Source truthfulness

Every normalized event includes:

- `platform`
- `source_event_id`
- `created_at`
- `ingested_at`
- source URL where available
- `source_mode = LIVE | REPLAY | IMPORT`
- `connector_run_id`
- SHA-256 raw/provenance hash after normalization/persistence

A connector failure never silently becomes demo data.

---

# Evidence & Trust Layer

**Backend**

- `backend-ai/app/certificates.py`

**API**

- `GET /api/certificates`
- `GET /api/certificates/narrative/{id}`
- `GET /api/certificates/alert/{id}`

**What it proves**

- snapshot hash;
- witness hash;
- algorithm/configuration hash;
- witness posts;
- witness graph nodes/edges;
- coverage;
- replayable result;
- explicit `CERTIFIED` or `ABSTAIN`.

**Policy**

If minimum provenance/confidence requirements are not satisfied, the system abstains rather than presenting a high-impact narrative conclusion as verified.

---

# Demo Resilience Requirement

The deterministic seeded scenario is not a hidden substitute for live collection. It is an explicit **REPLAY** resilience layer.

- `POST /api/demo/seed`
- fictional RiverLink / TechFest / Monsoon scenario
- no third-party credentials required
- all source modes are visible in UI

Use one or two real live connectors to prove ingestion, then use deterministic data to reliably demonstrate all four analytics vectors even if venue internet or a commercial API is unavailable.

---

# Validation Traceability

**Backend tests**

- `test_core.py` — enrichment, deduplication, narratives, network, demographics
- `test_free_connectors.py` — Telegram public HTML + RSS bridge parsers
- `test_telegram_polling.py` — Bot API offset advancement
- `test_youtube_official.py` — video retained when comments are disabled
- `test_meta_discovery.py` — official Instagram hashtag two-step flow
- `test_certificates.py` — evidence certificate / replay hash
- `test_api_contracts.py` — health / connector API contracts

**Frontend**

- strict TypeScript build: `npm run build`

**Spring gateway**

- `mvn -B test package`
- gateway proxies legacy, free-source, Instagram hashtag, and certificate endpoints

**Preflight**

From repository root:

```bat
python scripts\preflight.py
```

The preflight checks required modules/docs, parses Python source/tests, validates frontend configuration and environment-variable coverage, and runs tests/builds when local dependencies are present.
