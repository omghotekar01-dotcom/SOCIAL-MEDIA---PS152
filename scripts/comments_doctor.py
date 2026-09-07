from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend-ai"
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402

SETTINGS = get_settings()
FAILURES = 0
WARNINGS = 0


def status(label: str, state: str, detail: str) -> None:
    global FAILURES, WARNINGS
    print(f"[{state}] {label}: {detail}")
    if state == "FAIL":
        FAILURES += 1
    elif state == "WARN":
        WARNINGS += 1


def youtube_id(value: str) -> str | None:
    clean = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", clean):
        return clean
    try:
        parsed = urlparse(clean)
        if parsed.netloc.endswith("youtu.be"):
            candidate = parsed.path.strip("/").split("/")[0]
            return candidate if len(candidate) == 11 else None
        if "youtube.com" in parsed.netloc:
            if parsed.path == "/watch":
                candidate = parse_qs(parsed.query).get("v", [""])[0]
                return candidate if len(candidate) == 11 else None
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) >= 2 and parts[0] in {"shorts", "live", "embed"} and len(parts[1]) == 11:
                return parts[1]
    except Exception:
        pass
    return None


def _first_telegram_channel() -> str:
    raw = (SETTINGS.telegram_public_channels or "NexusSIHDemo").split(",", 1)[0].strip()
    raw = raw.split("||", 1)[0].strip().lstrip("@")
    return raw or "NexusSIHDemo"


def telegram_check() -> None:
    token = SETTINGS.telegram_bot_token.strip()
    if not token:
        status("Telegram Bot API", "FAIL", "TELEGRAM_BOT_TOKEN is blank in .env; public-channel preview can still work, but linked discussion comments need the Bot API path")
        return

    base = f"https://api.telegram.org/bot{token}"
    channel = _first_telegram_channel()
    try:
        with httpx.Client(timeout=12) as client:
            me = client.get(f"{base}/getMe")
            webhook = client.get(f"{base}/getWebhookInfo")
    except Exception as exc:
        status("Telegram", "FAIL", f"network request failed: {exc}")
        return

    if me.status_code != 200 or not me.json().get("ok"):
        status("Telegram token", "FAIL", "bot token was rejected by Telegram")
        return

    user = me.json().get("result") or {}
    bot_id = user.get("id")
    username = user.get("username") or "unknown"
    can_read_all = bool(user.get("can_read_all_group_messages"))
    status("Telegram token", "PASS", f"@{username} authenticated")
    status(
        "Telegram group privacy",
        "PASS" if can_read_all else "WARN",
        "bot-wide privacy mode appears disabled" if can_read_all else (
            "privacy mode appears enabled. Admin bots can still receive all messages in groups where they are admins; "
            "otherwise disable Group Privacy in BotFather and re-add the bot."
        ),
    )

    if webhook.status_code == 200 and webhook.json().get("ok"):
        info = webhook.json().get("result") or {}
        url = str(info.get("url") or "")
        if url:
            status("Telegram polling", "FAIL", "an active webhook is configured; getUpdates will return 409 until the webhook is removed")
        else:
            status("Telegram polling", "PASS", "no active webhook blocks getUpdates")
    else:
        status("Telegram polling", "WARN", "could not read webhook status")

    allowed = SETTINGS.telegram_allowed_chat_ids.strip()
    if allowed:
        status("Telegram allowed chats", "WARN", f"filter is enabled: {allowed}. Ensure BOTH the channel and linked discussion-group IDs are included")
    else:
        status("Telegram allowed chats", "PASS", "no chat-id filter; all bot-visible demo chats are eligible")

    # Verify the controlled channel and its linked discussion group where Telegram
    # exposes them through getChat. This does not consume messages/updates.
    channel_ref = f"@{channel}"
    try:
        with httpx.Client(timeout=12) as client:
            channel_resp = client.get(f"{base}/getChat", params={"chat_id": channel_ref})
    except Exception as exc:
        status("Telegram configured channel", "WARN", f"could not inspect {channel_ref}: {exc}")
        return

    if channel_resp.status_code != 200 or not channel_resp.json().get("ok"):
        status("Telegram configured channel", "WARN", f"Bot API could not inspect {channel_ref}. Check TELEGRAM_PUBLIC_CHANNELS and bot/channel access")
        return

    channel_info = channel_resp.json().get("result") or {}
    channel_id = channel_info.get("id")
    linked_chat_id = channel_info.get("linked_chat_id")
    status("Telegram configured channel", "PASS", f"{channel_ref} resolved as chat {channel_id}")

    if not linked_chat_id:
        status("Telegram linked discussion", "FAIL", "Telegram reports no linked_chat_id for the configured channel. Link a discussion group before testing channel comments")
        return

    status("Telegram linked discussion", "PASS", f"linked discussion chat detected: {linked_chat_id}")
    if not bot_id:
        status("Telegram discussion bot membership", "WARN", "bot id unavailable from getMe")
        return

    try:
        with httpx.Client(timeout=12) as client:
            member_resp = client.get(
                f"{base}/getChatMember",
                params={"chat_id": linked_chat_id, "user_id": bot_id},
            )
    except Exception as exc:
        status("Telegram discussion bot membership", "WARN", f"could not inspect bot membership: {exc}")
        return

    if member_resp.status_code != 200 or not member_resp.json().get("ok"):
        status("Telegram discussion bot membership", "FAIL", "bot membership in the linked discussion group could not be confirmed")
        return

    membership = member_resp.json().get("result") or {}
    member_state = str(membership.get("status") or "unknown")
    if member_state in {"administrator", "creator"}:
        status("Telegram discussion bot membership", "PASS", f"bot is {member_state}; ordinary discussion comments should be visible")
    elif member_state in {"member", "restricted"}:
        state = "PASS" if can_read_all else "WARN"
        status(
            "Telegram discussion bot membership",
            state,
            f"bot is {member_state}; {'privacy mode is disabled' if can_read_all else 'make it admin or disable privacy for reliable ordinary-comment visibility'}",
        )
    else:
        status("Telegram discussion bot membership", "FAIL", f"bot status is {member_state}; add/re-add it to the linked discussion group")


