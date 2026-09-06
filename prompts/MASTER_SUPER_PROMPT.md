# PS 26152 — Social Media Analytics
## Ultra Master Build Prompt

You are the principal engineer, applied AI researcher, data-platform architect, security engineer, product designer, SRE, QA lead and SIH jury-preparation specialist responsible for taking this repository from zero to a production-shaped Smart India Hackathon prototype for NTRO Problem Statement 26152: **Social Media Analytics**.

### 1. Mission
Build a privacy-aware, evidence-first, AI-driven social-media intelligence framework that turns public social-media data into four mandatory analytic vectors:
1. **Sentiment Analysis** — quantify positive/neutral/negative sentiment, polarization and sentiment drift.
2. **Audience/Demographic Mapping** — infer only privacy-safe and defensible aggregate attributes from public/self-declared signals: language, self-declared location, account/category type, activity window and community membership. Do not guess protected personal attributes.
3. **Trend & Narrative Tracking** — detect emerging keywords, hashtags, topics and narratives; rank burst velocity; cluster related discussions; show chronology and cross-platform convergence.
4. **Link/Network Analysis** — build interaction graphs from mentions, replies, repost/re-share references, shared URLs/hashtags and co-occurrence; rank influence; identify communities; trace information flow.

The framework must be useful to an analyst rather than merely showing charts. Every important analytic output should answer: **what happened, where, when, who/which segment amplified it, how confident are we, and what evidence supports the conclusion?**

### 2. Hard Requirements
- Primary public-source connectors: **X/Twitter, Telegram, Instagram, YouTube**.
- Additional low-cost/free connectors where practical: Reddit, Bluesky, Mastodon and import-from-JSON/CSV.
- Prefer free/open-source/no-key access methods. Where a platform requires official credentials, support the official free quota if available and a clearly labelled public-web or import fallback.
- The application must never fabricate live access. Connector health must report `live`, `degraded`, `credential_required`, `rate_limited` or `offline`.
- Include a deterministic **demo dataset** so the full product can be demonstrated without internet, credentials or paid APIs.
- Backend must expose stable REST endpoints and keep connector-specific logic behind adapters.
- Frontend must present an analyst console with overview, feed/evidence, trends, sentiment, network graph, audience map and source-health views.
- Every AI-derived result should include confidence/quality metadata and be traceable to source records.
- Do not store secrets in Git. Provide `.env.example` only.
- Respect platform terms, public-data boundaries, rate limits, privacy and applicable law. No credential theft, auth bypass, private-account access or stealth evasion.

### 3. Cost Constraint
Optimize for a student SIH team:
- Default local deployment cost: **₹0**.
- Use SQLite by default; allow PostgreSQL later.
- Use local Python analytics (scikit-learn, NetworkX, VADER/rule-based NLP) before paid LLMs.
- Use optional API keys only when they materially improve live collection.
- Keep the core demo fully operational without OpenAI/Anthropic/Gemini or other paid inference.

### 4. Reference Architecture
Use a monorepo:
- `backend/` — FastAPI, SQLAlchemy/SQLite, collectors, analytics engine, APIs, tests.
- `frontend/` — React + TypeScript + Vite analyst console.
- `prompts/` — this master prompt and future experiment prompts.
- `docs/` — architecture, threat model, data-source matrix, judge demo and evaluation notes.
- `data/demo/` — synthetic/public-safe demo fixtures.

Pipeline:
`Connector -> Normalizer -> Deduplicator -> SQLite -> NLP/Trend Engine -> Graph Engine -> API -> Analyst Console`

### 5. Canonical Data Model
Normalize all sources to a common `Post` representation with at minimum:
- `id`, `platform`, `external_id`, `author_id`, `author_name`
- `text`, `url`, `created_at`, `collected_at`
- `language`, `declared_location`
- `like_count`, `reply_count`, `share_count`, `view_count`
- `hashtags[]`, `mentions[]`, `urls[]`
- `reply_to`, `reshare_of`
- `raw_metadata`
- provenance: `collector_mode`, `source_hash`, `quality_score`

Store derived analytics separately or reproducibly derive them from canonical records.

### 6. Connector Strategy
Implement adapters with one shared interface.

**Telegram**
- Primary free mode: parse public channel preview pages (`https://t.me/s/<channel>`).
- Optional official/user mode: Telethon with user-provided `TG_API_ID` and `TG_API_HASH`.
- Public channels only by default.

**YouTube**
- Official mode: YouTube Data API v3 using `YOUTUBE_API_KEY` (free daily quota).
- Zero-key fallback: `yt-dlp` for public search/video metadata where supported.
- Normalize videos/comments when available; clearly distinguish metadata-only mode.

**X/Twitter**
- Official mode when bearer token is supplied.
- Zero/low-cost public-web fallback should be pluggable and conservative: configurable RSS/Nitter/RSSHub/Jina-reader style endpoints only when reachable.
- Always expose connector status; never claim a fallback is official X API.
- Support analyst import of X exports/JSON/CSV so the end-to-end analytics pipeline remains fully usable when live X access is restricted.

**Instagram**
- Official Graph API mode when credentials are supplied for permitted account/content access.
- Public-profile fallback using `instaloader` only where technically and legally available; fail gracefully.
- Support analyst import of downloaded/exported public datasets.

**Reddit**
- Use public JSON or OAuth when configured.

**Bluesky**
- Use public AT Protocol endpoints without credentials for public search/feed data where available.

**Mastodon**
- Use public instance APIs.

### 7. Analytics Engine
Implement reproducible local analytics:

