# NEXUS — SIH26152 Complete Requirement Map

Problem statement: **SIH26152 — Social Media Analytics**  
Organization: **National Technical Research Organisation (NTRO)**  
Solution: **NEXUS — Narrative & Influence Intelligence**

## What the problem requires

The SIH26152 description centers audience intelligence on four analytical vectors — **sentiment, demographics, trend tracking, and link analysis** — supported by a fifth operational requirement: **continuous multi-platform data collection with exact chronology**.

NEXUS therefore treats the system as an evidence pipeline rather than a dashboard that merely classifies isolated posts.

---

## A. Continuous Data Collection & Timeline Management

### Required behavior
- Multi-platform ingestion.
- Posts, comments/replies and interactions where the provider exposes them.
- Time-stamped historical evidence.
- Exact chronology of conversations.
- Essential focus: X and Telegram.
- Desirable: Instagram and Facebook.
- Appreciable: Reddit/YouTube.

### NEXUS implementation

**Telegram**
- Public monitored-channel preview path.
- Authorized Bot API path.
- Controlled `NexusSIHDemo` demo channel.
- Live messages/posts are time-stamped and deduplicated.

**X / Twitter**
- Official X API v2 recent search when a bearer token/credits are configured.
- Unauthenticated public oEmbed for explicit public Post URLs when X permits it.
- Resilient `x.com` / `twitter.com` URL normalization.
- Media/GIF-only public posts are retained with disclosure when oEmbed exposes no caption.
- Manual X Conversation Import is the guaranteed prototype fallback when provider access blocks the post/thread. It is always labelled `IMPORT`, never `LIVE`.

**Instagram / Facebook**
- Authorized Meta Graph paths for professional account/Page assets and comments where the granted permissions expose them.
- Instagram public-profile fallback is best-effort only and does not bypass login/private controls.

**Bluesky**
- Public AT Protocol search.
- Best-effort public thread replies attached to root posts.

**Mastodon**
- Public instance search with configured fallback instances.
- Best-effort status-context replies.

**Reddit**
- OAuth search when configured.
- Low-volume public fallback where permitted.
- Best-effort public comments attached to submissions.

**YouTube**
- Zero-key public video metadata fallback.
- Official YouTube Data API v3 path for video search/comments when a key is configured.

**Continuous collector**
- Default zero-cost/public cycle: Telegram monitored channels + Bluesky + Reddit + Mastodon.
- Official X and YouTube continuous polling are opt-in to protect paid credits/quota.
- Authorized Meta polling is opt-in.
- One source failure cannot stop the collection loop.

### Provenance contract
Every event carries:
- platform,
- source event ID,
- event type,
- source mode (`LIVE`, `IMPORT`, `REPLAY`),
- connector/run information,
- observed/created time,
- source URL when available,
- conversation and parent linkage,
- raw evidence hash after storage.

---

## B. Multi-Dimensional Sentiment Inference

NEXUS separates **author content analysis** from **audience reaction analysis**.

### Per-event NLP
- positive / negative / neutral sentiment,
- **8 emotion dimensions**:
  1. anxiety,
  2. anger,
  3. excitement,
  4. sadness,
  5. joy,
  6. disgust,
  7. surprise,
  8. trust,
- supportive / against / unclear stance,
- sarcasm probability,
- language signal,
- topic terms,
- quality score.

The current hackathon implementation uses transparent VADER + lexical signals so every fallback is explainable. The model boundary is explicit in `inference_method` and can later be replaced by transformer models without changing the evidence schema.

### Public Reaction Intelligence
For each root post, captured comments/replies are analyzed separately to show:
- comment/reply count,
- positive/negative/neutral reaction share,
- supportive vs against stance,
- anger/anxiety/disgust indicators,
- sarcasm,
- polarization,
- unique reaction authors,
- descriptive reaction risk score,
- `STABLE`, `WATCH`, or `ESCALATING` direction,
- sample supporting evidence.

**Important:** this score describes the captured reaction environment. It does not claim wrongdoing, intent, guilt, or internet-wide opinion.

---

## C. Automated Demographic Profiling

NEXUS exposes only **aggregate anonymized audience signals**.

### Signals
- language,
- broad geography,
- professional interests,
- age brackets.

