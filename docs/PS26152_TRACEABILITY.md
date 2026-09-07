# SIH26152 — Original Problem Statement Traceability

**Project:** NEXUS — Narrative & Influence Intelligence  
**Organization:** National Technical Research Organisation (NTRO)  
**Problem Statement:** SIH26152 — Social Media Analytics

This document maps the implementation directly to the **five core components in the original expected solution**, rather than reducing the requirement to only four analytical vectors.

---

## A. Continuous Data Collection & Timeline Management

### Original requirement represented in NEXUS

The system must support multi-platform ingestion of live posts, user interactions and comments, and preserve a structured time-stamped historical database so conversation chronology can be reconstructed.

Platform priority is displayed explicitly in the UI:

- **ESSENTIAL:** X (formerly Twitter), Telegram
- **DESIRABLE:** Instagram, Facebook
- **APPRECIABLE:** Reddit, YouTube

### Implementation

- Normalized event schema with root-post, comment/reply, parent and conversation identifiers.
- SQLite historical event store with source timestamp and ingestion timestamp.
- `LIVE / IMPORT / REPLAY` provenance preserved at event level.
- Continuous collector / Live Watch.
- Telegram Bot API + public monitored channel path.
- X official API when configured; explicit public Post URL/oEmbed path and analyst import fallback when commercial API access is unavailable.
- Instagram/Facebook authorized Meta paths.
- Reddit, YouTube, Bluesky and Mastodon supplemental paths.
- YouTube exact-video collection is fast-first for UX, then continues provider-bounded exhaustive public comment/reply collection in the background.

### Backend

- `backend-ai/app/db.py`
- `backend-ai/app/advanced_collector.py`
- `backend-ai/app/telegram_rich.py`
- `backend-ai/app/youtube_staged.py`
- `backend-ai/app/youtube_official.py`
- `backend-ai/app/connectors.py`
- `backend-ai/app/free_connectors.py`
- `backend-ai/app/resilient_connectors.py`

### API

- `POST /api/search/workspace`
- `POST /api/collector/start`
- `POST /api/collector/stop`
- source-specific connector endpoints
- `GET /api/events`
- `GET /api/timeline`

### UI proof

Open **PS26152 CORE** → Section **A**.

It shows:

- historical event count;
- root posts vs comments/replies;
- chronology span;
- Live Watch status;
- per-platform tier (`ESSENTIAL / DESIRABLE / APPRECIABLE`);
- connector state;
- current observed evidence.

Then open **Timeline** to inspect source-timestamped chronology.

---

## B. Multi-Dimensional Sentiment Inference

### Original requirement represented in NEXUS

The system must go beyond positive/negative polarity and detect nuanced reactions such as sarcasm, anxiety, excitement, supportive/against positions, and show how those signals fluctuate along the established timeline.

### Implementation

NEXUS keeps **root-content inference separate from audience-reaction inference**.

Signals include:

- positive / neutral / negative polarity;
- anxiety;
- anger;
- excitement;
- sadness;
- joy;
- disgust;
- surprise;
- trust;
- supportive / against / unclear stance;
- sarcasm probability.

### Backend

- `backend-ai/app/advanced_analytics.py`
- `backend-ai/app/reaction_engine.py`
- `backend-ai/app/ps26152_timeline.py`
- `backend-ai/app/complete_overview.py`

### UI proof

- **Posts / Explorer** → Public Reaction Intelligence for a selected root post/video.
- **Timeline** → polarity movement chart **and** Emotion / Stance / Sarcasm fluctuation chart.
- **PS26152 CORE** → Section **B** for aggregate audience sentiment, eight emotion dimensions, stance, sarcasm and time-window movement.

No root post is treated as proof of public opinion when no audience reactions are captured.

---

## C. Automated Demographic Profiling

### Original requirement represented in NEXUS

Aggregate, anonymized audience demographics should include age brackets, geography, language and professional interests, using supportable public profile indicators, bio text and behavioral patterns.

### Implementation

- pseudonymous user aggregation;
- language from observed text/profile signals;
- broad geography from public/self-declared location only;
- professional interests from public profile/bio first, with broad non-sensitive observed topic behavior as fallback;
- age brackets only from explicit self-declared public indicators;
- k-anonymity-style suppression for small groups;
- coverage and confidence values;
- no protected-trait guessing from names/photos.

### Backend

- `backend-ai/app/ps26152_demographics.py`
- `backend-ai/app/db.py`

### API

- `GET /api/demographics`

### UI proof

