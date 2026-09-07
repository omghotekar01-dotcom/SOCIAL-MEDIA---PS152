# NEXUS — Narrative & Influence Intelligence

**Smart India Hackathon 2026 · SIH26152 · Social Media Analytics · NTRO**

> **Collect public social conversations, separate the post from the public reaction, detect what is changing, map how it spreads, and keep the evidence behind every conclusion.**

NEXUS is a production-minded SIH prototype that normalizes public/authorized social data into one evidence store and exposes the five SIH26152 capability groups represented in this repository.

## A — Continuous Data Collection & Timeline Management

- timestamped root posts + comments/replies;
- Telegram Bot API and monitored public channels;
- exact-video YouTube Data API conversation collection;
- public Bluesky, Reddit and Mastodon paths;
- authorized Meta paths when credentials/permissions exist;
- X official search when authorized, explicit public-post oEmbed where available, and disclosed IMPORT fallback;
- continuous 60-second multi-source watch;
- SQLite historical evidence store;
- explicit `LIVE | IMPORT | REPLAY` provenance.

Original source-priority tiers are shown in the judge-facing UI:

- **ESSENTIAL:** X + Telegram
- **DESIRABLE:** Instagram + Facebook
- **APPRECIABLE:** Reddit + YouTube

## B — Multi-Dimensional Sentiment Inference

NEXUS separates the author/root post from the audience response and analyzes:

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
- sarcasm signal;
- reaction direction (`STABLE / WATCH / ESCALATING`);
- emotion/stance/sarcasm movement over the source-timestamped timeline.

These are descriptive NLP signals bounded to collected evidence, not intent/guilt/clinical classifications.

## C — Automated Aggregate Demographic Profiling

Privacy-conscious audience signals include:

- language;
- broad geography when publicly supported;
- broad professional-interest categories;
- age bracket only when explicit/self-declared evidence supports it;
- pseudonymous aggregation;
- coverage + confidence;
- k-anonymity-style small-group suppression.

NEXUS does not guess protected/sensitive traits from names, photographs or behavior.

## D — Real-Time Trend & Topic Detection

The analytics engine exposes:

- semantic narrative clustering;
- ranked narratives;
- growth and burst deviation;
- author diversity;
- cross-platform presence;
- engagement and recency;
- velocity and momentum;
- next observed 15-minute bucket estimate;
- forecast confidence;
- rising / falling / viral / shifting terms;
- evidence-backed narrative chronology and corrections.

“Earliest observed” always means earliest in the collected dataset, never absolute internet origin.

## E — Link Analysis & Network Topology

The network layer distinguishes direct evidence from weaker co-discussion evidence.

Direct/stronger relationship signals can include:

- replies;
- mentions;
- provider-observed public-follow relationships where available.

Weaker contextual links can include:

- shared domains;
- shared hashtags;
- shared topics;
- narrative co-amplification.

NEXUS calculates and displays:

- PageRank;
- betweenness;
- degree centrality;
- communities;
- High Reach Nodes;
- Bridge Nodes;
- key opinion-leader candidates;
- direct vs co-discussion edge counts;
- cross-community flows;
- timestamped community/segment adoption and sentiment-spread chronology.

Structural roles do **not** imply identity, guilt, intent, coordination or real-world influence outside the observed graph.

---

# Primary prototype sources

## Telegram — controlled live comments

For a dependable jury test:

1. Use a channel such as `NexusSIHDemo`.
2. Link a discussion group.
3. Add the NEXUS bot to the channel and linked discussion group; admin visibility is easiest.
4. Keep the bot token only in `.env`.
5. Create a **new** channel post after setup and add comments/replies.
6. In NEXUS open **Prototype Sources → Poll Bot comments now**.

The rich parser maps the discussion group's automatic channel-forward back to the original channel post and links comments/replies into the same conversation.

Telegram Bot API polling is not an arbitrary historical chat scraper.

## YouTube — official public comments/replies

Configure locally:

```env
YOUTUBE_API_KEY=YOUR_LOCAL_KEY
YOUTUBE_MAX_COMMENTS_PER_VIDEO=0
YOUTUBE_MAX_COMMENT_PAGES_PER_VIDEO=0
YOUTUBE_MAX_REPLY_PAGES_PER_THREAD=0
```

Then:

```text
Prototype Sources
→ paste exact public YouTube URL
→ Load video + comments/replies
```

The exact-video flow is:

```text
video metadata
→ fast first comment/reply batch
→ UI becomes usable
→ provider-bounded exhaustive crawl continues in background
→ commentThreads pagination
→ additional replies via comments.list(parentId=...)
→ final captured/coverage/stop metadata written to root evidence
```

