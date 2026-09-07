# NEXUS UI / PRODUCT GUIDE

## Design direction

NEXUS uses a light-first analyst-console design with a complete dark-mode alternative. The interface is intentionally closer to a production social-intelligence product than a college-project dashboard: restrained surfaces, consistent spacing, explicit source truth and dense data only where analysts need it.

## Primary shell

- **Light mode is default**; dark mode is persisted locally.
- The top bar contains global topic search and the primary Fresh Search action.
- `Ctrl+K` / `Cmd+K` focuses global search.
- Secondary source configuration lives in floating **Connections** and **Free Sources** drawers instead of permanently consuming screen space.
- Responsive guardrails prevent topbar, sidebar, badges and long evidence text from overlapping on common laptop widths.

## Overview

The **Live Intelligence Pulse** shows four immediate readiness signals:

1. LIVE evidence count.
2. Distinct platform coverage.
3. Ready/live connector count.
4. Timestamp of the latest observed evidence.

If a populated workspace contains only one platform, NEXUS visibly warns that cross-platform conclusions would be under-covered.

The normal KPI layer then shows observed events, narratives, rising narratives and evidence alerts.

## Posts / Explorer

The explorer is built for actual investigation rather than a static feed.

Analysts can:

- filter by platform;
- filter by `LIVE`, `REPLAY` or `IMPORT`;
- search within already-collected post text, authors, hashtags, mentions and topic terms;
- switch newest/oldest ordering;
- inspect source media / YouTube embeds / X oEmbed cards;
- inspect engagement and NLP analysis;
- inspect exact connector, search session, event IDs and provenance;
- open the original public source when a valid source URL exists.

For smooth rendering the result rail shows up to 250 matching records at once while the full evidence set remains in the workspace.

## Connections drawer

The Connection Center supports readiness filters:

- All
- High priority
- Ready
- Needs setup

Each card separates the **official connector** from the **free/fallback path**, avoiding misleading claims when official credentials are absent.

## Free Source Lab

The Free Source Lab supports a clean multi-source Fresh Mix and per-source append operations. It includes:

- Telegram public monitored sources
- YouTube zero-key metadata
- Bluesky
- Reddit where permitted
- Mastodon
- Instagram authorized/public fallback paths
- explicit X public Post URL oEmbed / configured bridge
- evidence certificate verification

Source actions refresh the NEXUS workspace in-place rather than reloading the whole browser.

## Reliability UX

A React error boundary prevents one rendering exception from blanking the entire application. If a UI rendering error occurs, NEXUS shows a controlled recovery screen; stored backend evidence is not deleted.

The browser shell restores the saved theme before React renders, preventing a visible light/dark theme flash.

## Submission safety

Use:

```bat
scripts\export_submission.bat
```

The clean exporter uses `git archive`, so local `.env`, `.venv`, `node_modules` and other untracked secrets/runtime files are excluded from the submission ZIP.
