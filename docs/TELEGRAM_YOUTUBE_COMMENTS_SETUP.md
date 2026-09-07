# NEXUS — Telegram + YouTube comments setup

This is the recommended SIH prototype path for obtaining real audience comments/replies.

## 1. Telegram: channel post + linked discussion comments

Telegram channel comments are messages in the channel's linked discussion group. The public `t.me/s/...` preview is useful for channel posts, but it is not the reliable comments path.

### Required setup

1. Use the public demo channel `NexusSIHDemo`.
2. In the channel, open **Manage Channel / Edit → Discussion** and link a discussion group (for example `NexusSIHDiscussion`).
3. Add the NEXUS bot as an administrator of **both** the channel and the linked discussion group. An admin bot receives group messages; alternatively disable BotFather privacy mode and re-add the bot.
4. Keep `TELEGRAM_BOT_TOKEN` in the local `.env`.
5. For the easiest prototype, leave `TELEGRAM_ALLOWED_CHAT_IDS=` blank. If you enable the filter, include both the channel id and the linked discussion-group id.
6. Restart NEXUS after editing `.env`.
7. Create a **new** channel post after the bot has access.
8. From a different Telegram account, open the post's Comments/Discussion and add several replies.
9. In NEXUS open **Social Sources → Telegram → Bot API**.

NEXUS normalizes the linked discussion auto-forward back to the original channel post and links discussion replies using `parent_event_id` + `conversation_id`, enabling Public Reaction Intelligence.

### Important

- Bot API polling is not a historical scraper. Generate new posts/comments after the bot is present.
- If `getUpdates` reports HTTP 409, an active webhook is consuming the bot updates. Remove the webhook or use a separate polling bot.
- If the bot is not an admin and BotFather privacy mode is enabled, ordinary group discussion messages may not be delivered to the bot.

## 2. YouTube: reliable public comment ingestion

For reliable YouTube comments use **YouTube Data API v3**. The zero-key yt-dlp path is metadata-oriented/best-effort and must not be treated as a guaranteed comments API.

### Required setup

1. Create/choose a Google Cloud project.
2. Enable **YouTube Data API v3**.
3. Create an API key and restrict the key to **YouTube Data API v3**.
4. Put the key only in the local `.env`:

```env
YOUTUBE_API_KEY=YOUR_KEY
YOUTUBE_MAX_VIDEOS_PER_RUN=5
YOUTUBE_MAX_COMMENTS_PER_VIDEO=30
```

5. Restart NEXUS.

### Strongest prototype test

Use an exact public YouTube video URL whose comments are visibly enabled, then click **Social Sources → YouTube → Data API**.

The official connector now accepts:

- normal search text;
- a `youtube.com/watch?v=...` URL;
- a `youtu.be/...` URL;
- a Shorts/live/embed URL;
- a raw 11-character video id.

For normal search text NEXUS inspects a wider candidate set and prioritizes videos that report comments instead of blindly choosing the newest uploads.

NEXUS collects:

- video/root evidence;
- top-level public comments;
- inline replies;
- additional replies through `comments.list(parentId=...)` when YouTube's `commentThreads` response only contains a subset;
- likes and source URLs;
- explicit `comments_state` and captured/reported comment counts in provenance.

If comments are disabled on a video, the root video is retained and marked `comments_state=disabled`; use another comment-enabled video for the prototype.

## 3. Diagnose both connectors

Run:

```powershell
.\.venv\Scripts\python.exe .\scripts\comments_doctor.py
```

For a specific YouTube target:

```powershell
.\.venv\Scripts\python.exe .\scripts\comments_doctor.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

The diagnostic checks Telegram bot authentication, webhook conflict, privacy visibility hints, allowed-chat filtering, YouTube key access, reported comment count and `commentThreads.list` availability. It never prints credentials.

## 4. Jury-safe claim

Say:

> NEXUS separates root content from audience reaction. Telegram comments are collected from bot-visible linked discussion groups, while YouTube public comments and replies are collected through the official YouTube Data API v3. Provider-disabled or inaccessible comments are disclosed rather than fabricated.

Do not claim internet-wide or unrestricted platform coverage. All conclusions remain bounded to collected evidence.
