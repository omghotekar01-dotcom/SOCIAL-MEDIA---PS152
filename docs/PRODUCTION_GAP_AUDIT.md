# NEXUS — Production Gap Audit

## Current maturity

NEXUS is an advanced SIH prototype / MVP, not a claim of production deployment inside an intelligence agency. The analytics core, evidence provenance, deterministic replay, public/official connector abstractions, alerting, network analysis, aggregate demographics and analyst UI are implemented. Production hardening remains a separate engineering phase.

## P0 — required before SIH jury demo

- Local preflight must pass on the actual presentation laptop.
- `start_demo.bat` must start FastAPI, seed demo data and launch React cleanly.
- Connection Center must clearly distinguish READY/LIVE/CREDENTIALS_REQUIRED/DEGRADED.
- At least two real live sources should be demonstrated when venue internet permits it.
- Telegram public should have a team-controlled public channel test case.
- YouTube zero-key or official API should have a real search query.
- X and Instagram must never be presented as unrestricted free live search when access is not provisioned.
- Offline replay/import fallback must be ready for every jury-critical screen.
- Alerts, trends, network, demographics and evidence certificates must all render from the deterministic dataset.
- Final local doctor output should be saved before the event.

## P1 — required for a polished startup / pilot MVP

- Case/workspace model: analysts create an investigation case with keywords, sources and time window.
- Saved searches and source-specific query configuration.
- Cost-aware source router: free/public sources first, premium connectors activated on thresholds.
- Collection queue with retry/backoff, per-source rate budget and run history.
- Cross-source duplicate / near-duplicate detection beyond platform-native IDs.
- Connector telemetry: latency, quota usage, last success, last error, records received.
- Better multilingual NLP evaluation and model selection for Indian languages.
- Explicit confidence calibration per analytics output.
- Search/filter across raw evidence, narratives, authors and time windows.
- Analyst annotations, bookmarks and case notes.
- One-click executive/investigation report generation.
- Better network layout for large graphs and narrative-specific filtering.
- Source-level cost estimate / acquisition budget dashboard.

## P2 — required for real government/enterprise production

- Authentication, RBAC and least-privilege analyst/admin roles.
- SSO/identity-provider integration appropriate to the deployment environment.
- PostgreSQL or equivalent production database; schema migrations and backups.
- Encrypted secret storage; no production tokens in plain `.env` files.
- Immutable audit logging of logins, searches, exports and connector actions.
- Encryption in transit and at rest; key-management integration.
- Deployment packaging, health probes, service supervision and controlled upgrades.
- High availability, queueing, horizontal worker scale and disaster recovery.
- Data-retention/deletion policies and legal/compliance controls.
- Formal API-provider agreements / enterprise feeds for high-volume commercial platforms.
- Security testing, dependency scanning, penetration testing and threat modeling.
- Monitoring/observability: metrics, traces, structured logs and alerting.
- Model governance: evaluation datasets, drift tests, false-positive tracking and approval gates.

## Non-negotiable truthfulness

A data-source limitation is not an analytics failure. NEXUS is designed so that official APIs, approved enterprise feeds, public endpoints, permitted bridges, authorized exports and replay data normalize into the same canonical event contract. Production deployment must use access methods authorized by the platform/data owner and the deploying organization.

## SIH target definition of done

For SIH, call the project complete only when:

1. Preflight passes on the demo laptop.
2. Deterministic demo works with the internet disconnected.
3. At least two genuine live connectors are demonstrated when internet is available.
4. Every event visibly discloses LIVE / IMPORT / REPLAY provenance.
5. All four PS vectors are provable in the UI: sentiment, demographics, trend/narrative, link/network analysis.
6. API cost/access limitations have a credible architecture answer: vendor-agnostic ingestion + selective premium collection.
7. No judge-facing feature depends on an unapproved X/Meta credential.
