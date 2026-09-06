from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from ..config import get_settings
from ..schemas import ConnectorStatus, SocialEvent, SocialEventIn
from ..services.normalizer import normalize_many


def bot_status() -> ConnectorStatus:
    settings = get_settings()
    if not settings.telegram_bot_token:
        return ConnectorStatus(
            platform="telegram",
            state="CREDENTIALS_REQUIRED",
            detail="Set TELEGRAM_BOT_TOKEN to ingest chats/channels where the bot is present.",
            source_mode="LIVE",
        )
    return ConnectorStatus(
        platform="telegram",
        state="READY",
        detail="Official Telegram Bot API configured. It can ingest updates visible to the authorized bot.",
        source_mode="LIVE",
    )


def mtproto_status() -> ConnectorStatus:
    settings = get_settings()
    if not settings.telegram_mtproto_enabled:
        return ConnectorStatus(
            platform="telegram",
            state="DISABLED",
            detail="Telegram MTProto public-channel reader is disabled; Bot API remains available.",
            source_mode="LIVE",
        )
    if not settings.telegram_api_id or not settings.telegram_api_hash:
        return ConnectorStatus(
            platform="telegram",
            state="CREDENTIALS_REQUIRED",
            detail="Set TELEGRAM_API_ID and TELEGRAM_API_HASH for the official MTProto client.",
            source_mode="LIVE",
        )
    try:
        import telethon  # noqa: F401
    except Exception:
        return ConnectorStatus(
            platform="telegram",
            state="ERROR",
            detail="Telethon is not installed. Install backend-ai requirements.",
            source_mode="LIVE",
        )
    return ConnectorStatus(
        platform="telegram",
        state="READY",
        detail="Official Telegram MTProto credentials configured. Session must be authorized once before server polling.",
        source_mode="LIVE",
    )


def poll_bot(max_updates: int = 50) -> tuple[list[SocialEvent], ConnectorStatus]:
    settings = get_settings()
    status = bot_status()
    if status.state != "READY":
        return [], status

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/getUpdates"
    params = {
        "limit": max(1, min(max_updates, 100)),
        "timeout": max(0, min(settings.telegram_poll_timeout_seconds, 20)),
        "allowed_updates": '["message","edited_message","channel_post","edited_channel_post"]',
    }
    try:
        with httpx.Client(timeout=settings.telegram_poll_timeout_seconds + 10) as client:
            response = client.get(url, params=params)
        if response.status_code == 429:
            return [], ConnectorStatus(
                platform="telegram", state="RATE_LIMITED",
                detail="Telegram Bot API rate limit reached; retry after the API-provided interval.", source_mode="LIVE"
            )
        response.raise_for_status()
        body = response.json()
        if not body.get("ok"):
            return [], ConnectorStatus(
                platform="telegram", state="ERROR",
                detail=str(body.get("description") or "Telegram Bot API returned ok=false"), source_mode="LIVE"
            )
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        state = "PERMISSION_REQUIRED" if code in (401, 403) else "ERROR"
        return [], ConnectorStatus(
            platform="telegram", state=state,
            detail=f"Telegram Bot API HTTP {code}: {exc.response.text[:220]}", source_mode="LIVE"
        )
    except Exception as exc:
        return [], ConnectorStatus(
            platform="telegram", state="ERROR", detail=f"Telegram connector error: {exc}", source_mode="LIVE"
        )

    normalized_inputs: list[SocialEventIn] = []
    allowed = settings.telegram_allowed_chat_id_set
    for update in body.get("result", []):
        message = (
            update.get("message")
            or update.get("edited_message")
            or update.get("channel_post")
            or update.get("edited_channel_post")
        )
        if not message:
            continue
        chat = message.get("chat") or {}
        chat_id = int(chat.get("id", 0))
        if allowed and chat_id not in allowed:
            continue
        item = _bot_message_to_event(message, edited=bool(update.get("edited_message") or update.get("edited_channel_post")))
        if item:
            normalized_inputs.append(item)

    events = normalize_many(normalized_inputs)
    return events, ConnectorStatus(
        platform="telegram",
        state="LIVE",
        detail=f"Official Bot API returned {len(events)} normalized public/authorized events.",
        source_mode="LIVE",
    )


