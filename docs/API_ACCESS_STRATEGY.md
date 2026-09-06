# API Access Strategy — Free First, Official First

NEXUS treats platform access as an engineering constraint, not something to hide from SIH judges.

## Decision table

| Platform | SIH priority | NEXUS path | Cost/access reality | Demo strategy |
|---|---|---|---|---|
| X | Essential | Official X API v2 recent search | Current self-serve access is usage/credit based; live reads may cost money | strict per-run caps; official live connector when credits exist; otherwise clearly labelled REPLAY |
| Telegram | Essential | Official Telegram Bot API | free for developers for normal bot use | primary genuinely-live zero-cost demo source using authorized team chat/channel |
| Instagram | Desirable | Official Meta Instagram API | API itself is not a per-read purchase, but professional account/app permissions constrain scope | sync authorized professional-account media/comments; report permission state honestly |
| Facebook | Desirable | Official Facebook/Meta Page APIs | Page/app access and permissions constrain scope | sync authorized Page data; report permission/app-review state honestly |
| YouTube | Appreciable | YouTube Data API v3 | quota based | use a small number of search/comment calls and cache IDs |
| Replay/Import | resilience | local JSON | free | deterministic evaluation path; never labelled LIVE |

## X

Implementation: `x_recent_search()` in `backend-ai/app/connectors.py`.

Safety/cost controls:
- official bearer-token authentication
- small analyst-selected query
- configurable `X_MAX_RESULTS_PER_RUN`
- configurable page limit
- dedupe so an observed event is not repeatedly stored
- request only fields used by NEXUS
- explicit handling for missing credentials, permission failures, quota/rate limit and credit/access failures

NEXUS **does not claim X is free** and does not use an unofficial login scraper to evade API restrictions. This matters for a government-facing project because a demo that depends on policy-bypassing scraping is not a reliable deployment plan.

## Telegram

Implementation: `telegram_poll()`.

Default mode uses the official Bot API and is intended for:
- a group the team controls; or
- a channel/group where the bot has been explicitly authorized.

Optional `TELEGRAM_ALLOWED_CHAT_IDS` creates an allowlist.

The Bot API is the preferred live jury path because the normal platform is free for developers and requires no paid data-provider contract. Bot visibility is still bounded by Telegram’s bot/privacy behavior; NEXUS never describes it as universal Telegram access.

## YouTube

Implementation: `youtube_search()`.

The connector:
- performs a bounded video search
- retrieves accessible top-level comments
- stores comment timestamps and permalinks
- caches/deduplicates event IDs at storage level
- skips videos where comments cannot be read

The current YouTube API uses quota accounting. Therefore the configured video/comment limits are deliberately small for a hackathon demo.

## Instagram

Implementation: `meta_sync(source="instagram")`.

The code is scoped to authorized Instagram professional-account access and requests media plus accessible comments. Consumer-account/public-web scraping is not used as a fallback.

Expected failure states are part of the product:
- token missing → `CREDENTIALS_REQUIRED`
- account ID or necessary app access missing → `PERMISSION_REQUIRED`

## Facebook

Implementation: `meta_sync(source="facebook")`.

The connector is scoped to a configured Facebook Page and applicable Meta permissions. NEXUS does not claim blanket access to all public Facebook posts.

## Why replay is a feature, not a fake

External social APIs can be unavailable during a hackathon because of:
- missing app review
- temporary quota/rate limit
- paid credits
- network failure
- platform policy changes

NEXUS routes imported/replayed records through the **same normalization and analytical pipeline**, but permanently labels them `REPLAY` or `IMPORT`. This gives the jury a deterministic demonstration without making a false “live data” claim.

## API keys to obtain before the presentation

Best order:

1. **Telegram Bot token** — highest priority; free live proof.
2. **YouTube API key** — useful second live source.
3. **X bearer token + minimal credits** only if the team can obtain them within budget.
4. **Meta developer app + professional/Page access** if already available; do not risk the core demo on app review.

## Judge answer

If asked why every platform is not universally live:

> “We use official access paths because this is intended for a government-grade system. Telegram gives us a genuinely free live source. X is connected through its official API with spend controls; if credits are unavailable we use a clearly labelled replay through the same analytics pipeline. Meta integrations are permission-scoped. We prefer an honest, deployable connector model over a scraper that works for one demo and violates platform restrictions.”

## Official documentation starting points

- X developer documentation: `https://docs.x.com/`
- Telegram APIs: `https://core.telegram.org/`
- Telegram Bot API: `https://core.telegram.org/bots/api`
- YouTube Data API: `https://developers.google.com/youtube/v3/`
- Meta developer documentation: `https://developers.facebook.com/docs/`

Always re-check platform terms and pricing before a production deployment because these policies change independently of NEXUS.