- **Demographics** tab;
- **PS26152 CORE** → Section **C**.

The UI must show unknown/low-coverage states honestly instead of fabricating demographic information that the platform does not expose.

---

## D. Real-Time Trend & Topic Detection

### Original requirement represented in NEXUS

Automatically identify, rank and predict rising trends, viral keywords and shifting discussions as they emerge chronologically.

### Implementation

Narrative ranking combines:

- volume growth;
- burst deviation;
- author diversity;
- cross-platform presence;
- engagement;
- recency.

Forecast extension includes:

- trend velocity;
- momentum (`ACCELERATING / RISING / FLAT / DECLINING / FALLING_FAST`);
- predicted next 15-minute bucket volume;
- forecast confidence.

The requirement console also surfaces rising/shifting terms from the visible evidence window.

### Backend

- `backend-ai/app/advanced_analytics.py`
- `backend-ai/app/scalable_clusters.py`
- `backend-ai/app/complete_narratives.py`

### API

- `GET /api/trends`
- `GET /api/narratives`
- `GET /api/narratives/{id}`
- `GET /api/alerts`

### UI proof

- **Trends** → ranked narratives and trend decomposition;
- **Narrative** → earliest-observed chronology and variants;
- **PS26152 CORE** → Section **D** → top narrative, momentum, next-window forecast, rising/shifting terms.

**Trust wording:** earliest observed means earliest in the collected dataset, not absolute internet origin.

---

## E. Link Analysis & Network Topology

### Original requirement represented in NEXUS

Map follower/user relationships, identify nodes of high influence (key opinion leaders), and visualize how a trend or sentiment spreads from one user segment to another over time.

### Implementation

Graph relationships can include:

**Direct observed relationships**

- reply;
- mention;
- provider-observed public-follow relationship when available.

**Lower-confidence co-discussion relationships**

- shared domain;
- shared hashtag;
- shared topic;
- narrative co-amplification.

Network outputs include:

- PageRank;
- betweenness centrality;
- degree centrality;
- communities;
- `High Reach Node`;
- `Bridge Node`;
- direct-vs-co-discussion edge counts;
- relationship-type counts;
- key opinion-leader candidates;
- community first-observed time;
- per-community sentiment mix;
- cross-community flow weights;
- segment adoption chronology.

### Backend

- `backend-ai/app/stable_views.py`
- `backend-ai/app/ps26152_network.py`
- `backend-ai/app/ps26152_intelligence.py`

### API

- `GET /api/network`
- `GET /api/network?narrative_id=...`
- network embedded in narrative detail.

### UI proof

Open **Network**.

The top workbench shows the interactive node/edge graph and Node Inspector. The additional **How trend & sentiment spread between user segments** section shows:

- relationship evidence types;
- direct vs co-discussion counts;
- cross-community flows;
- community adoption chronology;
- community sentiment mix.

Open **PS26152 CORE** → Section **E** for the condensed audit view.

Structural roles do **not** imply guilt, maliciousness, identity or intent.

---

# Original Requirement Console

The frontend now includes a persistent **PS26152 CORE — 5/5 requirement view** button.

This opens one audit-friendly console where the jury can see all five original requirements in the same place:

1. Collection & timeline
2. Multi-dimensional sentiment
3. Demographics
4. Trends & prediction
5. Link analysis & spread

Each requirement shows both:

- **implemented capability**, and
- **current workspace evidence**.

This distinction prevents a configured-but-unavailable external provider from being presented as successful live data.

---

# Source Truthfulness

Every normalized event preserves:

- platform;
- source event ID;
- source timestamp;
- ingestion timestamp;
- source URL when available;
- parent / conversation relationship when available;
- `LIVE | IMPORT | REPLAY` mode;
- connector run ID;
- normalized provenance hash in persistence.

A provider failure never silently becomes demo data.

---

# Demo Strategy

For the strongest deterministic proof when venue connectivity/provider access is unreliable:

1. use at least one real Telegram or YouTube live source;
2. use **Demo** only as explicitly labelled `REPLAY` resilience evidence;
3. open **PS26152 CORE** and walk A → E;
4. open **Timeline** for emotion movement;
5. open **Network** for propagation / key-node analysis;
6. open **Evidence** to prove provenance.

---

# Validation

From repository root:

```bat
scripts\start_demo.bat
```

or:

```bat
.\.venv\Scripts\python.exe .\scripts\preflight.py
```

Do not describe a build as verified until the current branch head passes the local backend tests, TypeScript typecheck and production frontend build.
