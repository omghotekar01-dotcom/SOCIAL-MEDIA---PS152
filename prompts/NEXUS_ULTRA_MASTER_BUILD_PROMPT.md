# NEXUS — Narrative & Influence Intelligence
## Ultra Master Build Prompt for SIH26152 — Social Media Analytics

### 0. Mission
Build a production-minded, judge-ready, low-cost social media analytics platform named **NEXUS — Narrative & Influence Intelligence** for **Smart India Hackathon 2026, Problem Statement SIH26152 — Social Media Analytics**, issued by the **National Technical Research Organisation (NTRO)**.

NEXUS must not be another generic dashboard that merely counts likes, hashtags or positive/negative posts. Its purpose is to reconstruct **how a narrative begins, mutates, crosses platforms, accelerates, polarizes communities and spreads through influential or bridge nodes over time**, while clearly expressing confidence, evidence coverage and uncertainty.

Primary product statement:

> **Track ideas, not just hashtags. Reconstruct origin, mutation, amplification, audience reaction, influence paths and emerging risk across social platforms.**

### 1. Official SIH requirements that MUST be satisfied
The implementation must explicitly map to all five official components of SIH26152.

#### A. Continuous Data Collection & Timeline Management
Build a multi-platform ingestion pipeline for live or near-live public content, user interactions and comments with a structured time-stamped historical database.

Platform priority:
- **Essentials / must-have:** X (formerly Twitter) and Telegram.
- **Desirable:** Instagram and Facebook.
- **Appreciable additions:** Reddit and/or YouTube comments.

NEXUS must normalize all sources into a common `SocialEvent` schema and support chronological replay.

#### B. Multi-Dimensional Sentiment Inference
Use NLP to infer more than positive/negative. At minimum support:
- positive / neutral / negative,
- anxiety / fear,
- anger,
- excitement,
- supportive / against / uncertain stance,
- sarcasm confidence when feasible,
- language detection,
- per-result model confidence.

The dashboard must show sentiment and stance changing along a timeline, not only aggregate pie charts.

#### C. Automated Demographic Profiling
Produce **aggregate, anonymized** audience estimates from public/self-declared profile indicators only. Potential aggregate dimensions:
- language,
- broad geography where explicitly available or reasonably inferred with confidence,
- professional-interest categories,
- broad age bracket only when a defensible public indicator exists.

Never present an individual user's sensitive trait as fact. Do not infer religion, caste, health condition, sexual orientation, political affiliation or other highly sensitive personal attributes. Every inferred aggregate must expose confidence and coverage.

#### D. Real-Time Trend & Topic Detection
Automatically identify and rank:
- emerging narratives,
- rising keywords/entities,
- burst velocity,
- acceleration,
- change points,
- topic migration across platforms,
- narrative mutation.

Support early-warning rules such as unusual velocity increase, rapid cross-platform migration or sharp sentiment/stance shift.

#### E. Link Analysis & Network Topology
Build relationship graphs that reveal:
- communities,
- high-influence nodes,
- bridge nodes connecting communities,
- repost/reply/mention edges,
- narrative propagation paths,
- community-to-community spread over time.

### 2. NEXUS differentiators / innovations
The implementation must include the following project-specific innovations because they are the core competitive advantage.

#### 2.1 Narrative Fingerprint
Create a semantic representation of each post/message using multilingual embeddings. Cluster semantically similar content even when hashtags and exact wording differ.

#### 2.2 Narrative Lineage Graph
Represent a narrative as a time-aware graph of related messages across platforms. Store:
- earliest detected source,
- later semantic matches,
- meaningful mutations,
- cross-platform hops,
- influencing/bridge accounts,
- associated communities,
- sentiment/stance shifts,
- velocity over time.

#### 2.3 Evidence & Coverage Ledger
Every analytical conclusion must carry evidence metadata:
- data sources included,
- time window,
- number of posts/messages observed,
- platforms missing/unavailable,
- model confidence,
- retrieval freshness,
- known limitations.

This prevents the system from pretending partial social-media visibility is complete visibility.

#### 2.4 Confidence-Aware Credibility Context
NEXUS is **not a truth oracle**. Do not output simplistic “TRUE/FALSE” labels for social-media claims unless an explicitly integrated authoritative fact-check source supports it.

