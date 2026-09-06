# NEXUS — MASTER SUPER ULTRA BUILD PROMPT

> **Project:** Smart India Hackathon 2026 — SIH26152 — Social Media Analytics  
> **Organization:** National Technical Research Organisation (NTRO)  
> **Team:** doomsDay  
> **Working product name:** **NEXUS — Narrative & Influence Intelligence**  
> **Core pitch:** **We track ideas, not just hashtags.**

---

## 0. ROLE AND EXECUTION MODE

You are the principal engineer, AI/NLP engineer, data engineer, frontend engineer, backend engineer, graph-analytics engineer, QA engineer, security reviewer, demo architect, documentation writer, and SIH jury-preparation partner for NEXUS.

Your job is to transform this specification into a reliable, demo-ready, maintainable prototype that satisfies the actual SIH problem statement rather than merely producing a beautiful dashboard.

Work continuously and methodically. Do not stop after scaffolding. Every feature must connect to the end-to-end user journey. Prefer a small feature that really works over a large feature that is decorative or fake.

### Non-negotiable execution rules

1. **Do not fabricate live data.** If a source is replay/demo data, label it `REPLAY` or `DEMO` in the UI.
2. **Do not claim an integration is live unless the connector actually authenticated and returned data.**
3. **Do not use private, stolen, bypassed, or unauthorized social-media data.**
4. **Use only public or explicitly authorized data.**
5. **Do not perform de-anonymization.** Demographics must be aggregate, probabilistic, anonymized, and confidence-bounded.
6. **Never infer sensitive traits such as religion, caste, health status, political affiliation, sexuality, or other protected/sensitive categories about named individuals.**
7. **Respect platform API terms, rate limits, and data-retention requirements.**
8. **No Docker dependency for the default hackathon run path.** The project must launch on a normal Windows laptop with Python, Node.js, and optionally Java/Maven.
9. **Free-first design.** Prefer local/open-source models and free quotas. Any paid API must be optional and budget-controlled.
10. **Official X and Telegram connectors are mandatory in the codebase.** Telegram must have a genuinely free live demo path. X must use the official X API when credentials/credits are configured; because X currently uses pay-per-use access, the app must also provide a clearly labelled replay/import mode so the complete analytics pipeline remains demonstrable without pretending replay data is live X.
11. **Every alert must be explainable and traceable to source evidence.**
12. **The analyst must be able to move from overview → trend → narrative → source posts → propagation graph → evidence timeline.**
13. **Default privacy mode must operate on pseudonymous user IDs in stored analytical tables.** Raw platform IDs may be retained only where needed for source traceability and must not be used for identity enrichment.
14. **Security first:** secrets in `.env`, never hard-code tokens, provide `.env.example`, validate inputs, sanitize URLs, and use server-side API access.
15. **The application must fail gracefully when a platform token is missing or quota is exhausted.** It should show connector status and continue operating with other sources.

---

## 1. OFFICIAL PROBLEM STATEMENT — BUILD AGAINST THIS, NOT AGAINST ASSUMPTIONS

The official SIH26152 problem is **Social Media Analytics** for NTRO.

The solution must implement five core components:

### A. Continuous Data Collection & Timeline Management
Build a multi-platform ingestion pipeline that can pull live data, posts, interactions, and comments and store a structured timestamped history so the exact chronology of conversations can be reconstructed.

Platform priority:
- **Essential / Must-Have:** X (formerly Twitter), Telegram
- **Desirable:** Instagram, Facebook
- **Appreciable additions:** Reddit or YouTube, especially text/comments

### B. Multi-Dimensional Sentiment Inference
Use NLP to infer nuanced sentiment/emotion such as sarcasm, anxiety, excitement, supportive/against, and show how sentiment changes over time.

### C. Automated Demographic Profiling
Infer aggregate, anonymized demographics from public profile indicators, bio text, language, behavioral patterns, etc. Examples include age brackets, broad geographic distribution, language, and professional interests. All outputs must have confidence/coverage and must remain aggregate.

### D. Real-Time Trend & Topic Detection
Identify, rank, and predict rising trends, viral keywords, and shifting discussions as they emerge chronologically.

### E. Link Analysis & Network Topology
Map relationships among followers/users/interactions, identify influential nodes, and visualize how trends or sentiment spread between user segments over time.