### Privacy controls
- pseudonymous user IDs,
- k-anonymity small-group suppression,
- free-form locations are reduced to broad regions,
- professional interests use public bio/headline terms,
- **age is not guessed from names, profile photos, or behavioral stereotypes**,
- age brackets are only populated from explicit self-declared/public age indicators or a provider-supplied age-bracket field.

Each demographic slice exposes coverage, confidence, minimum group size, and method.

---

## D. Real-Time Trend & Topic Detection

NEXUS clusters observed evidence into narratives and ranks them using:
- recent volume growth,
- burst z-score,
- unique-author diversity,
- cross-platform presence,
- engagement signal,
- recency.

Statuses:
- `VIRAL`,
- `RISING`,
- `EMERGING`,
- `STABLE`,
- `DECLINING`.

The advanced trend layer also exposes:
- velocity,
- momentum,
- next observed 15-minute bucket volume estimate,
- forecast confidence.

Forecast wording is intentionally bounded to the **collected dataset**. NEXUS does not claim to predict the whole internet from incomplete connector coverage.

---

## E. Link Analysis & Network Topology

NEXUS builds the graph from observed evidence relationships:
- direct reply edges,
- direct mention edges,
- low-weight shared-domain relationships,
- low-weight narrative co-amplification relationships.

It computes:
- PageRank,
- betweenness centrality,
- degree centrality,
- communities,
- High Reach Nodes,
- Bridge Nodes.

These are structural graph roles only. They are not identity, guilt, attribution, or intent claims.

The network UI provides filtering, node inspection, role explanations and evidence-aware community visualization.

---

# End-to-End Intelligence Flow

```text
MULTI-PLATFORM SOURCES
        |
        v
COLLECTION + PROVENANCE
LIVE / IMPORT / REPLAY
        |
        v
NORMALIZATION + DEDUPLICATION
        |
        +-----------------------------+
        |                             |
        v                             v
ROOT POST NLP                 COMMENTS / REPLIES
sentiment                     public opinions
8 emotions                    stance/emotions
stance/sarcasm                sarcasm
        |                             |
        +-------------+---------------+
                      v
             REACTION INTELLIGENCE
          stable / watch / escalating
                      |
          +-----------+-----------+
          |           |           |
          v           v           v
      TIMELINE      TRENDS      NETWORK
          |           |           |
          +-----------+-----------+
                      v
                NARRATIVE LINEAGE
                      |
                      v
             EXPLAINABLE ALERTS
                      |
                      v
               EVIDENCE LEDGER
```

---

# X Without a Paid API Key — Correct Prototype Strategy

For an explicit public X URL, NEXUS first attempts provider oEmbed. If X refuses that specific post/thread, use **Manual X Conversation Import**:

1. paste the public X URL,
2. paste the exact root-post caption/text (or disclose that the item is media-only),
3. paste visible public replies one per line,
4. add to NEXUS,
5. the root and replies enter the same analytics pipeline as `X / IMPORT`,
6. Reaction Intelligence immediately evaluates the copied public opinions.

This is preferable to copying X content into Telegram because it preserves original platform provenance.

---

# Jury Demonstration Sequence

1. Start NEXUS with `scripts\start_demo.bat`.
2. Show the controlled deterministic `REPLAY` dataset and provenance disclosure.
3. Run a fresh topic search to collect available public/live sources.
4. Show Telegram real-time/public evidence.
5. Paste an X URL and attempt public oEmbed.
6. If X blocks it, demonstrate Manual X Conversation Import with real visible replies.
7. Open Posts / Explorer and show root-post NLP.
8. Show **Public Reaction Intelligence** separately from root sentiment.
9. Open Timeline to show sentiment movement over chronology.
10. Open Trends to show narrative score + momentum.
11. Open Network to show observed influence/community structure.
12. Open Demographics and highlight anonymization + small-group suppression.
13. Open Alerts and explain exactly why an attention signal fired.
14. Open Evidence and prove the source mode and provenance of every item.

---

# Jury-safe positioning

> NEXUS is a source-agnostic social intelligence framework. It continuously collects low-cost/public signals and can activate premium official APIs selectively. The intelligence engine is decoupled from the data vendor, so an authorized production deployment can replace or augment connectors without changing the analytics pipeline. Every conclusion is bounded to collected evidence and every fallback is explicitly disclosed.

This is a **production-minded SIH prototype**, not a claim of unrestricted access to provider-controlled social-media data.