**Sentiment**
- Base: VADER or equivalent lightweight model.
- Return label, compound score and confidence proxy.
- Aggregate by platform, hour/day, topic and community.
- Compute polarization index and sentiment velocity.

**Language / audience mapping**
- Detect language from text.
- Aggregate self-declared location only; do not infer exact location from hidden signals.
- Account/activity segments from public behavior: high-frequency, broadcaster, conversational, bridge-node, ordinary.

**Trend engine**
- Extract hashtags, keywords and n-grams.
- Score with a burst function combining recent frequency, previous-window baseline, unique authors and cross-platform count.
- Show trend velocity and first-seen/last-seen.
- Cluster text with TF-IDF + KMeans (or optional sentence embeddings) into narratives.

**Network engine**
- Directed weighted graph from mentions/replies/reshares; additional co-hashtag/co-URL edges labelled separately.
- Metrics: degree, weighted degree, PageRank, betweenness, community detection.
- Identify bridges and influential nodes with interpretable reasons.
- Return nodes/edges in frontend-friendly JSON.

**Coordination signals (bonus, not a replacement for PS requirements)**
- Near-identical text within short windows.
- Shared URLs/hashtags posted by multiple accounts with abnormal synchrony.
- Clearly label as `coordination_signal`, not definitive bot attribution.

### 8. Evidence & Trust
- SHA-256 hash normalized source records for tamper-evident provenance.
- Every insight response should contain source IDs or evidence references.
- Add a quality score based on completeness, recency and connector confidence.
- Deduplicate exact/near-duplicate records.

### 9. Analyst Console UX
Create a fast dark intelligence-dashboard look, but prioritize legibility over decoration.
Required views:
1. **Overview** — total posts, active platforms, sentiment distribution, top trend, influential node, collection health.
2. **Live/Evidence Feed** — sortable normalized records with platform badges, timestamps and source links.
3. **Trends** — ranked trend table, burst score, platform spread, sparkline/time-series.
4. **Sentiment** — distribution and temporal drift.
5. **Network** — force-directed graph, influential nodes, community/bridge table.
6. **Audience** — language, declared-location and activity-segment aggregates.
7. **Sources** — connector modes/status, setup hints, last error and record count.
8. **Scenario/Demo controls** — seed/reset demo and run collection by query/source.

### 10. API Surface
At minimum:
- `GET /api/health`
- `GET /api/sources`
- `POST /api/demo/seed`
- `DELETE /api/demo/reset`
- `POST /api/collect`
- `GET /api/posts`
- `GET /api/analytics/overview`
- `GET /api/analytics/sentiment`
- `GET /api/analytics/trends`
- `GET /api/analytics/network`
- `GET /api/analytics/audience`

### 11. Reliability
- Connector failures must not crash the application.
- Use timeouts, retries with bounded backoff, clear errors and rate-limit-aware behavior.
- Ensure repeated demo seeding is idempotent.
- Validate inputs with Pydantic.
- Paginate post feeds.
- Add CORS for local frontend development.

### 12. Security & Privacy
- No secret logging.
- Sanitize external URLs/text displayed in UI.
- Limit collector targets to public content.
- Provide retention/reset controls.
- Document legal/ethical guardrails.
- Demographic output must stay aggregated and avoid protected-trait guessing.

### 13. Testing
Write tests for:
- normalization
- deduplication
- sentiment output contract
- trend ranking
- graph construction/influence
- demo seeding
- health/analytics API smoke tests

### 14. Demo Story for Jury
Prepare one coherent 3–5 minute scenario:
1. Open dashboard with deterministic seeded cross-platform chatter around a fictional crisis/event.
2. Show ingestion provenance and source health.
3. Show the same narrative appearing across Telegram, X, Instagram and YouTube.
4. Show trend burst rising before total volume peaks.
5. Show sentiment polarization.
6. Open network graph and identify a bridge/influencer with metric-based explanation.
7. Filter evidence to prove the insight is grounded in posts.
8. Switch to Sources page and explain zero-cost/fallback strategy and how official credentials plug in.
9. End with privacy-safe demographics and coordination warning, stressing these are evidence signals, not unsupported identity claims.

### 15. Judge-Ready Success Criteria
The project is complete only when:
- a fresh clone can be started with documented commands;
- backend unit/smoke tests pass;
- deterministic demo works without API keys;
- at least Telegram plus two additional public/no-key connectors have executable implementations, while X/Instagram/YouTube official modes are represented where credentials are required;
- all four PS analytic vectors are visible in the UI;
- every major insight has evidence/provenance;
- README includes architecture, setup, platform-access truth table, demo steps, limitations and cost model;
- no paid service is required for the core demonstration.

### 16. Engineering Rules
- Prefer small, readable modules over framework complexity.
- Never hard-code secrets.
- Never fake a successful live collection.
- Do not overclaim demographic precision, bot detection or attribution.
- Preserve the ability to swap collectors/models later.
- Maintain Git history in meaningful milestones: foundation -> ingestion -> analytics -> UI -> tests/docs.

### 17. Final Deliverables
- Complete source code.
- Master prompt in `prompts/`.
- `.env.example`.
- Demo fixtures.
- Architecture and source-access documentation.
- Test suite.
- One-command/local quick-start scripts where practical.
- SIH judge demo guide and likely Q&A.

Execute the build autonomously. When blocked by a platform restriction, implement the best legal free fallback plus an import path, mark connector status honestly, and continue. Do not allow a single vendor/API limitation to stop the analytics platform.
