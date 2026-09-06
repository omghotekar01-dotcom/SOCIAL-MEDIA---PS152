# NEXUS v0.3 — Free / Official Social Source Matrix

This document is the operational truth table for SIH26152. NEXUS does **not** claim that every commercial platform exposes unrestricted free search APIs. The framework keeps all four analytics vectors operational even when a vendor restricts access, and every record is labelled `LIVE`, `REPLAY`, or `IMPORT`.

## Platform matrix

| Platform | Zero/near-zero-cost path in NEXUS | Official/richer path | What works without paid API access | Known limitation | Jury recommendation |
|---|---|---|---|---|---|
| Telegram | Public channel preview `https://t.me/s/<channel>` | Telegram Bot API; optional MTProto credentials | Public channel posts, timestamps, views, URLs; bot-visible authorized chats | Private/restricted channels are never bypassed | Best live source: create/use a public demo channel and ingest it live |
| YouTube | `yt-dlp` public search metadata | YouTube Data API v3 free quota | Public video titles/descriptions/metadata and engagement when exposed | Zero-key path is metadata-focused; comments are richer through Data API | Use zero-key metadata live; add free Data API key if available |
| X / Twitter | Configurable permitted RSS/public bridge + JSON/import/replay | X API v2 recent search | Full downstream analytics from imported/public-bridge records | There is no reliable unrestricted free official recent-search API; bridge availability varies | Demonstrate connector health + X replay/import unless official access is already available |
| Instagram | Best-effort Instaloader public-profile path + optional public bridge/import | Meta Graph API for authorized professional account | Public-profile captions/metadata only when Instagram permits unauthenticated access | Instagram frequently rate-limits or blocks anonymous collection; private/login content is out of scope | Use authorized Meta access if ready; otherwise public fallback + deterministic replay |
| Facebook | Import/replay | Meta Graph API for authorized Page | Full analytics from supplied public export | Stable broad public search is not available without approved access | Optional source; do not make the core demo depend on it |
| Bluesky | Public AT Protocol search | Same public protocol | Public search/posts/engagement; no API key | Public endpoint availability/rate limits still apply | Excellent second zero-key live source |
| Reddit | Public JSON search where permitted | OAuth app credentials | Low-volume public search where network policy permits it | Reddit can return 403/429 depending on client/network | Use as bonus live source; keep import fallback |
| Mastodon | Public instance API search | Instance-specific authenticated API | Public statuses where the chosen instance permits unauthenticated search | Policy varies by instance | Bonus live source; switch `MASTODON_BASE_URL` if required |

## Core rule

A platform restriction must **never** break the SIH demonstration.

The data path is:

```text
Official API / free public endpoint / permitted bridge / import / replay
                              |
                              v
                  canonical SocialEvent
                              |
                              v
          sentiment + audience + trends + network
                              |
                              v
             evidence-backed analyst console
```

The analytics engine is source-agnostic. Switching from an official connector to a free public connector or import does not change the four required analytics pipelines.

## Recommended jury source setup

Use these in order:

1. **Telegram public channel** — completely zero-key and easy to control live.
2. **Bluesky public search** — zero-key cross-platform live evidence.
3. **YouTube zero-key search** — public video metadata; use Data API key for comments if available.
4. **X** — official API only if already provisioned; otherwise show deterministic replay/import and connector status honestly.
5. **Instagram** — official Meta access if already provisioned; otherwise run public-profile fallback and keep replay ready.

This gives the jury both a genuine live ingestion demonstration and a resilient deterministic demonstration.

## Environment variables

```env
# Official X
X_BEARER_TOKEN=
X_MAX_RESULTS_PER_RUN=50
X_MAX_PAGES_PER_RUN=2

# Optional permitted X public RSS bridge
# Example shape only; the team must supply an endpoint it is allowed to use.
X_PUBLIC_RSS_URL_TEMPLATE=

# Telegram official bot mode (public preview mode needs no key)
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_CHAT_IDS=

# YouTube official free-quota mode (yt-dlp mode needs no key)
YOUTUBE_API_KEY=

# Meta official mode
META_ACCESS_TOKEN=
META_INSTAGRAM_ACCOUNT_ID=
META_FACEBOOK_PAGE_ID=

# Optional Instagram bridge
INSTAGRAM_PUBLIC_RSS_URL_TEMPLATE=

# Mastodon public instance
MASTODON_BASE_URL=https://mastodon.social
```

## What `LIVE` means

`LIVE` means the event was fetched from a currently reachable public/authorized source during the run. It does **not** mean the connector is official. The API response includes a `connector` field such as:

- `official_x_api_v2`
- `telegram_public_preview`
- `telegram_bot_api`
- `youtube_data_api_v3`
- `yt_dlp_public_metadata`
- `meta_graph_api`
- `instaloader_public_profile`
- `public_atproto`
- `public_json`
- `public_instance_api`
- `configured_public_bridge`

The UI and evidence ledger retain the source mode so replay/import can never be mistaken for live data.

## Security and ethics guardrails

- Public or explicitly authorized sources only.
- No login bypass, credential theft, private-account access, CAPTCHA evasion, stealth proxy rotation, or scraping designed to defeat access controls.
- Demographic analytics are aggregate/privacy-safe; do not infer sensitive protected traits about named individuals.
- Graph labels such as `Bridge Node` or `High Reach Node` describe observed topology, not guilt, intent, extremism, or identity.
- `earliest observed` means earliest in the collected dataset, not absolute internet origin.
- Connector failures must surface as `CREDENTIALS_REQUIRED`, `PERMISSION_REQUIRED`, `RATE_LIMITED`, `DEGRADED`, or `ERROR` rather than silently fabricating data.
