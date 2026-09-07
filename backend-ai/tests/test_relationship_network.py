from datetime import datetime, timezone

from app.schemas import SocialEvent
from app.stable_views import stable_network


def row(source_id: str, author: str, pseudo: str, following: list[str] | None = None) -> SocialEvent:
    return SocialEvent(
        id=f"internal-{source_id}",
        platform="bluesky",
        source_event_id=source_id,
        event_type="post",
        author_platform_id=f"did:plc:{author}",
        author_pseudo_id=pseudo,
        author_display=author,
        text=f"Public post from {author}",
        created_at=datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc),
        public_profile={"observed_following_handles": following or []},
        source_mode="LIVE",
        sentiment_label="neutral",
        emotion_scores={"neutral_other": 1.0},
        stance_label="unclear",
        topic_terms=["public", "post"],
    )


def test_network_uses_provider_observed_public_follow_relationships():
    events = [
        row("p1", "alice.example", "pseudo-alice", ["bob.example"]),
        row("p2", "bob.example", "pseudo-bob"),
    ]
    network = stable_network(events)
    assert network["summary"]["nodes"] == 2
    assert network["summary"]["edges"] >= 1
    assert any(
        edge["source"] == "pseudo-alice"
        and edge["target"] == "pseudo-bob"
        and "public-follow" in edge["types"]
        for edge in network["edges"]
    )