---

## 2. PRODUCT THESIS

Most social-media dashboards answer:
- what hashtag is trending?
- how many posts mention it?
- is sentiment positive or negative?

NEXUS must answer deeper questions:

1. **What is being discussed?**
2. **How do people feel about it, and how does that feeling change over time?**
3. **Where did the narrative originate in our observed dataset?**
4. **Which accounts/communities amplified it?**
5. **How did wording, stance, and emotion mutate as it travelled?**
6. **Which communities acted as bridges?**
7. **How quickly is the narrative spreading?**
8. **Is it accelerating or fading?**
9. **What evidence supports every conclusion?**
10. **How complete is our platform coverage?**

The differentiator is **cross-platform narrative lineage + temporal propagation + explainable evidence**, not a generic social listening UI.

Core line for product decisions:

> **NEXUS tracks the life cycle of a narrative — emergence, mutation, amplification, migration, and decay — across platforms.**

---

## 3. END-TO-END DEMO STORY

The final prototype must support this exact jury demonstration:

1. Analyst enters a monitored topic/query, e.g. `#ExampleTopic` or a phrase.
2. Connector-status strip shows X, Telegram, YouTube, Instagram/Facebook, and replay/import status.
3. Live Telegram ingestion pulls messages from an authorized demo channel/group.
4. X ingestion runs through the official X API if a bearer token and credits are configured; otherwise a visible `REPLAY` source supplies a previously exported/publicly sourced dataset through the same normalization layer.
5. YouTube Data API optionally pulls recent matching videos/comments using free quota.
6. All events are normalized into one `SocialEvent` schema.
7. Dashboard updates topic volume and sentiment timeline.
8. Trend engine detects a burst and marks a narrative as `RISING`.
9. Narrative engine clusters semantically similar posts across platforms.
10. Evidence panel shows earliest observed posts and chronological propagation.
11. Graph view shows users/accounts as nodes and interactions/shared URLs/semantic narrative co-membership as edges.
12. Influence engine highlights high-centrality nodes and bridge nodes with explanations.
13. Sentiment engine shows supportive/against/neutral and emotion distribution over time, including uncertainty.
14. Demographics tab shows only aggregate anonymized language, broad geo where explicitly/publicly available, and professional-interest categories with coverage/confidence.
15. Analyst clicks an alert and sees: why it fired, first observed evidence, top spreaders, propagation path, sentiment shift, platform mix, confidence, and data-coverage warning.
16. Export button downloads JSON/CSV evidence for the selected narrative.

Target jury message:

> “We are not showing a dashboard with random charts. We are proving how a narrative emerged, who amplified it, how sentiment changed, and where the evidence came from.”

---

## 4. ARCHITECTURE

### 4.1 Monorepo layout

```text
/
├─ prompts/
├─ docs/
├─ data/
│  ├─ demo/
│  └─ imports/
├─ backend-ai/                 # Python + FastAPI analytics and connectors
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ config.py
│  │  ├─ db.py
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  ├─ api/
│  │  ├─ connectors/
│  │  ├─ analytics/
│  │  └─ services/
│  ├─ tests/
│  └─ requirements.txt
├─ backend-java/               # Spring Boot gateway / auth / analyst API
├─ frontend/                   # React + TypeScript + Vite
├─ scripts/
│  ├─ start_demo.bat
│  ├─ start_full.bat
│  ├─ seed_demo.py
│  └─ smoke_test.py
├─ .env.example
├─ .gitignore
└─ README.md
```

### 4.2 Logical flow

```text
X official API ─────┐
Telegram ───────────┤
YouTube ────────────┤
Instagram/Meta ─────┤
Facebook/Meta ──────┤ → Connector Layer → Normalizer → Event Store
CSV/JSON Replay ────┘                               │
                                                    ├→ NLP / stance / emotion
                                                    ├→ Trend / burst engine
                                                    ├→ Narrative clustering
                                                    ├→ Graph / influence engine
                                                    ├→ Aggregate demographics
                                                    └→ Evidence / alerts
                                                             │
                                              Spring Boot analyst API
                                                             │
                                                React analyst console
```

### 4.3 Default hackathon runtime

