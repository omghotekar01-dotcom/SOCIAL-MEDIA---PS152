from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from . import connectors as base
from .connectors import ConnectorError
from .schemas import SocialEventIn

# Conversation mapping survives successive getUpdates polls in the same process.
# It lets replies-to-replies inherit the root channel/discussion conversation.
TELEGRAM_CONVERSATION_CACHE: dict[str, str] = {}
_CACHE_MAX = 5000


def _remember(source_id: str, conversation_id: str) -> None:
    TELEGRAM_CONVERSATION_CACHE[source_id] = conversation_id
    if len(TELEGRAM_CONVERSATION_CACHE) > _CACHE_MAX:
        # Dicts preserve insertion order. Trim oldest mappings; this is only a
        # convenience cache, never the evidence store.
        for key in list(TELEGRAM_CONVERSATION_CACHE)[:1000]:
            TELEGRAM_CONVERSATION_CACHE.pop(key, None)


def _forwarded_channel_origin(message: dict[str, Any] | None) -> tuple[int | str, int] | None:
    """Resolve a Telegram discussion auto-forward back to its channel post.

    Modern Bot API messages expose forward_origin={type:'channel', chat, message_id}.
    Older payloads used forward_from_chat + forward_from_message_id. Supporting
    both makes the SIH prototype resilient across Telegram client/server versions.
    """
    if not message:
        return None
    origin = message.get("forward_origin") or {}
    if origin.get("type") == "channel":
        chat = origin.get("chat") or {}
        chat_id = chat.get("id")
        message_id = origin.get("message_id")
        if chat_id is not None and message_id is not None:
            return chat_id, int(message_id)

    legacy_chat = message.get("forward_from_chat") or {}
    legacy_chat_id = legacy_chat.get("id")
    legacy_message_id = message.get("forward_from_message_id")
    if legacy_chat_id is not None and legacy_message_id is not None:
        return legacy_chat_id, int(legacy_message_id)
    return None


def _message_text(message: dict[str, Any]) -> str:
    text = str(message.get("text") or message.get("caption") or "").strip()
    if text:
        return text
    # Keep media-only discussion evidence visible instead of silently dropping it.
    media_kind = next((key for key in ("photo", "video", "animation", "document", "sticker", "voice", "audio") if message.get(key)), None)
    return f"[Telegram {media_kind or 'media'} message; no text caption]" if media_kind else ""


def _sender(message: dict[str, Any], chat: dict[str, Any]) -> tuple[str | None, str | None]:
    sender = message.get("from") or message.get("sender_chat") or {}
    sender_id = sender.get("id") or chat.get("id")
    display = (
        sender.get("username")
        or sender.get("title")
        or " ".join(part for part in [sender.get("first_name"), sender.get("last_name")] if part)
        or chat.get("username")
        or chat.get("title")
    )
    return (str(sender_id) if sender_id is not None else None), (str(display) if display else None)


def _permalink(chat: dict[str, Any], message_id: int | None) -> str | None:
    username = chat.get("username")
    if username and message_id:
        return f"https://t.me/{username}/{message_id}"
    return None


def _semantic_event_type(update_key: str, chat: dict[str, Any], message: dict[str, Any], parent_event_id: str | None) -> str:
    chat_type = str(chat.get("type") or "")
    if update_key in {"channel_post", "edited_channel_post"}:
        return update_key
    if message.get("is_automatic_forward") and _forwarded_channel_origin(message):
        return "channel_post_forward"
    if parent_event_id:
        return "discussion_reply" if str(message.get("reply_to_message", {}).get("chat", {}).get("type") or chat_type) in {"group", "supergroup"} else "reply"
    if chat_type in {"group", "supergroup"}:
        return "discussion_message"
    return update_key


