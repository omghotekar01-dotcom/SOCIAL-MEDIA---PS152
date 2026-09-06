# NEXUS — 5-Minute SIH26152 Jury Demo

Goal: prove the **four required analytics vectors** and the system's evidence discipline in one coherent story. Do not spend the demo explaining frameworks or APIs unless the jury asks.

## Before the slot

1. Run `scripts\start_demo.bat`.
2. Open `http://127.0.0.1:5173`.
3. Click **Seed Demo** once.
4. Confirm Overview shows events, multiple narratives and at least one rising/emerging narrative.
5. Keep one public Telegram channel username ready for **FREE SOURCE LAB**.
6. Keep internet available for the live source moment, but assume any external platform can fail.
7. If available, configure a YouTube Data API key and/or Telegram Bot token. They are optional.
8. Run `python scripts\preflight.py` from the repository root before leaving for the venue.

---

## 0:00–0:35 — The problem and thesis

Say:

> Social media analytics usually stops at dashboards: counts, hashtags and a sentiment pie chart. NEXUS instead reconstructs how a narrative emerges, how sentiment changes, who amplifies it, and how it moves across communities — with evidence behind every conclusion.

Point to the Overview cards.

Show that records are explicitly labelled **LIVE / REPLAY / IMPORT**.

---

## 0:35–1:20 — Live/free ingestion

Use **FREE SOURCE LAB**.

Preferred order:

1. Telegram public channel
2. Bluesky public search
3. YouTube ₹0

Trigger only one or two live sources during the demo. Do not risk the whole presentation by testing every platform in front of the jury.

Say:

> The framework is connector-independent. Telegram public channels and Bluesky can be collected with zero API keys; YouTube has a zero-key metadata path and an official free-quota API path. Restricted platforms such as X and Instagram use official credentials where available, otherwise a permitted public bridge or import/replay path. The dashboard never mislabels replay as live.

If a live source fails, **do not debug on stage**. Point to the returned connector state and continue with the seeded evidence. This actually demonstrates resilience.

---

## 1:20–2:05 — Vector 1: Sentiment + stance

Open **Timeline**.

Show:

- exact source timestamps;
- volume movement;
- positive/negative/neutral movement;
- the fact that sentiment is stored per evidence item, not just as an aggregate chart.

Say:

> We combine event-level sentiment with stance and emotion signals, then aggregate them temporally. The purpose is not simply to say 'negative'; it is to show when polarization or emotional intensity changes as a narrative spreads.

Open one evidence item if useful.

---

## 2:05–2:50 — Vector 2: Trend & narrative tracking

Open **Trends** and select the top rising narrative.

Point out:

- trend score;
- growth rate;
- burst z-score;
- author diversity;
- number of platforms;
- chronology / lineage.

Say:

> We track narratives rather than exact hashtag strings. Related wording is clustered using text similarity plus temporal, hashtag and URL evidence. The score is explainable: growth, burst deviation, author diversity, cross-platform presence, engagement and recency.

Then say this exact distinction:

> 'Earliest observed' means earliest inside the data we actually collected. We never claim absolute internet origin without evidence.

---

## 2:50–3:40 — Vector 3: Link/network analysis

Open **Network**.

Point to one **High Reach Node** and one **Bridge Node**.

Say:

> We build an observed interaction graph from replies, mentions, shared links and narrative co-amplification. PageRank identifies high-reach positions, betweenness identifies bridges, and community structure shows how information crosses groups. These labels describe network topology — they are not accusations about a person's intent.

This is where the project should visually differentiate itself from basic social-media dashboards.

---

## 3:40–4:15 — Vector 4: Privacy-safe audience demographics

Open **Demographics**.

Show:

- language distribution;
- broad geography where publicly/self-declared;
- professional-interest categories where supportable;
- k-anonymity suppression / coverage values.

Say:

> The requirement asks for demographics, but individual-level guessing would be unreliable and privacy-invasive. NEXUS therefore returns aggregate, confidence-scored audience signals and suppresses small groups. We use public/self-declared evidence rather than inventing sensitive traits about users.

---

## 4:15–4:45 — Evidence certificate / trust layer

Open the certificate endpoint in FastAPI docs if there is no dedicated UI card yet:

`GET /api/certificates`

or

`GET /api/certificates/narrative/{narrative_id}`

Say:

> For higher-impact conclusions, NEXUS creates a replayable evidence certificate containing witness posts, source hashes, algorithm configuration, coverage and a deterministic snapshot hash. If the minimum evidence requirements are not met, the decision is ABSTAIN rather than overclaiming.

This is a strong research/paper-quality differentiator.

---

## 4:45–5:00 — Closing

Say:

> So the output is not 'social media is negative today.' The output is: this narrative appeared at this observed time, accelerated for these measurable reasons, moved through these communities, produced this sentiment shift, and these source records prove the conclusion. The entire core demo runs locally for essentially zero cost, while official platform credentials can be plugged in whenever richer access is available.

Stop there.

---

# If the jury asks: "Is X/Instagram 100% live without payment?"

Answer:

> No system can honestly promise unrestricted free live search on platforms that do not expose such an API. Our architecture handles that correctly: official connector when access exists, permitted public fallback where available, and import/replay otherwise. The analytics pipeline stays fully functional and the UI discloses the acquisition mode. We chose reliability and evidence integrity over pretending a restricted API is free.

# If the jury asks: "Then why is this still useful to NTRO?"

Answer:

> Because acquisition changes constantly, but the intelligence problem does not. NEXUS separates connectors from the normalized event and analytics layers, so a government-approved API, archive, data lake or future enterprise feed can be swapped in without rewriting sentiment, trends, graph analysis or analyst workflows.

# If the jury asks: "What is the main innovation?"

Answer:

> Evidence-backed narrative lineage. We do not treat a trending word as the intelligence output. We connect chronology, semantic variants, sentiment movement and influence topology, then preserve the witness evidence and abstain when confidence is insufficient.

# If the jury asks: "How is it better than Brandwatch/Talkwalker/etc.?"

Answer:

> Commercial tools are excellent monitoring products, but our research contribution is a transparent, deployable intelligence pipeline: source-mode truthfulness, explainable trend decomposition, narrative lineage, graph-based bridge analysis, privacy-safe demographics, and replayable evidence certificates. It is designed so an analyst can inspect why the system reached a conclusion.