def _bot_message_to_event(message: dict[str, Any], edited: bool = False) -> SocialEventIn | None:
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "unknown")
    message_id = str(message.get("message_id") or "")
    if not message_id:
        return None
    sender = message.get("from") or message.get("sender_chat") or {}
    author_id = str(sender.get("id") or chat.get("id") or "unknown")
    author_display = (
        sender.get("username")
        or " ".join(part for part in (sender.get("first_name"), sender.get("last_name")) if part)
        or sender.get("title")
        or chat.get("title")
        or "Telegram account"
    )
    text = message.get("text") or message.get("caption") or ""
    parent = message.get("reply_to_message") or {}
    parent_id = None
    if parent.get("message_id"):
        parent_id = f"telegram:{chat_id}:{parent['message_id']}"

    username = chat.get("username")
    permalink = f"https://t.me/{username}/{message_id}" if username else None
    forward_origin = message.get("forward_origin")
    if forward_origin:
        event_type = "forward"
    elif parent_id:
        event_type = "reply"
    elif edited:
        event_type = "edited_message"
    else:
        event_type = "message"

    timestamp = datetime.fromtimestamp(int(message.get("date") or 0), tz=timezone.utc)
    return SocialEventIn(
        platform="telegram",
        source_event_id=f"telegram:{chat_id}:{message_id}",
        event_type=event_type,
        author_platform_id=author_id,
        author_display=author_display,
        text=text,
        language=(sender.get("language_code") or None),
        created_at=timestamp,
        url=permalink,
        parent_event_id=parent_id,
        conversation_id=f"telegram:{chat_id}",
        engagement={},
        public_profile={
            "language": sender.get("language_code"),
            "username": sender.get("username"),
            "chat_type": chat.get("type"),
        },
        source_mode="LIVE",
    )


async def poll_mtproto(channel: str, limit: int = 50) -> tuple[list[SocialEvent], ConnectorStatus]:
    """Read recent public/authorized channel history through Telegram's MTProto API.

    The user account/session must be authorized once using `scripts/telegram_login.py`.
    This is useful when the Bot API cannot see historical public-channel messages.
    """
    settings = get_settings()
    status = mtproto_status()
    if status.state != "READY":
        return [], status
    try:
        from telethon import TelegramClient
    except Exception as exc:  # pragma: no cover
        return [], ConnectorStatus(platform="telegram", state="ERROR", detail=str(exc), source_mode="LIVE")

    client = TelegramClient(
        settings.telegram_session_name,
        int(settings.telegram_api_id),
        settings.telegram_api_hash,
    )
    try:
        await client.connect()
        if not await client.is_user_authorized():
            return [], ConnectorStatus(
                platform="telegram",
                state="PERMISSION_REQUIRED",
                detail="MTProto session is not authorized. Run scripts/telegram_login.py once interactively.",
                source_mode="LIVE",
            )
        entity = await client.get_entity(channel)
        raw_messages = await client.get_messages(entity, limit=max(1, min(limit, 500)))
        inputs: list[SocialEventIn] = []
        channel_id = str(getattr(entity, "id", channel))
        username = getattr(entity, "username", None)
        title = getattr(entity, "title", None) or str(channel)
        for message in reversed(raw_messages):
            if not getattr(message, "id", None):
                continue
            sender_id = str(getattr(message, "sender_id", None) or channel_id)
            text = getattr(message, "message", None) or ""
            parent = getattr(getattr(message, "reply_to", None), "reply_to_msg_id", None)
            event_type = "forward" if getattr(message, "fwd_from", None) else "reply" if parent else "message"
            inputs.append(
                SocialEventIn(
                    platform="telegram",
                    source_event_id=f"telegram:{channel_id}:{message.id}",
                    event_type=event_type,
                    author_platform_id=sender_id,
                    author_display=title if sender_id == channel_id else f"Telegram user {sender_id[-4:]}",
                    text=text,
                    created_at=message.date,
                    url=f"https://t.me/{username}/{message.id}" if username else None,
                    parent_event_id=f"telegram:{channel_id}:{parent}" if parent else None,
                    conversation_id=f"telegram:{channel_id}",
                    engagement={"views": getattr(message, "views", None), "forwards": getattr(message, "forwards", None)},
                    public_profile={"channel": title, "username": username},
                    source_mode="LIVE",
                )
            )
        events = normalize_many(inputs)
        return events, ConnectorStatus(
            platform="telegram", state="LIVE",
            detail=f"Official MTProto client returned {len(events)} recent events from {channel}.", source_mode="LIVE"
        )
    except Exception as exc:
        return [], ConnectorStatus(
            platform="telegram", state="ERROR", detail=f"MTProto connector error: {exc}", source_mode="LIVE"
        )
    finally:
        await client.disconnect()