The system must support a **zero-paid, low-friction demo mode**:
- FastAPI on `localhost:8000`
- React Vite on `localhost:5173`
- SQLite local database by default
- NetworkX graph analytics by default
- local/rule-based NLP fallbacks if transformer models are not downloaded
- Telegram Bot API live connector
- YouTube Data API connector when API key is configured
- X official connector present and testable once bearer token/credits are configured
- replay/import connector always available for deterministic demo

### 4.4 Production-aligned optional runtime

Support adapters/configuration for:
- PostgreSQL for structured/time-series data
- PostGIS for any geo-based aggregation
- Neo4j for large graph workloads
- Redis for caching/queues
- Kafka only as an optional scaling layer; it must not be required for the demo
- Spring Boot as the application/API gateway and RBAC layer

---

## 5. NORMALIZED DATA MODEL

Every connector must convert platform-specific payloads into the same schema.

### `SocialEvent`

Required fields:
- `id`: internal UUID
- `platform`: `x | telegram | youtube | instagram | facebook | reddit | replay`
- `source_event_id`: original platform event/post/comment ID
- `event_type`: `post | message | comment | reply | repost | mention | video_comment | imported`
- `author_platform_id`: original author ID if accessible
- `author_pseudo_id`: deterministic privacy-preserving hash used for analytics
- `author_display`: public display handle/name if policy permits
- `text`: normalized textual content
- `language`: detected or source-provided language
- `created_at`: platform timestamp
- `ingested_at`: collection timestamp
- `url`: source permalink where possible
- `parent_event_id`: reply/comment parent if known
- `conversation_id`: thread/conversation identifier if known
- `mentions`: list of mentioned handles/IDs
- `hashtags`: normalized hashtags
- `urls`: extracted URLs/domains
- `engagement`: object with available public counters
- `public_profile`: minimal public profile indicators used only for aggregate analysis
- `source_mode`: `LIVE | REPLAY | IMPORT`
- `connector_run_id`
- `raw_hash`: hash for deduplication/audit

### Derived analytical fields
- `sentiment_label`
- `sentiment_score`
- `emotion_scores`
- `stance_label`
- `stance_confidence`
- `sarcasm_probability`
- `topic_terms`
- `embedding_id` or vector
- `narrative_cluster_id`
- `trend_score`
- `quality_score`

### Data-integrity principles
- raw payloads are not blindly exposed to frontend
- deduplicate by source ID and normalized hash
- preserve original timestamp
- separate `created_at` from `ingested_at`
- store platform and source mode explicitly
- every derived inference stores model/version/method/confidence

---

## 6. CONNECTOR STRATEGY — FREE FIRST, POLICY COMPLIANT

### 6.1 X — essential

Use the **official X API v2** connector.

Capabilities to implement:
- bearer-token auth
- recent search query
- request only necessary fields
- pagination with hard budget cap
- deduplication
- per-run post limit
- query allowlist/validation
- usage/cost guardrails
- exponential backoff on 429/5xx
- connector health response
- clear error when credits/access are unavailable

Important current reality:
- X API uses pay-per-use access.
- Do not promise a free unlimited X firehose.
- Do not scrape X in a way that violates platform terms.

Cost-control strategy:
- query only analyst-selected topics
- cache post IDs and never re-read the same post unnecessarily
- use small windows for jury demo
- cap results per run
- cache metadata
- expose a `X_MAX_RESULTS_PER_RUN` environment variable
- expose usage status in UI

Demo continuity:
- if no X credits/token are present, show X as `CREDENTIALS_REQUIRED` or `NO_CREDITS`
- enable `REPLAY` dataset generated from lawful exported/public demonstration data through the exact same normalization and analytics pipeline
- never label replay data as live X

### 6.2 Telegram — essential

Implement two safe modes:

**Mode A: Telegram Bot API — default live hackathon demo**
- free
- bot is added to a team-controlled or otherwise authorized group/channel
- collect `message`, `channel_post`, edited variants, replies, public text and timestamps received by bot
- webhook or long-polling; default to long-polling for simple laptop demo
- use bot token from environment

**Mode B: MTProto / client API — optional, disabled by default**
- only where platform terms and the intended analytical use permit it
- never use it to bypass access controls
- never access private groups/channels without authorization
- display policy warning in docs

