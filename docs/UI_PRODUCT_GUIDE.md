# NEXUS UI / PRODUCT GUIDE

## Design direction

NEXUS uses a light-first analyst-console design with a complete dark-mode alternative. The interface is intentionally closer to a production social-intelligence product than a college-project dashboard: restrained surfaces, consistent spacing, explicit source truth and dense data only where analysts need it.

## Primary shell

- **Light mode is default**; dark mode is persisted locally.
- The top bar contains global topic/URL search and the primary Fresh Search action.
- `Ctrl+K` / `Cmd+K` focuses global search.
- Connector readiness lives in the floating **Connections** drawer.
- Actual prototype acquisition is consolidated into one floating **Prototype Sources** drawer.
- The original problem-statement proof lives in **PS26152 CORE**.
- Responsive guardrails prevent topbar, sidebar, badges, drawers and long evidence text from overlapping on common laptop widths.

## Two persistent controls

### Prototype Sources

This is the simple operator path. It intentionally replaces the older separate Free Source Lab / Live Watch acquisition drawers.

It contains three steps:

1. **YouTube — Full Public Conversation**
   - exact YouTube URL input;
   - official Data API route;
   - fast-first initial comments/replies;
   - provider-bounded exhaustive background crawl;
   - visible captured/reported counts and background state.
2. **Telegram — Channel + Discussion Comments**
   - Bot API poll;
   - public channel read;
   - visible root/reaction/LIVE counts;
   - clear connector detail.
3. **Extra Public Coverage + Continuous Watch**
   - append Telegram public + Bluesky + Reddit + Mastodon evidence;
   - start/stop 60-second continuous watch;
   - no implicit paid X polling.

The same drawer also gives a compact **A–E 5/5 Health** view and full-population rising/viral keyword signals.

### PS26152 CORE

This is the judge/audit view. It maps the active workspace to:

- **A** — Continuous Data Collection & Timeline Management
- **B** — Multi-Dimensional Sentiment Inference
- **C** — Automated Demographic Profiling
- **D** — Real-Time Trend & Topic Detection
- **E** — Link Analysis & Network Topology

Each requirement is shown as `STRONG`, `PARTIAL` or `EMPTY` based on current evidence. The UI does not hard-code success.

## Overview

The command center gives immediate workspace signals:

1. observed event count;
2. LIVE evidence count;
3. distinct platform coverage;
4. connector readiness;
5. priority narratives and source coverage truth.

Root-post sentiment and audience/comment sentiment are handled separately by the reaction analytics instead of being merged into one misleading score.

## Posts / Explorer

The explorer is built for investigation rather than a static feed.

Analysts can:

- filter by platform;
- filter by `LIVE`, `REPLAY` or `IMPORT`;
- search within collected post/comment text, authors, hashtags, mentions and topic terms;
- switch newest/oldest ordering;
- inspect source media / YouTube embeds / X oEmbed cards;
- inspect engagement and event-level NLP;
- inspect **Public Reaction Intelligence** for a root conversation;
- inspect exact connector, event IDs and provenance;
- open the original public source when a valid source URL exists.

Browser rendering stays bounded for performance while backend analytics can use the full active population.

## Timeline

The Timeline page contains two distinct visual layers:

1. **Conversation volume & sentiment movement**
   - volume;
   - positive;
   - neutral;
   - negative.
2. **Emotion, stance & sarcasm fluctuation**
   - anxiety;
   - anger;
   - excitement;
   - supportive stance;
   - against stance;
   - sarcasm;
   - backend buckets also retain the remaining emotion dimensions.

The timeline uses source timestamps. Visual zero-volume padding never becomes synthetic evidence.

## Trends / Narrative

The trend experience exposes:

- narrative score;
- growth;
- burst;
- diversity;
- platform spread;
- engagement;
- recency;
- momentum / velocity;
- next-bucket forecast;
- evidence lineage;
- rising/falling/shifting keywords through the PS/core surfaces.

“Earliest observed” remains bounded to the collected dataset.

## Network

The Network page shows:

- interactive community/influence graph;
- PageRank;
- betweenness;
- degree centrality;
- High Reach / Bridge roles;
- key opinion-leader candidates;
- direct vs co-discussion edge counts;
- relationship edge types;
- cross-community flows;
- segment-adoption chronology;
- community-level sentiment-spread context.

Direct interaction evidence and weaker co-discussion relationships are visibly separated. Structural roles never imply guilt, identity, intent or coordination.

## Demographics

The Demographics page shows aggregate, pseudonymous audience signals with explicit coverage/confidence:

- language;
- broad geography when public evidence supports it;
- broad professional interests;
- age bracket only when explicit/self-declared evidence supports it;
- k-anonymity small-group suppression.

## Connections drawer

The Connection Center is a readiness/configuration surface, not the main collection workflow. It supports filters such as:

- All
- High priority
- Ready
- Needs setup

A platform can have a public fallback while its official richer connector still needs credentials. Detail text preserves that distinction.

## Reliability UX

- React error boundary prevents one rendering exception from blanking the application.
- YouTube exact-video loading returns a fast initial analytical set while the exhaustive crawl runs server-side.
- Large browser lists are bounded independently from full backend analytics.
- A lightweight YouTube root probe updates crawl state without recalculating the whole dashboard every few seconds.
- Per-search YouTube generation tokens prevent stale background jobs from contaminating newer workspaces.
- Source failures are surfaced rather than silently replaced with demo data.
- Saved theme is restored before React renders.

## Submission safety

Use:

```bat
scripts\export_submission.bat
```

The exporter uses `git archive`, so local `.env`, `.venv`, `node_modules`, local databases and untracked credentials/runtime files are excluded from the submission ZIP.
