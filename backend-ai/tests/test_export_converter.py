from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts' / 'convert_social_export.py'
spec = importlib.util.spec_from_file_location('convert_social_export', SCRIPT)
assert spec and spec.loader
converter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(converter)


def test_x_export_row_normalizes_to_import_event():
    event = converter.normalize('x', {
        'tweet_id': '19001',
        'screen_name': 'public_demo_user',
        'full_text': 'Public #RiverLinkUpdate from @fieldteam https://example.org/source',
        'created_at': '2026-09-06T12:30:00Z',
        'favorite_count': '12',
        'retweet_count': '4',
        'url': 'https://x.com/public_demo_user/status/19001',
        'lang': 'en',
    }, 0)

    assert event is not None
    assert event['platform'] == 'x'
    assert event['source_mode'] == 'IMPORT'
    assert event['source_event_id'] == 'import:19001'
    assert event['author_display'] == 'public_demo_user'
    assert event['engagement']['likes'] == 12
    assert event['engagement']['shares'] == 4
    assert 'riverlinkupdate' in event['hashtags']
    assert 'fieldteam' in event['mentions']
    assert event['public_profile']['timestamp_fallback_to_import_time'] is False


def test_missing_timestamp_is_disclosed_as_fallback():
    event = converter.normalize('instagram', {'id': 'ig-1', 'caption': 'Public caption'}, 0)
    assert event is not None
    assert event['source_mode'] == 'IMPORT'
    assert event['public_profile']['timestamp_fallback_to_import_time'] is True