Telegram data must not be used to train/fine-tune models. Use pre-trained inference components only where permitted by applicable platform terms and the project’s approved use case.

### 6.3 YouTube — appreciative addition, strong free demo source

Use YouTube Data API v3.

Implement:
- search videos by topic
- retrieve comments/comment threads
- normalize comments into `SocialEvent`
- respect daily quota
- cache video IDs and comment IDs
- show quota-aware connector status

### 6.4 Instagram — desirable

Use official Meta/Instagram APIs only.

Support professional-account / authorized-account flows and documented hashtag/media/comment capabilities where available to the configured app permissions.

Because unrestricted public Instagram consumer-account access is not provided, the UI must state scope/coverage clearly.

### 6.5 Facebook — desirable

Use Graph/Pages APIs only with proper app permissions and page access where available.

Provide:
- page/account authorized connector
- comments/posts where permitted
- clear `APP_REVIEW_REQUIRED` or `PERMISSION_REQUIRED` status instead of failing silently

### 6.6 Reddit — optional

Implement only if developer credentials and use terms permit the intended use.

Do not use Reddit user content to train/fine-tune AI models without proper rights. Keep connector optional.

### 6.7 CSV/JSON replay/import — mandatory resilience layer

Support import of normalized or platform-export-style datasets.

Purpose:
- deterministic jury demo
- reproduce alerts
- test pipeline without API dependency
- benchmark analytics

Required importer behavior:
- schema validation
- platform label required
- source mode forced to `REPLAY`/`IMPORT`
- safe rejection of malformed rows
- deduplication
- import report

---

## 7. ANALYTICS ENGINES

## 7.1 Text normalization

Pipeline:
1. Unicode normalize
2. preserve original text
3. extract URLs, hashtags, mentions
4. collapse repeated whitespace
5. strip tracking query params for URL-domain comparison
6. detect language
7. optional transliteration-aware helper for Hinglish/Marathi/Hindi mixed text
8. remove only noise required by model; do not destroy evidence text

## 7.2 Sentiment + emotion + stance

Output must be multi-dimensional rather than only positive/negative.

Minimum output:
- polarity: positive / neutral / negative
- stance: supportive / against / unclear
- emotions: anxiety/fear, anger, excitement/joy, sadness, neutral/other
- sarcasm probability or `unknown`
- confidence

Implementation hierarchy:
1. local open-source transformer where available
2. lightweight local model or VADER/TextBlob-style fallback for English
3. lexical/rule fallback when model unavailable

Do not block the whole app while downloading a large model. Lazy-load and cache.

Every response must contain `method` and `confidence`.

## 7.3 Trend/burst engine

For each token/topic/narrative cluster over time buckets, compute:
- current volume
- baseline moving average
- growth rate
- z-score or robust deviation
- acceleration
- cross-platform spread count
- unique-author count
- engagement-weighted signal

Example explainable score:

```text
trend_score =
  0.30 * normalized_volume_growth +
  0.20 * burst_zscore +
  0.15 * author_diversity +
  0.15 * cross_platform_presence +
  0.10 * engagement_growth +
  0.10 * recency
```

Labels:
- EMERGING
- RISING
- VIRAL
- STABLE
- DECLINING

Never present a score without components/explanation.

## 7.4 Narrative clustering / lineage

Goal: connect semantically related posts even when wording differs.

Use:
- sentence-transformer embeddings when available
- TF-IDF/cosine fallback
- time-aware clustering
- shared URL/domain/hashtag features
- lexical overlap

Cluster output:
- narrative ID
- representative phrase/title
- earliest observed event
- platform of earliest observed event **within our observed data**
- later variants
- sentiment progression
- top accounts by amplification
- cross-platform transitions

Important wording:
- say `earliest observed in our collected dataset`, not absolute internet origin unless proven.

## 7.5 Link/network analysis

Construct graph nodes:
- public/pseudonymous accounts
- optionally narratives or URLs as bipartite nodes

Edges:
- reply
- mention
- repost/share where available
- comment-to-author
- shared URL/domain
- same narrative amplification within a time window

Compute:
- degree centrality
- weighted degree
- PageRank
- betweenness centrality
- connected components
- community detection where practical

Explain labels:
- `High Reach Node`: high weighted degree/PageRank
- `Bridge Node`: high betweenness between communities
- `Early Amplifier`: posts early and receives downstream interactions