Use evidence states such as:
- corroborated,
- uncorroborated,
- conflicting evidence,
- insufficient evidence.

Explain why the state was assigned and which evidence sources were used.

#### 2.5 Proactive Early Warning
Create explainable alerts such as:
- “Narrative velocity increased 3.2× in 20 minutes,”
- “Discussion crossed from Telegram Community A to X Community B,”
- “Negative/anxious sentiment rose sharply after mutation M2,”
- “Bridge node X connected two previously separate communities.”

### 3. Demo story to preserve
The default seeded demo should tell one continuous story.

Example:
1. A Telegram channel posts: “Metro services may remain closed tomorrow due to heavy rainfall.”
2. Replies question whether it is officially confirmed.
3. Related messages begin forwarding and discussing the claim.
4. NEXUS creates/updates a narrative fingerprint and lineage.
5. A semantically similar X post appears with changed wording.
6. Cross-platform semantic similarity is shown, e.g. high similarity rather than exact-hashtag matching.
7. A bridge node or community carries the narrative into another audience segment.
8. Narrative velocity increases and an early-warning alert appears.
9. Sentiment shifts toward anxiety/negative stance.
10. The analyst sees an evidence/coverage card, not a fake certainty label.

A stronger judge-facing example can additionally show:
- earliest detected event,
- Telegram → X migration,
- mutation point,
- bridge community,
- velocity delta,
- overall confidence.

### 4. Cost-first platform ingestion strategy
Prioritize official, legal and low-cost access. Do not build brittle credential-stealing, CAPTCHA bypass or login-bypass scrapers.

#### Telegram — MUST WORK
Use Telegram's official API/TDLib ecosystem through an open-source Python client such as Telethon for public channels/groups the operator is authorized to access. Telegram APIs are free of charge. Also support Bot API ingestion for chats where the bot is present.

Required connector features:
- recent messages,
- message timestamps,
- reply relationships,
- forwards where exposed,
- reactions/views where exposed,
- channel metadata,
- polling mode,
- replay from stored events.

#### X — MUST WORK, with honest cost handling
The official X API is pay-per-use for new developers in 2026, so the system must not falsely advertise free unlimited live X ingestion.

Implement **three X operating modes** behind the same adapter interface:
1. `official_api`: official X API v2 when credentials/credits are available.
2. `url_import`: free operator-driven ingestion of specific public X post URLs using legally accessible public metadata/oEmbed where available, suitable for demonstrations and analyst-selected evidence.
3. `dataset_replay`: import user-provided/exported JSON/CSV datasets and replay them through the exact same analytics pipeline.

The UI must display source mode (`LIVE`, `LIMITED LIVE`, `REPLAY`) so judges understand the engineering constraint rather than seeing fake live data.

The architecture must make switching to full official X ingestion a configuration change, not a rewrite.

#### YouTube — SHOULD WORK
Use YouTube Data API v3 with API key and default quota. Collect search results, video metadata and comment threads. Cache aggressively to stay within free quota.

#### Instagram — SHOULD WORK WHEN AUTHORIZED
Use Meta's official Instagram API for professional accounts / approved scopes. Support own/authorized professional-account media, comments, mentions, insights, and hashtag discovery where permitted by the selected login model and app permissions.

Do not claim arbitrary consumer-account scraping as official API support.

#### Facebook — OPTIONAL/DESIRABLE WHEN AUTHORIZED
Use Meta Graph API only for pages/data available under granted permissions and app review. Provide connector capability detection and a clear unavailable state when access is not granted.

#### Reddit — OPTIONAL
Use OAuth-based Reddit Data API only when the operator's use is eligible and approved. Respect deletion obligations, rate limits and current platform policy. Keep it as an adapter that can be disabled.

### 5. Architecture
Use a practical monorepo that is easy to run during an internal hackathon.

Preferred architecture:

#### Frontend
- React
- TypeScript
- Vite
- responsive analyst dashboard
- charting with Recharts or ECharts
- graph visualization with Cytoscape.js or Sigma.js

#### Core Backend
Use **Python FastAPI as the single runnable backend for the internal-hackathon MVP** to reduce operational complexity and make the system fully runnable quickly.

Keep service boundaries clean enough that a future Java Spring Boot gateway can be introduced if required, but do not force multiple runtimes for the first complete MVP.