`0` means no NEXUS-side count/page ceiling for the exact-video crawl. Provider exhaustion, disabled comments, quota/rate limits and inaccessible rows remain natural boundaries.

A per-search generation token prevents a stale background crawl from contaminating a newer workspace, including when the same video is loaded again.

---

# Extra public / authorized sources

The simple **Prototype Sources** drawer can also append:

- Telegram public channel preview;
- Bluesky + public replies;
- Reddit + public/OAuth comments where permitted;
- Mastodon + public status-context replies.

Authorized/configured paths also exist for:

- X recent search;
- Instagram professional-account / hashtag access;
- Facebook Page access;
- YouTube keyword search.

Provider failures stay explicit. NEXUS never converts a failed live connector into hidden demo data.

---

# Evidence integrity

Every normalized event keeps, where available:

- platform;
- original source event ID;
- event type;
- public author display + privacy-preserving pseudonymous ID;
- text;
- source timestamp (`created_at`);
- separate ingestion timestamp;
- source URL;
- parent / conversation IDs;
- mentions / hashtags / URLs;
- engagement counters;
- provenance metadata;
- connector run ID;
- `LIVE | REPLAY | IMPORT` source mode;
- derived sentiment / emotion / stance / sarcasm / topic / narrative fields.

Duplicate `(platform, source_event_id)` rows are suppressed.

The evidence/certificate layer supports replayable narrative evidence and explicit `ABSTAIN` behavior when provenance/confidence requirements are insufficient.

---

# Simple operator UI

After launch, use only two persistent controls:

### Prototype Sources

For:

- YouTube exact conversation load;
- Telegram Bot comments;
- Telegram public channel;
- extra public source append;
- 60-second Live Watch;
- current source counts;
- YouTube crawl status;
- rising/viral terms;
- quick A–E health.

### PS26152 CORE

For the full judge-facing A→E requirement proof view:

- collection/timeline;
- multidimensional sentiment;
- demographics;
- trends/topics/forecast;
- link topology/propagation.

Normal analyst tabs remain available for deeper inspection:

- Overview
- Posts / Explorer
- Timeline
- Trends
- Narrative
- Network
- Demographics
- Alerts
- Evidence

---

# Run on Windows

From repository root:

```bat
scripts\start_demo.bat
```

The launcher:

1. validates Python/Node/npm;
2. creates `.env` only if missing;
3. creates/uses `.venv`;
4. checks/install dependencies;
5. runs the base project preflight;
6. runs the SIH26152 A–E runtime-completeness gate;
7. starts FastAPI;
8. seeds the deterministic disclosed jury dataset;
9. starts the React console;
10. opens `http://127.0.0.1:5173`.

You want:

```text
PRE-FLIGHT PASSED
SIH26152 COMPLETENESS CHECK PASSED
```

Useful endpoints:

```text
UI:           http://127.0.0.1:5173
API docs:     http://127.0.0.1:8000/docs
Health:       http://127.0.0.1:8000/health
Certificates: http://127.0.0.1:8000/api/certificates
```

Maven/Java are optional unless the Spring gateway is used.

---

# Safe connector diagnostic

Telegram + YouTube diagnostic:

```bat
.\.venv\Scripts\python.exe .\scripts\comments_doctor.py
```

Specific YouTube video:

```bat
.\.venv\Scripts\python.exe .\scripts\comments_doctor.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

The diagnostic does not print your bot token or YouTube API key.

---

# Deterministic jury resilience

The project starts with a fictional dataset covering:

- X;
- Telegram;
- Instagram;
- Facebook;
- Reddit;
- YouTube;
- root posts + linked audience reactions;
- trend bursts/corrections;
- multidimensional sentiment;
- demographics;
- interaction/network evidence.

All such rows are explicitly `REPLAY`. Use them to show the complete product when venue internet/provider access is unreliable, then use Telegram and/or YouTube to prove real `LIVE` ingestion.

---

# Clean submission ZIP

```bat
scripts\export_submission.bat
```

The exporter uses `git archive`, so local `.env`, `.venv`, `node_modules`, credentials and runtime databases are not packaged.

For detailed setup and requirement traceability see:

- `START_HERE.md`
- `docs/TELEGRAM_YOUTUBE_COMMENTS_SETUP.md`
- `docs/PS26152_TRACEABILITY.md`
- `docs/SIH26152_COMPLETE_REQUIREMENT_MAP.md`
- `docs/JURY_DEMO_5_MIN.md`