Do not equate high centrality with maliciousness.

## 7.6 Aggregate demographics

Only aggregate/anonymized outputs.

Allowed categories:
- language distribution
- broad geography only if explicitly/publicly stated or platform-supplied, never precise home-location inference
- professional-interest categories inferred from public bios/content with confidence
- broad age-bracket estimates only if ethically supportable from explicit public cues; otherwise report `insufficient evidence`

Minimum group threshold: suppress demographic slice if fewer than `K_ANON_MIN_GROUP` users (default 10).

Always show:
- coverage percentage
- confidence
- unknown/insufficient bucket
- method

Never show inferred demographic labels on an individual profile card.

---

## 8. EXPLAINABLE ALERT ENGINE

An alert is not just a notification.

Every alert object must contain:
- `alert_id`
- `title`
- `severity`
- `narrative_id`
- `triggered_at`
- `trend_score`
- `why_triggered[]`
- `evidence_event_ids[]`
- `earliest_observed_event_id`
- `top_amplifiers[]`
- `platform_mix`
- `sentiment_shift`
- `coverage_warning`
- `confidence`

Example:

```text
RISING NARRATIVE: “Example phrase”
Why:
- 4.8x volume growth in 15 minutes
- appeared on 3 platforms
- 71 unique authors
- negative/anxious sentiment rose from 18% to 46%
- one bridge node connected two previously separate communities
Evidence:
- first observed Telegram message at 14:03
- first observed X post at 14:07
- first observed YouTube comment cluster at 14:16
Confidence: 0.82
Coverage: X limited to configured query window; Telegram limited to authorized channels.
```

Target internal alert latency after ingestion: under 60 seconds for demo-size data.

---

## 9. BACKEND API CONTRACT

FastAPI must expose at least:

### Health / configuration
- `GET /health`
- `GET /api/connectors/status`

### Ingestion
- `POST /api/ingest/replay`
- `POST /api/connectors/x/search`
- `POST /api/connectors/telegram/poll`
- `POST /api/connectors/youtube/search`
- `POST /api/connectors/meta/sync`

### Analytics
- `GET /api/overview`
- `GET /api/timeline`
- `GET /api/trends`
- `GET /api/narratives`
- `GET /api/narratives/{id}`
- `GET /api/network`
- `GET /api/demographics`
- `GET /api/alerts`

### Evidence / export
- `GET /api/events`
- `GET /api/events/{id}`
- `GET /api/export/narrative/{id}.json`
- `GET /api/export/narrative/{id}.csv`

All responses should have stable JSON schemas.

---

## 10. SPRING BOOT RESPONSIBILITIES

Spring Boot is the application-facing backend/gateway.

Minimum responsibilities:
- `/api/gateway/health`
- proxy selected analytics calls to FastAPI
- CORS configuration for frontend
- analyst demo-session endpoint
- RBAC-ready structure (`ANALYST`, `ADMIN`)
- no hard-coded production passwords
- in demo mode, provide a simple clearly labelled demo analyst session rather than fake enterprise auth

The frontend may have a documented direct-FastAPI demo mode to reduce hackathon setup risk.

---

## 11. FRONTEND — ANALYST CONSOLE

Use React + TypeScript + Vite.

Design goal: modern intelligence workstation, not overdecorated sci-fi UI.

### Screens

#### 1. Overview
- active monitored query
- connector status cards
- total events
- active narratives
- rising trends
- sentiment snapshot
- data-coverage banner

#### 2. Timeline
- chronological event volume
- sentiment/emotion overlay
- platform filters
- click to inspect evidence

#### 3. Trends
- ranked narratives/topics
- status badge: Emerging/Rising/Viral/etc.
- growth and acceleration
- explainable score breakdown

#### 4. Narrative detail — HERO SCREEN
- narrative title
- earliest observed evidence
- propagation timeline
- wording/semantic variants
- sentiment shift
- top amplifiers
- platform transitions
- confidence + coverage
- source-event evidence list

#### 5. Network
- interactive SVG/canvas graph
- filters by platform / edge type
- highlight bridge nodes and high-reach nodes
- side panel explaining why a node is important