Backend modules:
- ingestion adapters,
- normalization,
- analysis pipeline,
- narratives,
- trends,
- graph analysis,
- demographics aggregation,
- alerts,
- credibility/evidence layer,
- export/report endpoints.

#### Storage
Default no-cost developer mode:
- SQLite for immediate zero-config operation.

Production-ready optional profile:
- PostgreSQL for relational/time data,
- Neo4j optional for large relationship graphs,
- Redis optional for caching,
- Kafka optional for high-throughput streaming.

The application MUST run without PostgreSQL/Neo4j/Kafka/Redis so the demo is not blocked by infrastructure setup.

#### AI/NLP
Prefer free/open-source models and deterministic fallbacks:
- sentence-transformers multilingual embeddings when available,
- Hugging Face models for sentiment/emotion when locally available,
- scikit-learn / TF-IDF fallback,
- language detection,
- semantic clustering,
- NetworkX for graph analytics,
- lightweight trend/burst statistics.

All model components need a graceful deterministic fallback so the demo works even without downloading a large model.

### 6. Canonical SocialEvent schema
Every connector must normalize data into a common structure similar to:

```json
{
  "event_id": "platform:native_id",
  "platform": "telegram|x|youtube|instagram|facebook|reddit|demo",
  "native_id": "...",
  "event_type": "post|comment|reply|repost|forward",
  "author_id": "platform-scoped-public-id",
  "author_display": "public display name or pseudonymized value",
  "text": "...",
  "created_at": "ISO-8601",
  "collected_at": "ISO-8601",
  "conversation_id": "...",
  "reply_to_event_id": "...",
  "repost_of_event_id": "...",
  "url": "...",
  "language": "...",
  "public_profile": {},
  "metrics": {},
  "raw": {},
  "source_mode": "live|limited_live|replay|seeded_demo"
}
```

### 7. Analytics pipeline
For each normalized event:
1. clean and normalize text,
2. detect language,
3. extract hashtags, URLs, mentions, entities and keywords,
4. infer sentiment/emotion/stance + confidence,
5. compute semantic embedding/fingerprint,
6. assign/update narrative cluster,
7. update narrative lineage edges,
8. update trend counters/velocity,
9. update interaction graph,
10. recalculate influence/bridge/community metrics incrementally,
11. update aggregate audience profile,
12. evaluate alert rules,
13. update evidence/coverage ledger.

### 8. Graph analytics
Use NetworkX in MVP.

Required metrics:
- degree centrality,
- PageRank,
- betweenness centrality,
- community detection,
- bridge-node ranking,
- narrative-specific propagation subgraph.

Never equate high influence with malicious intent. Label the metric precisely as structural influence within the observed dataset/window.

### 9. Trend engine
Implement transparent, explainable heuristics first.

For each narrative/topic maintain time buckets and compute:
- current mentions,
- previous-window mentions,
- velocity,
- acceleration,
- z-score or burst score,
- platform diversity,
- community diversity,
- sentiment shift,
- stance shift.

Create alerts only when thresholds are exceeded and include the reason.

### 10. Aggregate demographics
Build only privacy-preserving aggregate estimates.

Potential signals:
- explicit profile language,
- detected language distribution,
- explicitly declared location or broad geocoded region,
- professional keywords in public bio,
- topic-interest clusters.

Required UI fields:
- estimate,
- confidence,
- sample size,
- coverage percentage,
- “unknown” percentage.

### 11. Dashboard — six priority screens
1. **Command Center** — live counters, platform health, active narratives, alerts, global sentiment/stance.
2. **Narrative Explorer** — narrative cards, semantic cluster members, timeline, mutations and evidence.
3. **Lineage Graph** — cross-platform narrative path and key propagation points.
4. **Influence Network** — communities, high-influence nodes, bridge nodes, structural metrics.
5. **Audience Intelligence** — anonymized aggregate language/geography/interests + confidence/coverage.
6. **Evidence & Reports** — source coverage, confidence, data freshness, exports, analyst-ready summary.

Also include a mode switch/status indicator for:
- LIVE,
- RECORDED REPLAY,
- OFFLINE DATASET.

