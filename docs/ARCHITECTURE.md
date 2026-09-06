# NEXUS Architecture

## Design goal

NEXUS is built around one invariant: **every analytical claim must be traceable to timestamped observed evidence and bounded by data coverage.**

## Runtime layers

### 1. Connector layer

Implemented in `backend-ai/app/connectors.py`.

- X API v2 recent search
- Telegram Bot API `getUpdates`
- YouTube Data API search + comments
- Meta Instagram professional-account media/comments
- Facebook Page feed/comments
- replay/import

Each connector converts provider payloads into the same `SocialEventIn` contract before data enters analytics.

### 2. Event store

`backend-ai/app/db.py`

Hackathon default: SQLite.

Responsibilities:
- schema creation
- platform/source ID deduplication
- source timestamp preservation
- separate ingestion timestamp
- salted pseudonymous author ID
- storage of derived analytical fields

Production scale path: PostgreSQL/PostGIS without changing API-facing event semantics.

### 3. Continuous collection

`backend-ai/app/collector.py`

The process can continuously poll configured sources at >=60 second intervals. Telegram is default-on in the free-first mode. X and YouTube are opt-in because they can consume credits/quota.

One source failure is isolated and reported; it does not terminate the collector or other sources.

### 4. Analytics

`backend-ai/app/analytics.py`

Current stable demo engines:

- language detection
- polarity sentiment
- stance estimate
- emotion distribution
- sarcasm heuristic with uncertainty
- term extraction
- TF-IDF semantic narrative similarity
- time/URL/hashtag-aware clustering
- explainable trend/burst scoring
- network construction and centrality
- aggregate/k-anonymous audience signals
- explainable alert construction

The algorithms are deliberately transparent and lightweight for offline hackathon reliability.

### 5. FastAPI analytical API

`backend-ai/app/main.py`

Exposes ingestion, collector controls, analytics, evidence lookup and export.

### 6. Spring application gateway

`backend-java/`

Spring Boot is the organization-facing application layer:
- gateway health
- analyst demo session
- proxy boundary between UI and Python analytics
- RBAC-ready role model
- integration point for future organization identity/SSO

The jury demo may use FastAPI directly to reduce setup risk.

### 7. Analyst console

`frontend/`

React/TypeScript workstation screens:
- Overview
- Timeline
- Trends
- Narrative lineage
- Network
- aggregate Demographics
- Alerts
- Evidence ledger

Every event visibly preserves `LIVE`, `REPLAY`, or `IMPORT` status.

## Data flow

```text
source API
  ↓
platform connector
  ↓
SocialEvent normalization
  ↓
privacy pseudonymization + dedupe
  ↓
SQLite event history
  ↓
NLP enrichment
  ↓
narrative clustering
  ↓
trend scoring + network graph
  ↓
alert/evidence objects
  ↓
FastAPI → Spring gateway(optional) → React analyst console
```

## Narrative lineage

NEXUS never equates a keyword with a narrative. Events are linked through a combination of:
- textual semantic similarity
- shared hashtag
- shared URL/domain
- temporal proximity

Every cluster retains its chronological events. Therefore the UI can show the earliest **observed** evidence in the configured dataset and the later variants.

## Network topology

Graph nodes are privacy-preserving observed account IDs. Available evidence creates edges for:
- reply
- mention
- shared domain
- narrative co-amplification

Metrics:
- PageRank
- degree centrality
- betweenness centrality
- community structure

A central node is never automatically labelled malicious. Structural roles only describe the observed graph.

## Availability philosophy

The architecture is intentionally adapter-driven. A missing platform credential creates a connector state, not an application crash. The analyst can continue with other live sources or clearly labelled replay/import data.

## Scale path

Hackathon → pilot → larger deployment:

1. SQLite → PostgreSQL/PostGIS
2. NetworkX → Neo4j for larger graphs
3. in-process collection → queued workers
4. add Redis for cache/state
5. add Kafka only when ingestion throughput warrants it
6. organization SSO/OIDC at Spring gateway
7. approved long-term retention policies and platform-specific deletion synchronization

No scale component is required just to prove the SIH workflow.