#### 6. Demographics
- aggregate only
- language
- broad geo where evidence exists
- professional-interest categories
- unknown/coverage
- privacy note

#### 7. Alerts
- chronological alert feed
- severity
- why triggered
- evidence count
- open narrative button

### UI requirements
- large readable text for projection
- fast load
- responsive at 1366×768 and 1920×1080
- no tiny labels
- accessible contrast
- tooltips for technical terms
- badges for `LIVE`, `REPLAY`, `IMPORT`
- no fake “live” pulsing indicator for replay data

---

## 12. DEMO DATASET

Create a deterministic demo dataset with at least 60–120 events spread across X-style replay, live/team Telegram, and YouTube-style comments.

The dataset must contain a believable narrative evolution:
- initial neutral information post
- early Telegram discussion
- wording mutation
- X-style amplification
- sentiment shift from neutral to anxiety/against
- two communities
- one bridge account connecting them
- one shared URL/domain
- later corrective/supportive counter-narrative

No real person should be falsely accused or portrayed as malicious. Use fictional handles/accounts for synthetic records.

Demo needs to produce:
- one obvious rising narrative
- one stable background topic
- one declining topic
- graph with visible clusters
- measurable sentiment shift
- at least one bridge node
- at least one explainable alert

---

## 13. TESTING

### Unit tests
- normalization
- deduplication
- X payload mapping
- Telegram payload mapping
- YouTube payload mapping
- trend score
- narrative similarity
- graph centrality
- demographic k-anonymity suppression

### API smoke tests
- health endpoint
- seed/import demo data
- overview non-empty
- trends non-empty
- network nodes/edges non-empty
- alerts non-empty

### Demo acceptance test
A fresh laptop should be able to:
1. clone repo
2. copy `.env.example` → `.env`
3. install Python requirements
4. run `scripts/start_demo.bat`
5. open frontend
6. import/seed demo dataset
7. show all five official analytics components even without paid X access
8. optionally connect live Telegram and YouTube
9. optionally switch X connector live by supplying official token/credits

---

## 14. FAILURE HANDLING

Each connector has states:
- `READY`
- `LIVE`
- `CREDENTIALS_REQUIRED`
- `PERMISSION_REQUIRED`
- `RATE_LIMITED`
- `NO_CREDITS`
- `DEGRADED`
- `DISABLED`
- `ERROR`

A connector failure must never crash the analytics system.

The UI should explain the exact condition in plain language.

---

## 15. COST BUDGET

Default target: **₹0 recurring cost for the core demo**, excluding internet/electricity.

- Telegram Bot API: free
- local NLP: free
- SQLite/NetworkX: free
- React/FastAPI/Spring Boot: free/open source
- YouTube Data API: default quota-based access
- X API: optional minimal pay-per-use only when true live X search is required
- Meta APIs: no per-call purchase for normal API access, but permissions/account/app-review constraints apply

Do not introduce paid LLMs if local inference can do the job.

---

## 16. SECURITY, PRIVACY, ETHICS

- `.env` secrets only
- never log full tokens
- pseudonymize account IDs for analytics
- retain source URLs for evidence where policy permits
- aggregate demographics only
- enforce minimum cohort threshold
- show confidence and unknowns
- no private-channel bypass
- no credential stuffing
- no scraping behind login/access controls
- no automated harassment, targeting, or action against users
- no attribution of criminality or intent from graph centrality alone
- no sensitive-trait inference
- include `docs/PRIVACY_AND_ETHICS.md`

---

## 17. DOCUMENTATION DELIVERABLES

Create:
- root `README.md`
- `docs/ARCHITECTURE.md`
- `docs/API_ACCESS_STRATEGY.md`
- `docs/DEMO_RUNBOOK.md`
- `docs/PRIVACY_AND_ETHICS.md`
- `docs/JURY_QA.md`
- `docs/TEST_PLAN.md`

README must include:
- what problem NEXUS solves
- official five-component coverage matrix
- architecture
- quick start
- live connector setup
- limitations
- demo flow
- project structure

---

## 18. SIH JURY DEFENCE

### “Isn’t this just another sentiment dashboard?”
Answer:
> “No. Sentiment is one layer. NEXUS reconstructs narrative chronology, links semantically related posts across platforms, maps amplification paths, identifies bridge communities, and attaches source evidence to every alert.”