### 12. API endpoints
At minimum implement:
- `GET /health`
- `GET /api/platforms/status`
- `POST /api/ingest/demo`
- `POST /api/ingest/telegram/poll`
- `POST /api/ingest/x/search` when official credentials exist
- `POST /api/ingest/x/url`
- `POST /api/ingest/youtube/search`
- `POST /api/import/events`
- `GET /api/events`
- `GET /api/narratives`
- `GET /api/narratives/{id}`
- `GET /api/narratives/{id}/timeline`
- `GET /api/narratives/{id}/graph`
- `GET /api/trends`
- `GET /api/network`
- `GET /api/demographics`
- `GET /api/alerts`
- `GET /api/evidence`
- `GET /api/dashboard/summary`
- `GET /api/export/events.csv`

### 13. Demo-mode reliability requirements
The project must be demonstrable even if external APIs fail at the venue.

Implement:
- deterministic seeded dataset,
- replay engine with adjustable speed,
- same processing functions used by live adapters and replay,
- visible source-mode badge,
- no fake claims that replay is live.

The seeded dataset should contain Telegram and X-like events sufficient to demonstrate all five official SIH components plus NEXUS innovations.

### 14. Setup and developer experience
Required repository items:
- root `README.md`,
- `.env.example`,
- `backend/`,
- `frontend/`,
- `prompts/`,
- `docs/`,
- `scripts/`,
- `tests/`,
- seed datasets,
- one-command Windows launcher where practical,
- setup guide requiring no paid infrastructure for demo mode.

### 15. Testing
Create automated tests for:
- SocialEvent normalization,
- narrative clustering,
- trend velocity/burst calculation,
- graph metrics,
- demographic aggregation privacy behavior,
- evidence coverage calculations,
- core API endpoints,
- seeded demo end-to-end flow.

### 16. Security & responsible analytics
- Analyze only data available to the operator under platform rules/permissions.
- Do not bypass authentication or rate limits.
- Avoid collecting private messages unless explicitly authorized and required.
- Minimize stored personally identifiable information.
- Hash or pseudonymize identifiers for analytics/export where feasible.
- Do not infer highly sensitive personal traits.
- Keep individual-level predictions out of demographic screens; show aggregates.
- Keep an audit trail of connector, collection time and source mode.
- Support deletion of imported events and source-specific retention policies.

### 17. Low-cost principle
Default budget target for internal SIH demo: **₹0 external infrastructure/API spend** where possible.

Use:
- local SQLite,
- open-source NLP,
- Telegram official API,
- YouTube free quota,
- authorized Meta APIs where available,
- X limited/operator-driven or replay mode when paid read credits are unavailable.

If the team later buys a small amount of X API credit, the official connector should immediately become live without changing analytics code.

### 18. Definition of done
NEXUS is considered internally complete when:
- application starts locally with clear instructions,
- seeded demo loads without external accounts,
- Telegram connector works with valid API credentials,
- X adapter works in official mode with credentials and in free URL/replay modes without them,
- YouTube connector works with an API key,
- Meta connectors report capability honestly and operate when authorized,
- all five official SIH components are visible in the UI,
- narrative lineage is demonstrated cross-platform,
- trend alert is generated from measurable velocity/change,
- network screen identifies communities and bridge/influence metrics,
- demographics are aggregate/confidence-aware,
- evidence ledger states source coverage and uncertainty,
- CSV export works,
- automated tests pass,
- README maps each feature to SIH26152 requirements,
- demo can be completed in under 3 minutes.

### 19. Judge-facing product language
Use precise claims:
- “We track ideas, not just hashtags.”
- “NEXUS reconstructs narrative lineage across time, platform and community.”
- “Influence is a structural graph metric inside the observed dataset, not an accusation.”
- “Demographics are aggregate, anonymized and confidence-aware.”
- “We show evidence coverage and uncertainty instead of pretending partial data is complete.”
- “Replay mode is a resilience feature for demonstration and historical analysis; it is clearly labeled.”

### 20. Build order
Execute in this order and commit after each stable milestone:
1. repository specification + master prompt,
2. backend skeleton + schemas + persistence,
3. seeded data + deterministic analytics,
4. dashboard APIs,
5. Telegram adapter,
6. X multi-mode adapter,
7. YouTube adapter,
8. Meta/Reddit adapter interfaces,
9. React dashboard,
10. tests + launch scripts,
11. docs + architecture + demo script,
12. final polish and acceptance checklist.

Do not stop after scaffolding. Each milestone must leave the repository in a runnable state and preserve compatibility with the previous milestone.
