# NEXUS — START HERE

**SIH26152 — Social Media Analytics**  
Narrative & Influence Intelligence workspace aligned to the original NTRO problem-statement requirements represented in this repository.

## 1. Run the project

From the repository root on Windows:

```bat
scripts\start_demo.bat
```

If `.env` does not exist, the starter creates it from `.env.example`. If `.env` already exists, **do not overwrite it**. Keep API keys/tokens local and never commit them.

Then open:

```text
http://127.0.0.1:5173
```

`start_demo.bat` runs both the base preflight and the SIH26152 A–E runtime-completeness gate before launching.

---

## 2. The two controls you actually need

The operator UI is intentionally simple now.

### Prototype Sources

Bottom-right:

```text
Prototype Sources
Telegram + YouTube + 5/5 health
```

Use this for all live-prototype collection:

1. **YouTube** — paste one exact public video URL and click **Load video + comments/replies**.
2. **Telegram** — click **Poll Bot comments now** for Bot API channel/discussion messages, or **Read public channel** for the monitored public channel.
3. **Extra coverage** — **Append public mix** adds available Telegram public + Bluesky + Reddit + Mastodon evidence without clearing the workspace.
4. **Continuous watch** — **Start 60s Live Watch** repeatedly checks Telegram Bot when configured, monitored Telegram, Bluesky, Reddit and Mastodon.
5. The same drawer shows live **A–E 5/5 health** and rising/viral terms from the full backend analytical population.

### PS26152 CORE

Bottom-center:

```text
PS26152 CORE
5/5 requirement view
```

This is the judge/audit console for all five original expected-solution components.

---

## 3. A — Continuous Data Collection & Timeline Management

NEXUS shows:

- historical event count;
- root posts;
- comments/replies;
- source timestamps and chronology span;
- continuous collector state;
- platform priority tiers:
  - **ESSENTIAL:** X + Telegram
  - **DESIRABLE:** Instagram + Facebook
  - **APPRECIABLE:** Reddit + YouTube
- per-platform current evidence;
- connector state;
- `LIVE / IMPORT / REPLAY` provenance.

The active database is a timestamped SQLite event store. A new workspace clears the prior analyst query so unrelated searches do not silently mix.

---

## 4. B — Multi-Dimensional Sentiment Inference

The active runtime exposes:

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
- emotion / stance / sarcasm fluctuation over source-timestamped time buckets;
- Public Reaction Intelligence with `STABLE / WATCH / ESCALATING` descriptive attention state.

Open:

```text
Timeline
```

for both the volume/polarity chart and the dedicated emotion/stance/sarcasm timeline.

---

## 5. C — Automated Demographic Profiling

Open:

```text
Demographics
```

NEXUS shows aggregate/anonymized:

- language;
- broad geography when publicly supported;
- broad professional-interest categories;
- age brackets only when explicit/self-declared evidence supports them;
- coverage;
- confidence;
- k-anonymity small-group suppression.

Professional-interest profiling may use broad, non-sensitive observed public topic behaviour when profile/bio indicators are absent. Age is **not** guessed from names, photographs or behaviour.

---

## 6. D — Real-Time Trend & Topic Detection

Open:

```text
Trends
```

and the `PS26152 CORE` view.

The active runtime shows:

- ranked narratives;
- growth;
- burst deviation;
- author diversity;
- engagement;
- recency;
- velocity;
- momentum;
- next 15-minute observed-bucket forecast;
- forecast confidence;
- rising / falling / shifting terms;
- next-window keyword estimate.

Trend/origin language is bounded to the **collected dataset**. “Earliest observed” never claims absolute internet origin.

---

## 7. E — Link Analysis & Network Topology

Open:

```text
Network
```

NEXUS exposes:

- nodes + edges;
- direct relationship evidence:
  - reply;
  - mention;
  - provider-observed public-follow where available;
- weaker co-discussion evidence separately:
  - shared domain;
  - shared hashtag;
  - shared topic;
  - narrative co-amplification;
- PageRank;
- betweenness;
- degree centrality;
- communities;
- High Reach Nodes;
- Bridge Nodes;
- key opinion-leader candidates;
- direct vs co-discussion edge counts;
- cross-community flows;
- timestamped segment-adoption / sentiment-spread chronology.

These are structural observations inside the collected graph. They do **not** assert identity, intent, guilt, coordination or wrongdoing.

---

## 8. Best deterministic jury walkthrough

The project starts with a deterministic fictional jury dataset so every analytics screen can be demonstrated even if venue internet or a provider is unavailable.

The dataset is explicitly labelled **REPLAY** and contains:

