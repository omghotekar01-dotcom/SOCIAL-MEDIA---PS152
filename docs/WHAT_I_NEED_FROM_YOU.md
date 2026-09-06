# NEXUS — What I Need From You to Finish Real Integrations

This checklist separates **code work** from **account-side access**. The project can be made production-grade without exposing secrets in chat or GitHub.

## Rule zero — do not send secrets

Never paste or upload any of these into chat, screenshots, issues, or GitHub:

- API keys
- bearer tokens
- Telegram bot tokens
- Meta access tokens
- client secrets
- passwords
- browser cookies / session files
- private `.env` contents

Put secrets **only** in your local repository `.env` file. NEXUS reads them from there at runtime.

Run this safe diagnostic and share only its output when debugging:

```powershell
.\.venv\Scripts\python.exe .\scripts\doctor.py
```

It prints only READY / NEEDS SETUP states, never secret values.

---

## 1. Telegram

### Send/share with the project team
- One **public Telegram channel username** that we are allowed to use for the SIH demo.
- Whether you want Bot API continuous monitoring: YES/NO.
- If using Bot API, the **chat/channel numeric ID** may be shared if needed; it is not a secret.
- A screenshot of the BotFather setup with the token hidden is useful if setup fails.

### Keep locally in `.env`
```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_ALLOWED_CHAT_IDS=...
```

### Best demo plan
Create a controlled public demo channel, publish posts during the jury demo, and ingest them with **Telegram Public**. This works without a token.

---

## 2. YouTube

### Send/share
- The exact topic/query you want to monitor.
- Whether you created a Google Cloud project with YouTube Data API v3 enabled.
- Any quota/permission error screenshot with the API key hidden.

### Keep locally in `.env`
```env
YOUTUBE_API_KEY=...
```

The zero-key YouTube path works without this key; the official path is richer.

---

## 3. X / Twitter

### Send/share
- Whether you actually have X developer API access: YES/NO.
- Which access plan/tier you have, if any.
- The query/hashtags/accounts you want to monitor.
- Provider error screenshots with the bearer token hidden.
- If you have a permitted RSS/Atom bridge, send the **public template URL only if it contains no secret token**.

### Keep locally in `.env`
```env
X_BEARER_TOKEN=...
X_PUBLIC_RSS_URL_TEMPLATE=...
```

If no official/bridge access exists, NEXUS should use IMPORT/REPLAY for X and disclose that honestly.

---

## 4. Instagram / Meta

### Send/share
- Whether your Instagram account is Business/Creator and linked to the required Meta assets.
- Your **Instagram account ID** if available; this is normally not a secret.
- Your **Facebook Page ID** if Facebook is needed.
- Whether the Meta app is Development or Live.
- Which permissions/features have been approved.
- Screenshot of Meta Graph/API errors with the access token hidden.
- One public Instagram username and one hashtag for test cases.

### Keep locally in `.env`
```env
META_ACCESS_TOKEN=...
META_INSTAGRAM_ACCOUNT_ID=...
META_FACEBOOK_PAGE_ID=...
```

Do not depend on anonymous Instagram scraping for the final production story; it is only a best-effort fallback.

---

## 5. Bluesky / Mastodon / Reddit

### Send/share
- One topic/query for each source.
- Desired Mastodon instance if not `mastodon.social`.
- Any network error screenshot.

### Local `.env`
```env
MASTODON_BASE_URL=https://mastodon.social
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
```

Reddit OAuth credentials are optional unless the public low-volume path is restricted.

---

## 6. Demo narrative / jury scenario

Send these **non-secret** choices so the product can be polished around your real SIH story:

- Final project name: keep **NEXUS** or rename?
- Team name.
- One final investigation scenario for the jury demo.
- 3–5 keywords / hashtags to monitor.
- The platforms you want to visibly demonstrate LIVE.
- Whether internet at the SIH venue is reliable.
- Whether the demo must still work completely offline.

Recommended final architecture is **hybrid**: deterministic replay guarantees the demo, while 2–3 public/authorized sources prove live ingestion.

---

## 7. Branding / product polish

Send or upload:

- Project/team logo if you have one.
- Any official SIH/college logo you are permitted to use.
- Preferred product subtitle/tagline.
- Team member names/roles only if you want an About/Team page.
- Any UI reference screenshots you want NEXUS to resemble.

No branding asset is required for backend functionality.

---

## 8. Your laptop / runtime

Share only this safe information:

```powershell
python --version
node --version
.\.venv\Scripts\python.exe .\scripts\doctor.py
```

Also share:

- Windows version.
- Whether Maven/Java should be part of the actual jury runtime or whether we keep the simpler FastAPI + React architecture.
- Any red browser console error or backend terminal traceback.

---

## 9. What can be finished without any extra input

The codebase can be improved independently in these areas:

- professional Connection Center
- connector readiness UX
- error handling and empty states
- live/replay/import provenance
- deterministic demo/recovery mode
- evidence certificates
- alerts and trend persistence
- network-analysis visuals
- privacy-safe demographic display
- export/reporting
- startup/preflight/doctor tooling
- docs, jury script and deployment architecture
- cost-aware source routing design

The only blockers that require you are **third-party account authorization, API credentials, and the final demo/branding choices**.
