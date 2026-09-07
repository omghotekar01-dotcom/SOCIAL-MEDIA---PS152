# NEXUS — Telegram + YouTube comments setup

This is the recommended SIH prototype path for obtaining real audience comments/replies with the simplified **Prototype Sources** control.

## 1. Telegram: channel post + linked discussion comments

Telegram channel comments are messages in the channel's linked discussion group. The public `t.me/s/...` preview is useful for channel posts, but it is not the reliable comments path.

### Required setup

1. Use the controlled demo channel `NexusSIHDemo` or another channel you manage.
2. In the channel, open **Manage Channel / Edit → Discussion** and link a discussion group (for example `NexusSIHDiscussion`).
3. Add the NEXUS bot to **both** the channel and the linked discussion group. Admin visibility is the easiest prototype setup.
4. If normal discussion messages are not delivered, use BotFather → Bot Settings → Group Privacy, disable privacy, then remove/re-add the bot to the discussion group.
5. Keep `TELEGRAM_BOT_TOKEN` only in local `.env`.
6. For the first prototype test, leave:

```env
TELEGRAM_ALLOWED_CHAT_IDS=
```

blank. If you later enable this filter, include both channel and linked discussion-group IDs.
7. Restart NEXUS after editing `.env`.
8. Create a **new** channel post after the bot has access.
9. From another Telegram account, open the channel post's Comments and create several comments/replies.
10. In NEXUS open:

```text
Prototype Sources
→ Poll Bot comments now
```

NEXUS normalizes the discussion group's automatic channel-forward back to the original channel post, then links top-level comments and replies-to-replies using `parent_event_id` + `conversation_id`. Those rows feed Public Reaction Intelligence, Timeline, Trends and Network analysis.

### Public-channel path

For root channel posts you can also use:

```text
Prototype Sources
→ Read public channel
```

This is a public-preview path for channel content. It is not presented as the Telegram Bot API and should not be relied on for linked discussion comments.

### Important

- Bot API polling is not a historical scraper. Generate new posts/comments after the bot is present.
- If `getUpdates` reports HTTP 409, an active webhook is consuming bot updates. Remove that webhook or use a separate polling bot.
- If the bot cannot see ordinary discussion messages, check admin visibility / Group Privacy and re-add it after changing privacy.
- `TELEGRAM_ALLOWED_CHAT_IDS` can accidentally block the discussion group even while allowing the channel; keep it blank for the first controlled test.

---

## 2. YouTube: official full public conversation path

For reliable YouTube comments use **YouTube Data API v3**. The zero-key yt-dlp path is metadata-oriented and must not be treated as a comments API.

### Required setup

1. Create/choose a Google Cloud project.
2. Enable **YouTube Data API v3**.
3. Create an API key and restrict that key to **YouTube Data API v3**.
4. Put the key only in local `.env`:

```env
YOUTUBE_API_KEY=YOUR_KEY
YOUTUBE_MAX_VIDEOS_PER_RUN=5
YOUTUBE_MAX_COMMENTS_PER_VIDEO=0
YOUTUBE_MAX_COMMENT_PAGES_PER_VIDEO=0
YOUTUBE_MAX_REPLY_PAGES_PER_THREAD=0
```

For an exact-video prototype request, `0` means no NEXUS-side comment/page ceiling. YouTube provider exhaustion, disabled comments, quota, rate limits or inaccessible rows remain natural boundaries.

5. Restart NEXUS.

### Strongest prototype test

Pick one exact public YouTube video with visibly enabled comments, then:

```text
Prototype Sources
→ paste exact YouTube URL
→ Load video + comments/replies
```

The active exact-video flow is:

```text
exact URL / video id
→ official videos.list metadata
→ fast first comment/reply batch
→ UI becomes usable
→ background provider-bounded exhaustive crawl
→ commentThreads.list pagination
→ comments.list(parentId=...) for additional replies
→ root metadata updated with final coverage/completion/stop reason
→ dashboard automatically refreshes
```

Supported exact inputs include:

- `youtube.com/watch?v=...`
- `youtu.be/...`
- Shorts URL
- live URL
- embed URL
- raw 11-character video ID

The root record reports:

- `reported_comment_count`
- `captured_comment_count`
- `captured_top_level_comment_count`
- `captured_reply_count`
- comment-thread pages fetched
- reply pages fetched
- `collection_complete`
- `collection_stop_reason`
- background collection state

If comments are disabled, the video itself remains valid evidence and is marked accordingly instead of showing invented comments.

### Fast-first is not a final sample cap

The first small batch exists only so the prototype is responsive. The background task continues through available public pages. NEXUS also uses a per-search generation token, so a stale crawl for an older workspace cannot attach its rows to a newer same-video search.

---

## 3. Extra public conversation coverage

Inside **Prototype Sources**:

```text
Append public mix
```

adds available evidence from:

- monitored Telegram public channel;
- Bluesky + public replies;
- Reddit + comments where access permits;
- Mastodon + public replies/context.

Use:

```text
Start 60s Live Watch
```

for recurring Telegram Bot when configured + Telegram public + Bluesky + Reddit + Mastodon collection.

---

## 4. Diagnose both primary connectors

Run:

```powershell
.\.venv\Scripts\python.exe .\scripts\comments_doctor.py
```

For a specific YouTube target:

```powershell
.\.venv\Scripts\python.exe .\scripts\comments_doctor.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

The diagnostic checks Telegram bot authentication, webhook conflict, privacy visibility hints, allowed-chat filtering, YouTube key access, reported comment count and `commentThreads.list` availability. It never prints credentials.

---

## 5. What to show after comments arrive

Use the normal analyst pages:

1. **Posts / Explorer** — root content + linked Public Reaction Intelligence.
2. **Timeline** — volume/polarity plus emotion/stance/sarcasm fluctuation.
3. **Trends** — narrative growth, momentum and keyword movement.
4. **Network** — reply/mention/co-discussion graph, KOL candidates, communities and spread chronology.
5. **Demographics** — aggregate/privacy-safe audience signals with coverage.
6. **PS26152 CORE** — one A→E requirement proof view.
7. **Evidence** — source URL/mode/provenance.

## Jury-safe claim

> NEXUS separates root content from audience reaction. Telegram comments are collected from bot-visible linked discussion groups, while YouTube public comments and replies are collected through the official YouTube Data API v3. Provider-disabled or inaccessible comments are disclosed rather than fabricated.

Do not claim internet-wide or unrestricted platform coverage. All conclusions remain bounded to collected evidence.
