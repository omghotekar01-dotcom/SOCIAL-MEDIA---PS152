# NEXUS Primary Source Setup — X + Telegram

This is the operational setup for the two SIH26152 priority sources. NEXUS must remain truthful about what is globally searchable, what is channel-scoped, and what is paid.

## 1. Telegram — primary zero-cost LIVE source

### Recommended SIH path: monitored public channels

No API key is required.

1. Create or choose public Telegram channels you are allowed to monitor.
2. Put only their public usernames in your local `.env`:

```env
TELEGRAM_PUBLIC_CHANNELS=YourDemoChannel,AnotherPublicChannel
```

3. Restart NEXUS.
4. Run `Fresh Search` for a topic.

NEXUS fetches the latest public-preview posts from every configured channel and locally filters those posts against the active query before ingestion. This means a new query does not blindly mix unrelated posts from those channels.

For the strongest live demo, create a team-controlled public channel and publish several posts around the jury scenario before/during the demonstration.

### Optional Telegram Bot API path

Create a bot through Telegram's official `@BotFather` and put the token only in local `.env`:

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_CHAT_IDS=
```

Add the bot to the authorized demo chat/channel. Bot API polling is useful for live incoming updates and continuous collection.

Do NOT commit or share the bot token.

### What Telegram does not mean here

The zero-key public-preview connector is not an unrestricted global Telegram search API. It monitors a deliberate public-channel set. NEXUS labels this scope in the evidence metadata.

## 2. X / Twitter — two honest modes

### FREE official mode: public Post URL oEmbed

No bearer token, subscription or API credit is required.

1. Find one or more public X Post URLs using X in your browser.
2. Paste the URL(s) into the Free Source Lab target field.
3. Click `+ X URL / Bridge`, or use `Fresh Free Mix` with the X URL(s) in the target field.

Examples of accepted shapes:

```text
https://x.com/example/status/1234567890
https://twitter.com/example/status/1234567890
```

NEXUS calls X's official public oEmbed endpoint, extracts the public post text/author/date for analytics, stores the official embed markup, marks the event LIVE, and renders the official X embed in Posts / Explorer.

This is a free way to ingest known public X Posts. It is NOT free global X keyword search.

### Official automatic X keyword search: optional paid path

For automatic recent-search queries, create an X developer Project/App and configure its bearer token locally:

```env
X_BEARER_TOKEN=
```

The current X API uses pay-per-use billing for reads. Keep hard per-run caps enabled and only use this connector when you intentionally want paid search coverage.

Never commit or share the bearer token.

### Optional permitted RSS/Atom bridge

If the team has a public RSS/Atom provider it is allowed to use, configure:

```env
X_PUBLIC_RSS_URL_TEMPLATE=
```

This is optional. Do not rely on a random third-party bridge for the jury demo.

## 3. Recommended jury configuration

```text
Telegram monitored public channels      LIVE / zero-key / primary
Telegram team demo channel + Bot API    LIVE / free / controlled
X explicit public Post URLs via oEmbed  LIVE / zero-key / official embed
X recent-search API                     Optional pay-per-use
YouTube zero-key                        LIVE / secondary
Bluesky public API                      LIVE / secondary
Reddit / Mastodon                       Bonus coverage
Instagram                               Authorized Meta if available; otherwise fallback/import
```

## 4. What you can safely send to a teammate/ChatGPT for debugging

Safe:
- Public Telegram channel usernames.
- Public X Post URLs.
- Search query/hashtag.
- `scripts/doctor.py` output.
- Error screenshots after hiding credentials.

Never send:
- `TELEGRAM_BOT_TOKEN`.
- `X_BEARER_TOKEN`.
- YouTube/Meta API keys or access tokens.
- Passwords, cookies, `.env`, or Telegram session files.
