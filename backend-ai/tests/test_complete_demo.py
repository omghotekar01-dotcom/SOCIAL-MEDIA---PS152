from datetime import datetime, timezone

from app.complete_demo import complete_seed_demo_events


def test_complete_demo_contains_linked_reaction_conversations():
    rows = complete_seed_demo_events(datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc))
    roots = {row.source_event_id: row for row in rows if row.conversation_id == row.source_event_id and row.event_type in {"post", "channel_post"}}
    replies = [row for row in rows if row.event_type == "reply" and row.parent_event_id]

    assert "demo-x-riverlink-root" in roots
    assert "demo-telegram-riverlink-verified" in roots
    assert "demo-reddit-techfest-root" in roots
    assert len(replies) >= 30
    assert all(row.source_mode == "REPLAY" for row in replies)
    assert all(row.parent_event_id in roots for row in replies)


def test_complete_demo_exposes_explicit_public_profile_signals_without_guessing_age():
    rows = complete_seed_demo_events(datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc))
    reaction_rows = [row for row in rows if row.public_profile.get("collection_scope") == "fictional_reaction_demo"]
    assert reaction_rows
    assert any("I am 21" in str(row.public_profile.get("bio")) for row in reaction_rows)
    assert all(row.public_profile.get("demo_disclosure") for row in reaction_rows)
