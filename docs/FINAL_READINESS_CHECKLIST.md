# NEXUS — Final SIH Readiness Checklist

Use this checklist on the **actual demo laptop and venue network**. NEXUS is ready for the slot only when every **BLOCKER** item passes.

## BLOCKER — repository / runtime

- [ ] `git switch build/ps152-complete` is the active branch unless the final build has intentionally been merged elsewhere.
- [ ] `git pull origin build/ps152-complete` completes before final validation.
- [ ] `.\.venv\Scripts\python.exe .\scripts\preflight.py` exits with `PRE-FLIGHT PASSED`.
- [ ] Backend pytest suite passes inside preflight.
- [ ] Frontend `typecheck` passes inside preflight.
- [ ] Frontend production build passes inside preflight.
- [ ] `scripts\start_demo.bat` starts FastAPI and React without manual code edits.
- [ ] `http://127.0.0.1:8000/health` returns `version: 0.4.0`.
- [ ] `http://127.0.0.1:5173` loads the analyst console.
- [ ] No `.env` secret file is committed; only `.env.example` is tracked.

## BLOCKER — modern UI / presentation

- [ ] App opens in **Light** mode by default on a clean browser profile.
- [ ] Light ↔ Dark theme switch works without unreadable labels/cards.
- [ ] Browser reload preserves the selected theme.
- [ ] No topbar/sidebar/card overlap at the laptop's presentation resolution.
- [ ] Browser zoom is 90–100%; no horizontal page scrollbar appears at normal desktop width.
- [ ] **Live Intelligence Pulse** renders on Overview.
- [ ] Pulse shows LIVE evidence, platform coverage, connector readiness and latest evidence time.
- [ ] A one-platform workspace visibly shows the coverage-limited warning.
- [ ] `Ctrl+K` / `Cmd+K` focuses the global search box.
- [ ] **Connections** opens as a drawer and supports High Priority / Ready / Needs Setup filters.
- [ ] **Free Sources** opens as a drawer and does not cause page overlap.
- [ ] Escape closes each utility drawer.
- [ ] Source actions refresh the workspace in-place rather than visibly reloading the browser.
- [ ] If a frontend render failure is intentionally simulated during development, the controlled NEXUS recovery screen appears instead of a blank page.

## BLOCKER — Telegram / primary live demo

- [ ] `NexusSIHDemo` is public and reachable from the demo laptop without a Telegram login requirement for the public preview.
- [ ] The channel contains at least one recent post matching the chosen demo query.
- [ ] `.env` contains `TELEGRAM_PUBLIC_CHANNELS=NexusSIHDemo` or relies on the built-in/demo fallback intentionally.
- [ ] Searching that keyword with **Fresh Search** returns at least one Telegram result on venue internet.
- [ ] **Posts / Explorer** → Telegram filter shows the expected channel post.
- [ ] The selected Telegram post is labelled `LIVE` and retains timestamp/provenance.
- [ ] Optional Bot API token, if used, remains only in local `.env` and is never shown or committed.

## BLOCKER — Posts / Explorer

- [ ] Platform chips show the sources currently present in the workspace.
- [ ] LIVE / REPLAY / IMPORT filters work.
- [ ] Local post search filters text/authors/hashtags without a backend request.
- [ ] Newest / Oldest sorting works.
- [ ] Selected post opens without layout overflow for long text.
- [ ] YouTube evidence renders an embedded player when the source exposes a video.
- [ ] Explicit public X Post evidence renders the official oEmbed card when available.
- [ ] Provenance shows connector, search query/session, source event ID and internal evidence ID.
- [ ] Open-original link appears only for a usable public source URL.

## BLOCKER — PS26152 requirement coverage

- [ ] Sentiment vector is visible at event level and on Timeline.
- [ ] Audience/demographic vector is visible as aggregate privacy-conscious slices.
- [ ] Trend/narrative vector shows explainable trend decomposition.
- [ ] Link/network vector shows nodes, edges, centrality/community roles.
- [ ] Every evidence record retains acquisition mode: `LIVE`, `REPLAY`, or `IMPORT`.
- [ ] Narrative detail says **earliest observed** rather than claiming absolute internet origin.
- [ ] Network roles are described as graph topology, never intent/guilt.

## BLOCKER — source truth / resilience

- [ ] At least one real live/public source is tested on venue internet before the slot.
- [ ] Telegram is the preferred primary proof.
- [ ] YouTube zero-key path is tested or deliberately omitted from the live on-stage step.
- [ ] Bluesky is treated as useful bonus zero-key coverage, not a dependency.
- [ ] X status remains truthful when official developer access/credits are absent.
- [ ] Free X mode is described only as explicit public Post URL oEmbed / configured permitted bridge — not unrestricted keyword search.
- [ ] Instagram status is truthful when Meta authorization/public-profile access is unavailable.
- [ ] Failure of one external connector does not erase evidence returned by successful connectors.
- [ ] Deterministic Demo / IMPORT remains available as offline fallback.

## BLOCKER — evidence / trust

- [ ] Evidence ledger rows open the exact selected post.
- [ ] `GET /api/certificates` returns certificate summaries when evidence supports them.
- [ ] A narrative certificate returns `CERTIFIED` or explicit `ABSTAIN` rather than fabricating confidence.
- [ ] Evidence certificate includes witness/evidence references and deterministic integrity metadata where implemented.
- [ ] Demographics UI does not expose guessed protected traits for named individuals.

## BLOCKER — clean submission ZIP

Run:

```bat
scripts\export_submission.bat
```

- [ ] Exporter refuses to run if tracked project files have uncommitted changes.
- [ ] ZIP filename contains the Git commit SHA.
- [ ] ZIP contains `START_HERE.md`, frontend, backend, scripts, docs and `.env.example`.
- [ ] ZIP does **not** contain `.env`, `.venv`, `node_modules`, local DB files or credentials.
- [ ] Extract the final ZIP into a temporary folder once and inspect its structure before submission.

## SHOULD PASS — stage preparation

- [ ] Close unrelated browser tabs, notifications and messaging popups.
- [ ] Keep FastAPI docs in a second tab only for technical questions.
- [ ] Keep `docs/JURY_DEMO_5_MIN.md` on a teammate's phone/laptop, not projected.
- [ ] Keep **Connections** and **Free Sources** drawers closed when beginning the presentation.
- [ ] Use a controlled demo query whose expected Telegram evidence you already verified.
- [ ] Do not test every source live on stage.
- [ ] Keep mobile hotspot as backup for venue Wi-Fi.
- [ ] Keep a deterministic imported/replay dataset ready.
- [ ] Record a short screen capture of the working live demo as disaster-recovery proof if time permits.

## Optional gateway

The Spring gateway is not required for the normal verified demo. Only if the team intentionally uses it:

```bat
cd backend-java
mvn -B test package
```

## Final rule

If an external platform fails during judging, **do not debug the vendor on stage**. Show the truthful connector state, acknowledge the bounded coverage, continue with successful LIVE evidence or the deterministic Demo workspace, and prove the four analytics vectors plus evidence traceability. A resilient system that reports its limitations is a stronger engineering demonstration than a brittle integration that pretends every platform is always available.
