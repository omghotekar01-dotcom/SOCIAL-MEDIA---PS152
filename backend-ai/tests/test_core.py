from datetime import datetime, timezone

from app.analytics.demographics import aggregate_demographics
from app.analytics.graph import build_network
from app.analytics.narratives import cluster_events
from app.analytics.nlp import analyze_text
from app.schemas import SocialEventIn
from app.services.normalizer import normalize_event


def make_event(platform: str, source_id: str, author: str, text: str, minute: int, parent: str | None = None):
    return normalize_event(
        SocialEventIn(
            platform=platform,
            source_event_id=source_id,
            event_type="reply" if parent else "post",
            author_platform_id=author,
            author_display=author,
            text=text,
            created_at=datetime(2026, 9, 6, 14, minute, tzinfo=timezone.utc),
            parent_event_id=parent,
            public_profile={"language": "en", "location": "Pune", "bio": "software engineer and metro commuter"},
            source_mode="REPLAY",
        )
    )


def test_normalizer_pseudonymizes_and_extracts_entities():
    event = normalize_event(
        SocialEventIn(
            platform="x",
            source_event_id="x:1",
            author_platform_id="alice",
            author_display="Alice",
            text="  Pune   Metro #Rain update @bob https://example.org/news  ",
            created_at=datetime.now(timezone.utc),
            source_mode="IMPORT",
        )
    )
    assert event.author_pseudo_id
    assert event.author_pseudo_id != "alice"
    assert "rain" in event.hashtags
    assert "bob" in event.mentions
    assert "https://example.org/news" in event.urls
    assert event.raw_hash


def test_nlp_returns_multi_dimensional_signals():
    result = analyze_text("I am worried and afraid this metro closure rumour may be true")
    assert result["language"]
    assert result["sentiment_label"] in {"positive", "neutral", "negative"}
    assert result["emotion_label"] in {"anxiety", "anger", "excitement", "neutral"}
    assert result["stance_label"] in {"supportive", "against", "uncertain"}
    assert 0 <= result["sarcasm_probability"] <= 1
    assert result["topic_terms"]


def test_cross_platform_narrative_and_interaction_graph():
    first = make_event("telegram", "tg:1", "alice", "Pune metro may close tomorrow because of heavy rain", 0)
    second = make_event("x", "x:2", "bob", "Pune metro may close tomorrow because heavy rain continues", 5)
    third = make_event("x", "x:3", "charlie", "Metro closure is unconfirmed; wait for an official rain update", 7, parent="x:2")

    analyzed, cards = cluster_events([first, second, third])
    assert any(card["cross_platform"] for card in cards)
    network = build_network(analyzed)
    assert network["metadata"]["node_count"] == 3
    assert network["metadata"]["edge_count"] >= 1
    assert all("structural_influence_score" in node for node in network["nodes"])


def test_demographics_are_aggregate_and_k_anonymous():
    events = [
        make_event("x" if index % 2 else "telegram", f"e:{index}", f"u{index}", "metro transport update", index, None)
        for index in range(12)
    ]
    demographics = aggregate_demographics(events)
    assert demographics["sample_size"] == 12
    assert demographics["publishable"] is True
    assert demographics["privacy_note"]
    assert "sensitive traits" in demographics["privacy_note"]
    # All demo profiles explicitly say Pune, so this broad aggregate is publishable.
    assert any(item["label"] == "Pune" for item in demographics["broad_geography"])