### “How do you know where a narrative started?”
Answer:
> “We say earliest observed origin within our collected dataset, not absolute internet origin. The timeline is evidence-backed and coverage-bounded.”

### “How is X free?”
Answer:
> “It isn’t unlimited/free under the current official API model. We use the official connector with strict cost caps when enabled and a clearly labelled replay/import path for deterministic prototype evaluation. We do not fake live X data.”

### “Why Telegram?”
Answer:
> “Telegram is a must-have platform in the problem statement. Our live hackathon path uses an authorized bot/channel flow so the integration is genuinely working without bypassing access controls.”

### “Are demographics ethical?”
Answer:
> “We never profile named individuals. We produce only aggregate anonymized distributions with minimum group thresholds, coverage, unknown buckets and confidence.”

### “How is influence calculated?”
Answer:
> “Using graph measures such as PageRank, weighted degree and betweenness on observed interaction edges. We explain why a node ranks highly; we do not interpret centrality as guilt or malicious intent.”

### “What is your novelty?”
Answer:
> “Evidence-aware cross-platform narrative lineage: detecting a burst, showing the earliest observed evidence, tracking semantic mutation and sentiment shift, finding the communities and bridge nodes that amplified it, and preserving confidence and coverage limits.”

---

## 19. BUILD ORDER — DO NOT SKIP

### Phase 1 — Foundation
1. Repo docs and environment template
2. FastAPI health endpoint
3. SQLite models
4. normalized SocialEvent ingestion
5. deterministic demo dataset

### Phase 2 — Required analytics
6. sentiment/emotion/stance service with fallback
7. trend/burst scoring
8. narrative clustering
9. NetworkX graph and centrality
10. aggregate demographics with k-anonymity
11. alert/evidence engine

### Phase 3 — Connectors
12. Telegram live Bot API
13. X official API v2 connector with cost caps
14. YouTube Data API connector
15. Meta Instagram/Facebook authorized connectors
16. replay/import connector

### Phase 4 — Analyst UI
17. overview
18. timeline
19. trends
20. narrative detail
21. network graph
22. demographics
23. alerts

### Phase 5 — Java gateway
24. Spring Boot app
25. health/proxy endpoints
26. demo auth/RBAC-ready structure

### Phase 6 — Reliability
27. start scripts
28. smoke tests
29. graceful connector failures
30. docs
31. final demo runbook

---

## 20. DEFINITION OF DONE

NEXUS is considered demo-complete only if all of the following are true:

- [ ] X connector exists, authenticates against official API when configured, and handles no-credit/missing-token state honestly.
- [ ] Telegram connector can ingest real authorized live messages for the demo.
- [ ] YouTube comments can be ingested when an API key is supplied.
- [ ] Instagram/Facebook connector scaffolding uses official Meta endpoints/permissions and reports permission limitations clearly.
- [ ] Replay/import path works without external API dependencies.
- [ ] Unified SocialEvent schema is used across every source.
- [ ] Sentiment is multidimensional and timestamped.
- [ ] Demographics are aggregate/anonymized and confidence-aware.
- [ ] Trend detection identifies a rising topic from seeded data.
- [ ] Narrative lineage shows earliest observed evidence and variants.
- [ ] Network graph identifies high-reach and bridge nodes.
- [ ] Every alert links to evidence.
- [ ] Frontend clearly differentiates live/replay/import sources.
- [ ] Missing credentials never crash the system.
- [ ] Project runs without Docker.
- [ ] A Windows start script exists.
- [ ] README setup works from a clean clone.
- [ ] Demo can be completed in under 3 minutes.

---

## 21. FINAL PRODUCT MESSAGE

Every engineering decision should reinforce this sentence:

> **NEXUS turns disconnected social-media posts into an evidence-backed timeline of how a narrative emerges, spreads, changes sentiment, and moves through communities.**

And every SIH demonstration should prove these five official requirements visibly:

1. **Continuous/timestamped collection**
2. **Nuanced sentiment/emotion**
3. **Aggregate anonymized demographics**
4. **Real-time trend detection**
5. **Link/network analysis**

The prototype must be trustworthy enough that a judge can click from any summary claim back to the underlying evidence and can see exactly which data is live, imported, replayed, uncertain, or unavailable.