def youtube_check(target: str | None) -> None:
    key = SETTINGS.youtube_api_key.strip()
    if not key:
        status("YouTube", "FAIL", "YOUTUBE_API_KEY is blank. Reliable public commentThreads ingestion requires YouTube Data API v3")
        return

    video_id = youtube_id(target or "") if target else None
    if not video_id:
        video_id = "dQw4w9WgXcQ"
        status("YouTube target", "INFO", "no exact video supplied; using a public video only to test API connectivity")

    try:
        with httpx.Client(timeout=15) as client:
            video = client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"key": key, "part": "snippet,statistics,status", "id": video_id},
            )
            comments = client.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params={"key": key, "part": "snippet,replies", "videoId": video_id, "textFormat": "plainText", "maxResults": 5, "order": "time"},
            )
    except Exception as exc:
        status("YouTube", "FAIL", f"network request failed: {exc}")
        return

    if video.status_code == 403:
        status("YouTube key", "FAIL", "403 from videos.list — check YouTube Data API v3 enablement, API-key restriction and quota")
        return
    if video.status_code >= 400:
        status("YouTube key", "FAIL", f"videos.list returned HTTP {video.status_code}: {video.text[:180]}")
        return
    items = video.json().get("items", [])
    if not items:
        status("YouTube target", "FAIL", f"video {video_id} was not returned by the API")
        return

    stats = items[0].get("statistics") or {}
    privacy = str((items[0].get("status") or {}).get("privacyStatus") or "unknown")
    status("YouTube key", "PASS", "YouTube Data API v3 request succeeded")
    status("YouTube video", "PASS", f"video {video_id} accessible ({privacy}); API reports {stats.get('commentCount', 'unknown')} top-level comments")

    if comments.status_code == 200:
        rows = comments.json().get("items", [])
        status("YouTube comments", "PASS", f"commentThreads.list returned {len(rows)} thread(s) in the probe")
        if rows:
            first = rows[0]
            snippet = first.get("snippet") or {}
            total_replies = int(snippet.get("totalReplyCount") or 0)
            inline_replies = len(((first.get("replies") or {}).get("comments") or []))
            if total_replies > inline_replies:
                top_id = str(((snippet.get("topLevelComment") or {}).get("id") or ""))
                if top_id:
                    try:
                        with httpx.Client(timeout=15) as client:
                            replies = client.get(
                                "https://www.googleapis.com/youtube/v3/comments",
                                params={"key": key, "part": "snippet", "parentId": top_id, "textFormat": "plainText", "maxResults": 5},
                            )
                        if replies.status_code == 200:
                            status("YouTube nested replies", "PASS", f"comments.list(parentId) returned {len(replies.json().get('items', []))} reply row(s) in the probe")
                        else:
                            status("YouTube nested replies", "WARN", f"comments.list(parentId) returned HTTP {replies.status_code}; top-level comments still work")
                    except Exception as exc:
                        status("YouTube nested replies", "WARN", f"reply probe failed: {exc}")
            else:
                status("YouTube nested replies", "INFO", "first sampled thread does not require an additional reply-page request")
    elif comments.status_code == 403:
        try:
            reasons = ((comments.json().get("error") or {}).get("errors") or [])
            reason = str(reasons[0].get("reason") if reasons else "forbidden")
        except Exception:
            reason = "forbidden"
        if reason == "commentsDisabled":
            status("YouTube comments", "WARN", "comments are disabled on this specific video; use another public comment-enabled video")
        else:
            status("YouTube comments", "FAIL", f"commentThreads.list returned 403 ({reason})")
    else:
        status("YouTube comments", "FAIL", f"commentThreads.list returned HTTP {comments.status_code}: {comments.text[:180]}")


def main() -> int:
    print("NEXUS COMMENTS DOCTOR — Telegram + YouTube\n")
    target = sys.argv[1] if len(sys.argv) > 1 else None
    telegram_check()
    print()
    youtube_check(target)
    print("\nUsage with an exact YouTube video for the strongest test:")
    print(r"  .\.venv\Scripts\python.exe .\scripts\comments_doctor.py https://www.youtube.com/watch?v=VIDEO_ID")
    print("\nThis diagnostic never prints your bot token or YouTube API key.")
    print(f"\nSUMMARY: {FAILURES} failure(s), {WARNINGS} warning(s).")
    # This is an explicit operator diagnostic, so a confirmed failure should be
    # machine-visible too. Warnings do not fail the command.
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