def _normalize_message(update_key: str, message: dict[str, Any], run_id: str) -> SocialEventIn | None:
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    message_id = message.get("message_id")
    if chat_id is None or message_id is None:
        return None

    allowed = base.SETTINGS.telegram_allowed_chat_id_set
    if allowed and chat_id not in allowed:
        return None

    text = _message_text(message)
    if not text:
        return None

    # Telegram copies a channel post into its linked discussion group. Normalize
    # that automatic forward to the ORIGINAL channel event id so the channel_post
    # and discussion copy dedupe into one root evidence object.
    forwarded_origin = _forwarded_channel_origin(message) if message.get("is_automatic_forward") else None
    if forwarded_origin:
        origin_chat_id, origin_message_id = forwarded_origin
        source_event_id = f"{origin_chat_id}:{origin_message_id}"
        conversation_id = source_event_id
        parent_event_id = None
        collection_scope = "telegram_linked_discussion_root"
    else:
        source_event_id = f"{chat_id}:{message_id}"
        reply = message.get("reply_to_message") or {}
        parent_event_id: str | None = None
        conversation_id: str

        # A top-level channel comment is a group message replying to the
        # auto-forwarded channel post. Resolve that nested forward back to the
        # original channel post so ReactionIntelligence can join them.
        reply_origin = _forwarded_channel_origin(reply)
        if reply_origin:
            origin_chat_id, origin_message_id = reply_origin
            root_id = f"{origin_chat_id}:{origin_message_id}"
            parent_event_id = root_id
            conversation_id = root_id
            collection_scope = "telegram_linked_discussion_comment"
        elif reply.get("message_id") is not None:
            parent_event_id = f"{chat_id}:{reply.get('message_id')}"
            conversation_id = TELEGRAM_CONVERSATION_CACHE.get(parent_event_id, str(chat_id))
            collection_scope = "telegram_group_reply"
        elif update_key in {"channel_post", "edited_channel_post"}:
            conversation_id = source_event_id
            collection_scope = "telegram_channel_post"
        else:
            thread_id = message.get("message_thread_id")
            conversation_id = f"{chat_id}:thread:{thread_id}" if thread_id is not None else str(chat_id)
            collection_scope = "telegram_bot_visible_message"

    _remember(source_event_id, conversation_id)

    sender_id, display = _sender(message, chat)
    date_value = int(message.get("date") or 0)
    created_at = datetime.fromtimestamp(date_value, tz=timezone.utc) if date_value else datetime.now(timezone.utc)
    event_type = _semantic_event_type(update_key, chat, message, parent_event_id)

    profile: dict[str, Any] = {
        "language": (message.get("from") or {}).get("language_code"),
        "chat_id": chat_id,
        "chat_type": chat.get("type"),
        "chat_title": chat.get("title"),
        "chat_username": chat.get("username"),
        "message_thread_id": message.get("message_thread_id"),
        "is_automatic_forward": bool(message.get("is_automatic_forward")),
        "collection_scope": collection_scope,
        "comments_capability": "linked discussion group via Bot API",
    }
    if forwarded_origin:
        profile["forwarded_channel_chat_id"] = forwarded_origin[0]
        profile["forwarded_channel_message_id"] = forwarded_origin[1]

    return SocialEventIn(
        platform="telegram",
        source_event_id=source_event_id,
        event_type=event_type,
        author_platform_id=sender_id,
        author_display=display,
        text=text,
        created_at=created_at,
        url=_permalink(chat, int(message_id)),
        parent_event_id=parent_event_id,
        conversation_id=conversation_id,
        engagement={},
        public_profile=profile,
        source_mode="LIVE",
        connector_run_id=run_id,
    )


async def telegram_rich_poll(max_updates: int = 50) -> list[SocialEventIn]:
    """Poll Telegram Bot API and preserve channel -> discussion comment lineage.

    This uses the same process-level offset/lock as the original connector so
    existing API behavior and tests remain compatible. Telegram only delivers
    messages that the bot is entitled to see; for a linked discussion group the
    bot should be an admin or group privacy should be disabled in BotFather.
    """
    token = base.SETTINGS.telegram_bot_token
    if not token:
        raise ConnectorError("Telegram bot token is not configured.", "CREDENTIALS_REQUIRED")

    run_id = f"tg-rich-{uuid4().hex[:10]}"
    endpoint = f"https://api.telegram.org/bot{token}/getUpdates"

    async with base.TELEGRAM_POLL_LOCK:
        params: dict[str, Any] = {
            "timeout": min(max(0, base.SETTINGS.telegram_poll_timeout_seconds), 20),
            "limit": min(max_updates, 100),
            "allowed_updates": '["message","edited_message","channel_post","edited_channel_post"]',
        }
        if base.TELEGRAM_UPDATE_OFFSET > 0:
            params["offset"] = base.TELEGRAM_UPDATE_OFFSET

        async with httpx.AsyncClient(timeout=base.SETTINGS.telegram_poll_timeout_seconds + 10) as client:
            response = await client.get(endpoint, params=params)

        if response.status_code == 401:
            raise ConnectorError("Telegram bot token is invalid.", "CREDENTIALS_REQUIRED")
        if response.status_code == 409:
            raise ConnectorError(
                "Telegram getUpdates conflicts with an active webhook. Remove the webhook before using NEXUS polling.",
                "PERMISSION_REQUIRED",
            )
        if response.status_code == 429:
            raise ConnectorError("Telegram Bot API rate-limited the request.", "RATE_LIMITED")
        if response.status_code >= 400:
            raise ConnectorError(f"Telegram API error {response.status_code}: {response.text[:300]}")

        body = response.json()
        if not body.get("ok"):
            raise ConnectorError(f"Telegram API returned an error: {body.get('description', 'unknown error')}")

        updates = body.get("result", [])
        if updates:
            update_ids = [int(item.get("update_id")) for item in updates if item.get("update_id") is not None]
            if update_ids:
                base.TELEGRAM_UPDATE_OFFSET = max(base.TELEGRAM_UPDATE_OFFSET, max(update_ids) + 1)

    output: list[SocialEventIn] = []
    seen: set[str] = set()
    for update in updates:
        for key in ("message", "edited_message", "channel_post", "edited_channel_post"):
            message = update.get(key)
            if not message:
                continue
            event = _normalize_message(key, message, run_id)
            if event and event.source_event_id not in seen:
                output.append(event)
                seen.add(event.source_event_id)
            break
    return output
