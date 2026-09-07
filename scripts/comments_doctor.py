from __future__ import annotations

import json
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


def status(label: str, state: str, detail: str) -> None:
    print(f"[{state}] {label}: {detail}")


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


def telegram_check() -> None:
    token = SETTINGS.telegram_bot_token.strip()
    if not token:
        status("Telegram", "FAIL", "TELEGRAM_BOT_TOKEN is blank in .env")
        return

    base = f"https://api.telegram.org/bot{token}"
    try:
        with httpx.Client(timeout=12) as client:
            me = client.get(f"{base}/getMe")
            webhook = client.get(f"{base}/getWebhookInfo")
    except Exception as exc:
        status("Telegram", "FAIL", f"network request failed: {exc}")
        return

    if me.status_code != 200 or not me.json().get("ok"):
        status("Telegram", "FAIL", "bot token was rejected by Telegram")
        return

    user = me.json().get("result") or {}
    username = user.get("username") or "unknown"
    can_read_all = bool(user.get("can_read_all_group_messages"))
    status("Telegram token", "PASS", f"@{username} authenticated")
    status(
        "Telegram group privacy",
        "PASS" if can_read_all else "WARN",
        "bot can read all group messages" if can_read_all else (
            "privacy mode appears enabled. For discussion comments, either make the bot an admin in the linked discussion group "
            "or disable privacy in BotFather and re-add the bot."
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
        status("Telegram allowed chats", "WARN", f"filter is enabled: {allowed}. Ensure BOTH the channel and linked discussion-group IDs are included.")
    else:
        status("Telegram allowed chats", "PASS", "no chat-id filter; all bot-visible demo chats are eligible")


def youtube_check(target: str | None) -> None:
    key = SETTINGS.youtube_api_key.strip()
    if not key:
        status("YouTube", "FAIL", "YOUTUBE_API_KEY is blank. Reliable public commentThreads ingestion requires YouTube Data API v3.")
        return

    video_id = youtube_id(target or "") if target else None
    if not video_id:
        # Stable public test target used only to validate the key/videos endpoint.
        video_id = "dQw4w9WgXcQ"
        status("YouTube target", "INFO", "no video URL supplied; using a public video only to test API connectivity")

    try:
        with httpx.Client(timeout=15) as client:
            video = client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"key": key, "part": "snippet,statistics,status", "id": video_id},
            )
            comments = client.get(
                "https://www.googleapis.com/youtube/v3/commentThreads",
                params={"key": key, "part": "snippet,replies", "videoId": video_id, "textFormat": "plainText", "maxResults": 5},
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
        status("YouTube target", "WARN", f"video {video_id} was not returned by the API")
        return

    stats = items[0].get("statistics") or {}
    status("YouTube key", "PASS", "YouTube Data API v3 request succeeded")
    status("YouTube video", "PASS", f"video {video_id} accessible; API reports {stats.get('commentCount', 'unknown')} comments")

    if comments.status_code == 200:
        rows = comments.json().get("items", [])
        status("YouTube comments", "PASS", f"commentThreads.list returned {len(rows)} thread(s) in the probe")
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
