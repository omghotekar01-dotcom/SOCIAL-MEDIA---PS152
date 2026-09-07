# NEXUS — START HERE

**SIH26152 — Social Media Analytics**  
Narrative & Influence Intelligence workspace aligned to the original NTRO problem statement.

## 1. Run the project

From the repository root on Windows:

```bat
copy .env.example .env
scripts\start_demo.bat
```

If `.env` already exists, do **not** overwrite it. Keep API keys/tokens local and never commit them.

Then open:

```text
http://127.0.0.1:5173
```

`start_demo.bat` runs pre-flight checks before launching.

## 2. The original SIH26152 requirement view

After NEXUS opens, use the bottom-center:

```text
PS26152 CORE — 5/5 requirement view
```

This is the jury/audit console for the five original expected-solution components:

### A — Continuous Data Collection & Timeline Management

Shows:

- historical event count;
- root posts;
- comments/replies;
- observed chronology span;
- Live Watch state;
- platform tiers and current evidence:
  - **ESSENTIAL:** X + Telegram
  - **DESIRABLE:** Instagram + Facebook
  - **APPRECIABLE:** Reddit + YouTube
- connector state and LIVE/IMPORT/REPLAY disclosure.

### B — Multi-Dimensional Sentiment Inference

Shows:

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
- root-content sentiment kept separate from audience-comment sentiment;
- emotion / stance fluctuation over the source-timestamped timeline.

### C — Automated Demographic Profiling

Shows aggregate, anonymized:

- language;
- broad geography;
- professional-interest categories;
- age brackets when explicitly/self-declared support exists;
- coverage + confidence;
- k-anonymity small-group suppression.

Professional-interest profiling may use broad non-sensitive public topic behavior when profile/bio indicators are absent. Age is **not** guessed from names, photos or behavior.

### D — Real-Time Trend & Topic Detection

Shows:

- ranked narratives;
- growth / burst / diversity / engagement / recency;
- trend momentum;
- velocity;
- next 15-minute observed-bucket forecast;
- forecast confidence;
- rising / falling / shifting keywords.

### E — Link Analysis & Network Topology

Shows:

- observed nodes + edges;
- direct relationship evidence (`reply`, `mention`, provider-observed `public-follow` where available);
- weaker co-discussion relationships shown separately;
- PageRank;
- betweenness;
- degree centrality;
- communities;
- High Reach Nodes;
- Bridge Nodes;
- key opinion-leader candidates;
- cross-community flows;
- timestamped segment-adoption / sentiment-spread chronology.

These are structural observations inside the collected graph, not identity, guilt, intent or wrongdoing claims.

## 3. Best deterministic jury walkthrough

Click **Demo** first when you want a guaranteed, venue-safe demonstration.

The deterministic demo is explicitly labelled **REPLAY** and covers:

- X;
- Telegram;
- Instagram;
- Facebook;
- Reddit;
- YouTube;
- posts + linked reactions;
- mixed sentiment / emotion / stance;
- trend bursts + corrections;
- demographic aggregate signals;
- interaction/network evidence.

Then walk through:

1. **PS26152 CORE** — show A → E at a glance.
2. **Posts / Explorer** — show root content + Public Reaction Intelligence.
3. **Timeline** — show volume/polarity, then emotion/stance/sarcasm fluctuation.
4. **Trends** — show ranked narrative and evidence-backed chronology.
5. **Narrative** — show earliest observed event and variants.
6. **Network** — show KOL candidates, Bridge/High Reach nodes and cross-community spread.
7. **Demographics** — show coverage/confidence/suppression.
8. **Evidence** — prove exact provenance and LIVE/IMPORT/REPLAY mode.

## 4. Live-source proof

### Telegram

For real comments, use an authorized bot in the controlled channel **and its linked discussion group**. Use:

```text
Social Sources → Telegram → Bot API
```

`NexusSIHDemo` remains the default monitored demo channel:

```env
TELEGRAM_PUBLIC_CHANNELS=NexusSIHDemo
```

### YouTube

With a valid YouTube Data API v3 key, paste an exact public video URL into **Fresh Search**.

NEXUS uses a fast-first flow so the UI becomes usable quickly, then continues provider-bounded public comment/reply collection in the background.

```env
YOUTUBE_API_KEY=YOUR_LOCAL_KEY
YOUTUBE_MAX_COMMENTS_PER_VIDEO=0
YOUTUBE_MAX_COMMENT_PAGES_PER_VIDEO=0
YOUTUBE_MAX_REPLY_PAGES_PER_THREAD=0
```

`0` means no NEXUS-side count/page ceiling for the exact-video exhaustive path. Collection still stops when YouTube exhausts public pages or the provider blocks/rate-limits access.

### X

Without commercial/authorized X search access:

- use an explicit public X Post URL through the public oEmbed path where X permits it;
- or use Manual X Conversation Import for analyst-copied public post/reply evidence.

Manual/import evidence remains `IMPORT`, never fake `LIVE`.

## 5. Interface controls

- **Light mode is default**.
- Use the top-right Theme control for dark mode.
- Press **Ctrl+K** / **Cmd+K** to focus global search.
- Use **Connections** for connector readiness.
- Use **Social Sources** for source-specific ingestion and enrichment.
- Use **Live Watch** for continuous collection.
- The Overview/PS26152 CORE views distinguish implemented capability from current workspace evidence.

## 6. Verify before presenting

Run:

```bat
.\.venv\Scripts\python.exe .\scripts\preflight.py
```

or simply:

```bat
scripts\start_demo.bat
```

Only treat the current branch as locally verified when you see:

```text
PRE-FLIGHT PASSED
```

Maven is optional unless using the Spring gateway.

## 7. Create a clean submission ZIP

Run:

```bat
scripts\export_submission.bat
```

The exporter uses `git archive`, so local `.env`, `.venv`, `node_modules`, credentials and local runtime files are not packaged.

## Evidence integrity

NEXUS keeps `LIVE`, `IMPORT` and `REPLAY` explicitly separated. It does not claim absolute internet origin when only the earliest event in the collected dataset is known. Provider fallbacks are not misrepresented as unrestricted official platform access, and privacy-sensitive demographic traits are not invented when the source does not support them.