- X;
- Telegram;
- Instagram;
- Facebook;
- Reddit;
- YouTube;
- root posts + linked reactions;
- mixed sentiment / emotion / stance;
- trend bursts + corrections;
- demographic aggregate signals;
- interaction/network evidence.

Walk through:

1. **PS26152 CORE** — show A → E at a glance.
2. **Posts / Explorer** — open a root post and show Public Reaction Intelligence.
3. **Timeline** — volume/polarity, then emotion/stance/sarcasm fluctuation.
4. **Trends** — ranked narrative + forecast + keywords.
5. **Narrative** — earliest observed evidence and variants.
6. **Network** — KOL candidates, communities, Bridge/High Reach nodes and cross-community spread.
7. **Demographics** — coverage/confidence/suppression.
8. **Evidence** — exact provenance and source mode.

---

## 9. Live YouTube proof — recommended

Prerequisite in your local `.env`:

```env
YOUTUBE_API_KEY=YOUR_LOCAL_KEY
YOUTUBE_MAX_COMMENTS_PER_VIDEO=0
YOUTUBE_MAX_COMMENT_PAGES_PER_VIDEO=0
YOUTUBE_MAX_REPLY_PAGES_PER_THREAD=0
```

Then:

```text
Prototype Sources
→ paste exact YouTube URL
→ Load video + comments/replies
```

NEXUS now uses:

```text
exact video
→ official YouTube Data API v3
→ video metadata
→ fast first reaction batch
→ UI becomes usable
→ exhaustive public commentThreads pagination continues in background
→ missing inline replies fetched via comments.list(parentId=...)
→ final captured count / completion / stop reason stored on root evidence
→ dashboard refreshes automatically
```

`0` means no NEXUS-side count/page ceiling for that provider-bounded exact-video crawl. Collection can still end because YouTube has no more public pages, comments are disabled, quota/rate limits are reached, or the provider does not expose a row.

For a source diagnostic without revealing the key:

```bat
.\.venv\Scripts\python.exe .\scripts\comments_doctor.py "PASTE_YOUTUBE_URL_HERE"
```

---

## 10. Live Telegram proof — recommended

For the controlled demo:

1. Keep your channel, e.g. `NexusSIHDemo`.
2. Link a discussion group to the channel.
3. Add the NEXUS bot to the channel **and** linked discussion group; admin visibility is the easiest prototype setup.
4. If required, disable BotFather Group Privacy and re-add the bot to the discussion group.
5. Keep this blank during the first test so the discussion group is not accidentally filtered:

```env
TELEGRAM_ALLOWED_CHAT_IDS=
```

6. Create a **NEW** channel post after bot setup.
7. Add several real comments/replies through the channel’s Comments UI.
8. In NEXUS:

```text
Prototype Sources
→ Poll Bot comments now
```

The rich Telegram parser maps the linked discussion auto-forward back to the original channel post and links discussion comments/replies into the same conversation. Telegram Bot API polling is not an arbitrary downloader for old chat history, so create fresh test messages after the bot is correctly configured.

For a safe diagnostic that does not print the bot token:

```bat
.\.venv\Scripts\python.exe .\scripts\comments_doctor.py
```

---

## 11. Extra live/public coverage

Inside **Prototype Sources** use:

```text
Append public mix
```

This attempts available low-cost/public collection from:

- monitored Telegram public channel;
- Bluesky + public replies;
- Reddit + comments where Reddit permits access;
- Mastodon + public status-context replies.

Then use:

```text
Start 60s Live Watch
```

to repeat those sources plus Telegram Bot polling when your bot token is configured.

X remains explicit because unrestricted recent-search/reply access requires authorized provider access. Known public X URLs can use the oEmbed path where X permits it; analyst-copied public X conversations remain `IMPORT`, never fake `LIVE`.

---

## 12. Verify before presenting

Run:

```bat
scripts\start_demo.bat
```

You want both gates to pass before launch:

```text
PRE-FLIGHT PASSED
SIH26152 COMPLETENESS CHECK PASSED
```

The second gate now verifies the **active runtime wiring**, not just file existence: PS-specific timeline, demographics, network propagation, six-platform disclosed demo, Telegram comment linkage, YouTube staged/exhaustive support, A–E output, and the frontend requirement surfaces.

Maven remains optional unless you use the Spring gateway.

---

## 13. Create a clean submission ZIP

Run:

```bat
scripts\export_submission.bat
```

The exporter uses `git archive`, so local `.env`, `.venv`, `node_modules`, credentials and local runtime files are not packaged.

## Evidence integrity

NEXUS keeps `LIVE`, `IMPORT` and `REPLAY` explicitly separated. It does not claim absolute internet origin when only the earliest event in the collected dataset is known. Provider fallbacks are not misrepresented as unrestricted official access, and privacy-sensitive demographic traits are not invented when the source does not support them.
