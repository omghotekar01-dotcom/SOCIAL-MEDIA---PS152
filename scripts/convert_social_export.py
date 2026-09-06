from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUPPORTED_PLATFORMS = {
    'x', 'telegram', 'youtube', 'instagram', 'facebook', 'reddit', 'bluesky', 'mastodon', 'replay'
}

ID_KEYS = ('source_event_id', 'id', 'post_id', 'tweet_id', 'media_id', 'message_id', 'comment_id')
TEXT_KEYS = ('text', 'full_text', 'caption', 'message', 'body', 'content', 'description', 'title')
TIME_KEYS = ('created_at', 'created_time', 'timestamp', 'date', 'published_at', 'publishedAt', 'datetime')
AUTHOR_ID_KEYS = ('author_platform_id', 'author_id', 'user_id', 'account_id', 'channel_id')
AUTHOR_KEYS = ('author_display', 'username', 'author', 'user', 'screen_name', 'channel_title', 'name')
URL_KEYS = ('url', 'permalink', 'permalink_url', 'link', 'web_url')
LANGUAGE_KEYS = ('language', 'lang')


def first(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ''):
            return value
    return None


def text_from(row: dict[str, Any]) -> str:
    direct = first(row, TEXT_KEYS)
    if direct not in (None, ''):
        return ' '.join(str(direct).split())
    parts = [str(row.get(k)).strip() for k in ('title', 'description') if row.get(k)]
    return ' — '.join(parts)


def parse_time(value: Any) -> tuple[str, bool]:
    if value in (None, ''):
        return datetime.now(timezone.utc).isoformat(), True
    raw = str(value).strip()
    if raw.isdigit():
        try:
            number = int(raw)
            if number > 10_000_000_000:
                number //= 1000
            return datetime.fromtimestamp(number, timezone.utc).isoformat(), False
        except (ValueError, OSError, OverflowError):
            pass
    candidate = raw.replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(candidate)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat(), False
    except ValueError:
        # Preserve source value for audit while using collection time as a safe fallback.
        return datetime.now(timezone.utc).isoformat(), True


def stable_id(platform: str, row: dict[str, Any], index: int) -> str:
    explicit = first(row, ID_KEYS)
    if explicit not in (None, ''):
        return str(explicit)
    raw = json.dumps(row, sort_keys=True, ensure_ascii=False, default=str)
    digest = hashlib.sha256(f'{platform}|{index}|{raw}'.encode('utf-8')).hexdigest()[:24]
    return f'import-{digest}'


def entities(text: str) -> tuple[list[str], list[str], list[str]]:
    hashtags = sorted({m.group(1).lower() for m in re.finditer(r'(?<!\w)#([\w-]{2,80})', text, re.UNICODE)})
    mentions = sorted({m.group(1).lower() for m in re.finditer(r'(?<!\w)@([A-Za-z0-9_.-]{2,80})', text)})
    urls = sorted({m.group(0).rstrip('.,;:!?)]}') for m in re.finditer(r'https?://[^\s<>()\[\]{}\"\']+', text, re.I)})
    return hashtags, mentions, urls


def number(row: dict[str, Any], *keys: str) -> int | float | None:
    for key in keys:
        value = row.get(key)
        if value in (None, ''):
            continue
        try:
            number_value = float(str(value).replace(',', ''))
            return int(number_value) if number_value.is_integer() else number_value
        except ValueError:
            continue
    return None


def normalize(platform: str, row: dict[str, Any], index: int) -> dict[str, Any] | None:
    text = text_from(row)
    if not text:
        return None
    created_at, timestamp_fallback = parse_time(first(row, TIME_KEYS))
    hashtags, mentions, urls = entities(text)
    source_url = first(row, URL_KEYS)

    engagement: dict[str, int | float] = {}
    metric_map = {
        'likes': ('likes', 'like_count', 'favorite_count', 'favourites_count'),
        'shares': ('shares', 'share_count', 'retweet_count', 'repost_count', 'reblogs_count'),
        'replies': ('replies', 'reply_count', 'comments', 'comments_count', 'num_comments'),
        'views': ('views', 'view_count', 'views_count'),
    }
    for label, keys in metric_map.items():
        value = number(row, *keys)
        if value is not None:
            engagement[label] = value

    raw_id = stable_id(platform, row, index)
    author_id = first(row, AUTHOR_ID_KEYS)
    author = first(row, AUTHOR_KEYS)
    language = first(row, LANGUAGE_KEYS)

    return {
        'platform': platform,
        'source_event_id': f'import:{raw_id}',
        'event_type': str(row.get('event_type') or row.get('type') or 'post'),
        'author_platform_id': str(author_id) if author_id not in (None, '') else None,
        'author_display': str(author) if author not in (None, '') else None,
        'text': text,
        'language': str(language) if language not in (None, '') else None,
        'created_at': created_at,
        'url': str(source_url) if source_url not in (None, '') else None,
        'parent_event_id': str(row.get('parent_event_id')) if row.get('parent_event_id') not in (None, '') else None,
        'conversation_id': str(row.get('conversation_id')) if row.get('conversation_id') not in (None, '') else None,
        'mentions': mentions,
        'hashtags': hashtags,
        'urls': urls,
        'engagement': engagement,
        'public_profile': {
            'collection_scope': 'analyst_supplied_export',
            'original_timestamp': first(row, TIME_KEYS),
            'timestamp_fallback_to_import_time': timestamp_fallback,
        },
        'source_mode': 'IMPORT',
        'connector_run_id': 'offline-export-converter-v1',
    }


def load_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == '.csv':
        with path.open('r', encoding='utf-8-sig', newline='') as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if suffix == '.json':
        payload = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(payload, list):
            return [dict(item) for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ('events', 'data', 'items', 'posts', 'tweets', 'media'):
                value = payload.get(key)
                if isinstance(value, list):
                    return [dict(item) for item in value if isinstance(item, dict)]
            return [payload]
        raise ValueError('JSON must be an object or array')
    raise ValueError('Input must be .csv or .json')


def main() -> int:
    parser = argparse.ArgumentParser(description='Convert public/authorized social exports to NEXUS import JSON.')
    parser.add_argument('input', type=Path, help='CSV or JSON export')
    parser.add_argument('--platform', required=True, choices=sorted(SUPPORTED_PLATFORMS - {'replay'}))
    parser.add_argument('--output', type=Path, default=Path('nexus-import.json'))
    args = parser.parse_args()

    rows = load_rows(args.input)
    events = [event for i, row in enumerate(rows) if (event := normalize(args.platform, row, i)) is not None]
    payload = {
        'events': events,
        'meta': {
            'source_file': args.input.name,
            'platform': args.platform,
            'input_rows': len(rows),
            'converted_events': len(events),
            'mode': 'IMPORT',
        },
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Converted {len(events)}/{len(rows)} rows -> {args.output}')
    print('Upload this JSON with the NEXUS Import JSON control. Records remain labelled IMPORT.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
