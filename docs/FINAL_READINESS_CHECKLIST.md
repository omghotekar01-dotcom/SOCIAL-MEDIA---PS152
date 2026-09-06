# NEXUS — Final SIH Readiness Checklist

Use this checklist on the demo laptop. The project is ready for the slot when every **BLOCKER** item passes.

## BLOCKER — repository/runtime

- [ ] `python scripts\preflight.py` exits with `PRE-FLIGHT PASSED`.
- [ ] `scripts\start_demo.bat` starts FastAPI and React without manual code edits.
- [ ] `http://127.0.0.1:8000/health` returns `version: 0.3.0`.
- [ ] `http://127.0.0.1:5173` loads the analyst console.
- [ ] **Seed Demo** produces deterministic events and multiple narratives.
- [ ] Overview, Timeline, Trends, Network, Demographics, Alerts and Evidence pages load.
- [ ] No `.env` secret file is committed; only `.env.example` is in Git.
- [ ] Git working tree used for the demo corresponds to the final merged commit.

## BLOCKER — PS26152 requirement coverage

- [ ] Sentiment vector visible with event-level and timeline output.
- [ ] Audience/demographic vector visible as aggregate privacy-safe slices.
- [ ] Trend/narrative vector visible with explainable trend decomposition.
- [ ] Link/network vector visible with nodes, edges, PageRank/betweenness/community roles.
- [ ] Every evidence record shows its acquisition mode: `LIVE`, `REPLAY`, or `IMPORT`.
- [ ] Narrative detail uses `earliest observed` language, never absolute origin claims.

## BLOCKER — live source resilience

- [ ] At least one zero-key live source has been tested on venue internet before the slot.
- [ ] Recommended: Telegram public channel ingestion works with a known public channel.
- [ ] Recommended: Bluesky search works for the chosen demo query.
- [ ] YouTube zero-key path has been tested or intentionally skipped in the live stage demo.
- [ ] X connector status is truthful when no bearer token/public bridge is configured.
- [ ] Instagram connector status is truthful when Meta/public-profile access is unavailable.
- [ ] A failed external connector does not break seeded analytics.

## BLOCKER — evidence/trust

- [ ] `GET /api/certificates` returns certificate summaries after demo seed.
- [ ] A narrative certificate returns `CERTIFIED` or explicit `ABSTAIN`.
- [ ] Evidence certificate includes snapshot hash, algorithm hash and witness posts.
- [ ] Graph labels are explained as topology, not accusation/identity attribution.
- [ ] Demographic UI does not expose inferred protected traits for named individuals.

## SHOULD PASS — tests

From `backend-ai`:

```bat
..\.venv\Scripts\python -m pytest -q
```

From `frontend`:

```bat
npm run build
```

Optional Spring gateway:

```bat
cd backend-java
mvn -B test package
```

- [ ] Python tests pass.
- [ ] Python `compileall` passes.
- [ ] React/TypeScript production build passes.
- [ ] Spring gateway package passes if the team plans to use it during the presentation.

## SHOULD PASS — demo preparation

- [ ] Browser zoom 90–100%, no devtools visible.
- [ ] Close unrelated tabs/notifications.
- [ ] Keep FastAPI docs in a second tab for certificate/API questions.
- [ ] Keep `docs/JURY_DEMO_5_MIN.md` open on a teammate's phone, not on the projector.
- [ ] Use a controlled fictional/demo narrative for deterministic presentation.
- [ ] Do not test all connectors live on stage; one or two is enough to prove the architecture.
- [ ] Keep hotspot/mobile data as backup for venue Wi-Fi.

## OPTIONAL polish

- [ ] Add project logo/favicon.
- [ ] Add a dedicated Evidence Certificate UI card if presentation time permits.
- [ ] Add official API credentials only if already provisioned; do not spend the last hours fighting access approval.
- [ ] Prepare one exported JSON dataset as a backup import file.
- [ ] Record a 30–60 second screen capture of the working live demo as disaster recovery evidence.

## Final rule

If an external service fails during judging, **do not debug the vendor**. Show the connector state, state that the source is unavailable/rate-limited, seed or use existing evidence, and continue through the four analytics vectors. A resilient system that tells the truth is a stronger engineering demonstration than a brittle scraper that pretends it always works.
