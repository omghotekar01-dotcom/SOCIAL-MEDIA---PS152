# NEXUS — 5-Minute SIH26152 Jury Demo

Goal: prove the **four required analytics vectors**, live-source capability and evidence discipline in one coherent story. The interface is designed so you can do this without opening configuration screens unless the jury asks.

## Before the slot

1. Pull the latest `build/ps152-complete` branch.
2. Run `scripts\start_demo.bat` and require **PRE-FLIGHT PASSED**.
3. Open `http://127.0.0.1:5173` and hard-refresh once if the browser cached an older frontend.
4. Keep **Light** theme for the main demo unless the projector makes it hard to read; dark mode remains available from the top-right Theme control.
5. Confirm the Overview **Live Intelligence Pulse** renders.
6. Confirm `NexusSIHDemo` contains at least one post matching your live demo keyword.
7. Search that keyword once before the slot and verify Telegram appears in **Posts / Explorer**.
8. Keep the deterministic Demo dataset as fallback. Do not depend on every external source being reachable during judging.
9. Keep **Connections** and **Free Sources** drawers closed at the start so the screen looks like a finished analyst product rather than a setup console.

---

## 0:00–0:35 — Problem + product thesis

Show **Overview**.

Say:

> Social-media analytics often stops at counts, hashtags and a sentiment chart. NEXUS goes further: it reconstructs how a narrative emerges, how sentiment changes, how it moves through communities, and which source records prove the conclusion.

Point to **Live Intelligence Pulse** and quickly show:

- LIVE evidence count;
- platform coverage;
- connector readiness;
- latest observed evidence time.

Then say:

> The first thing the analyst sees is not a vanity metric — it is coverage truth. If we only have one platform, NEXUS warns us before we make a cross-platform claim.

Do not open Connections yet.

---

## 0:35–1:20 — Live collection + selected-post proof

Use the global search box. `Ctrl+K` / `Cmd+K` focuses it instantly.

Search a keyword that exists in `NexusSIHDemo`, then click **Fresh Search**.

NEXUS should move to **Posts / Explorer**.

Show the platform chips and click **Telegram**.

Point out:

- Telegram result card;
- `LIVE` source-mode pill;
- full post text;
- timestamp;
- connector / search session provenance;
- NLP analysis.

Say:

> Every Fresh Search creates a clean workspace. Telegram public channels can be monitored at zero API cost, while the rest of the analytics stack stays independent of the acquisition provider. Every event keeps its source mode and provenance.

If Telegram or another live source is temporarily unreachable, do **not** debug on stage. Click **Demo** and continue. If asked, open **Connections** to show the connector state and fallback path.

---

## 1:20–2:00 — Vector 1: Sentiment + temporal movement

Open **Timeline**.

Show:

- exact source chronology;
- volume movement;
- positive / negative movement;
- theme-aware chart and tooltip.

Say:

> Sentiment is not only an aggregate pie chart. Each evidence item carries its own sentiment, stance and emotion signals, and we aggregate those over time to show when the conversation changes.

If useful, return to Posts / Explorer and use the local search or LIVE filter to show the exact supporting post.

---

## 2:00–2:45 — Vector 2: Trend + narrative lineage

Open **Trends** and select the strongest rising narrative.

Point to:

- trend score;
- growth rate;
- burst z-score;
- author diversity;
- cross-platform count.

Then open **Narrative lineage**.

Say:

> We track narratives, not only exact hashtag strings. Related wording is clustered using semantic and temporal evidence, and the score is decomposable into measurable factors rather than a black-box trending label.

Say this distinction exactly:

> Earliest observed means earliest inside the dataset we actually collected. We never claim absolute internet origin without evidence.

---

## 2:45–3:30 — Vector 3: Link / network analysis

Open **Network**.

Point to a **High Reach Node** and a **Bridge Node** if present.

Say:

> The observed interaction graph combines replies, mentions, shared links and narrative co-amplification. PageRank highlights high-reach positions, betweenness highlights bridges, and community structure shows how information crosses groups. These labels describe network topology — not guilt or intent.

This is one of the strongest visual differentiators from a basic social dashboard.

---

## 3:30–4:05 — Vector 4: Privacy-conscious audience signals

Open **Demographics**.

Show:

- language;
- broad geography where supportable;
- professional-interest categories where supportable;
- coverage/confidence;
- k-anonymity suppression.

Say:

> The problem statement asks for demographics, but individual-level guessing would be unreliable and privacy-invasive. NEXUS therefore produces aggregate, confidence-scored signals and suppresses small groups rather than inventing sensitive traits about individuals.

---

## 4:05–4:35 — Evidence + trust layer

Open **Evidence**.

Click one row and show that it opens the exact post in **Posts / Explorer**.

Point to:

- source platform;
- source mode;
- timestamp;
- source event ID;
- internal evidence ID;
- connector;
- search session;
- inference metadata.

Then, only if useful, open **Free Sources** and click **Verify Evidence**.

Say:

> NEXUS is designed so an analyst can move from a conclusion back to the witness records. Higher-impact conclusions can also be packaged into deterministic evidence certificates; if minimum evidence is not met, the system can abstain instead of overclaiming.

---

## 4:35–5:00 — Architecture + close

If the jury asks about APIs, open **Connections** and filter **High priority**. Show Telegram, X, YouTube and Bluesky.

Say:

> Acquisition changes constantly, so NEXUS separates connectors from the normalized evidence and analytics layers. Low-cost/public sources can detect signals, and official or enterprise feeds can be plugged in without rewriting the intelligence engine.

Close with:

> So the output is not simply “social media is negative today.” The output is: this narrative was first observed at this time in our collected data, accelerated for these measurable reasons, moved through these communities, produced this sentiment shift, and these source records prove the conclusion.

Stop there.

---

# Presentation rules

- Keep the two floating utility drawers closed unless needed.
- Do not test every connector live in front of the jury.
- Never say X offers unrestricted free keyword search.
- Never call REPLAY/IMPORT data LIVE.
- Do not claim a global narrative origin.
- If only one platform returned data, acknowledge the coverage warning rather than hiding it.
- If an external provider fails, continue using the deterministic Demo workspace instead of debugging on stage.
- Use **Light** theme by default; switch only if the venue/projector makes Dark easier to read.

# If the jury asks: “Is X / Instagram 100% live without payment?”

Answer:

> No system can honestly promise unrestricted free live search on platforms that do not expose such access. NEXUS handles that correctly: official connector when authorized access exists, permitted public fallback where available, and import/replay otherwise. The analytics pipeline stays functional and the acquisition mode is visible to the analyst.

# If the jury asks: “Then why is this useful to NTRO?”

Answer:

> Because acquisition providers can change, but the intelligence problem does not. A government-approved API, enterprise agreement, archive, data lake or future provider can feed the same normalized event layer without rewriting sentiment, narrative tracking, graph analysis or analyst workflows.

# If the jury asks: “What is the main innovation?”

Answer:

> Evidence-backed narrative lineage. We connect chronology, semantic variants, sentiment movement and influence topology, then preserve the witness evidence and avoid making claims beyond the collected coverage.

# If the jury asks: “How is it different from Brandwatch / Talkwalker?”

Answer:

> Commercial tools are strong monitoring products. NEXUS focuses on a transparent intelligence pipeline: source-mode truthfulness, explainable trend decomposition, narrative lineage, graph-based bridge analysis, privacy-conscious audience signals and evidence traceability that lets an analyst inspect why the system reached a conclusion.
