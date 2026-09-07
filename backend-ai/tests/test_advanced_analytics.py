from datetime import datetime, timedelta, timezone

from app.advanced_analytics import advanced_demographics, advanced_infer_text, advanced_trend_metrics
from app.reaction_engine import summarize_conversation, workspace_reaction_overview
from app.schemas import SocialEvent


NOW = datetime(2026, 9, 7, 12, 0, tzinfo=timezone.utc)


def event(
    source_id: str,
    text: str,
    *,
    author: str,
    minutes: int = 0,
    event_type: str = "post",
    parent: str | None = None,
    conversation: str | None = None,
    sentiment: str = "neutral",
    stance: str = "unclear",
    emotions: dict[str, float] | None = None,
    profile: dict | None = None,
) -> SocialEvent:
    return SocialEvent(
        id=f"internal-{source_id}",
        platform="x",
        source_event_id=source_id,
        event_type=event_type,
        author_platform_id=author,
        author_pseudo_id=f"pseudo-{author}",
        author_display=author,
        text=text,
        created_at=NOW + timedelta(minutes=minutes),
        parent_event_id=parent,
        conversation_id=conversation,
        public_profile=profile or {},
        source_mode="IMPORT",
        sentiment_label=sentiment,
        sentiment_score=0.0,
        stance_label=stance,
        stance_confidence=0.8,
        sarcasm_probability=0.1,
        emotion_scores=emotions or {"neutral_other": 1.0},
        topic_terms=["demo"],
    )


def test_eight_emotion_contract_is_always_exposed():
    result = advanced_infer_text("I am shocked, worried and angry but I trust the verified evidence")
    expected = {"anxiety", "anger", "excitement", "sadness", "joy", "disgust", "surprise", "trust"}
    assert expected.issubset(result["emotion_scores"])
    assert "neutral_other" in result["emotion_scores"]
    assert result["inference_method"].endswith("v2")


def test_demographics_use_broad_public_signals_and_explicit_age_only():
    rows = []
    for index in range(12):
        rows.append(
            event(
                f"d-{index}",
                "Public post",
                author=f"user{index}",
                profile={
                    "bio": "I am 21, engineering student and AI developer",
                    "region": "Pune, Maharashtra, India",
                    "language": "en",
                },
            )
        )
    result = advanced_demographics(rows)
    assert result["age_brackets"]["method"] == "explicit-self-declared-age-only"
    assert result["age_brackets"]["counts"]["18-24"] == 12
    assert result["broad_geography"]["counts"]["West India"] == 12
    assert result["professional_interests"]["counts"]["technology"] == 12
    assert "names/photos/behavior" in result["privacy_note"]


def test_trend_metrics_include_near_term_momentum_without_claiming_global_prediction():
    rows = [
        event("t1", "topic alpha", author="u1", minutes=0),
        event("t2", "topic alpha", author="u2", minutes=15),
        event("t3", "topic alpha", author="u3", minutes=30),
        event("t4", "topic alpha", author="u4", minutes=30),
        event("t5", "topic alpha", author="u5", minutes=45),
        event("t6", "topic alpha", author="u6", minutes=45),
        event("t7", "topic alpha", author="u7", minutes=45),
    ]
    result = advanced_trend_metrics(rows, rows)
    assert "velocity" in result
    assert "momentum" in result
    assert "predicted_next_bucket_volume" in result
    assert "forecast_confidence" in result
    assert "collected dataset" in result["forecast_scope"]


def test_reaction_engine_separates_root_post_from_public_opinion():
    root = event("root", "Root post is informational", author="publisher", conversation="root")
    reply1 = event(
        "r1",
        "This is wrong and unacceptable",
        author="a",
        minutes=1,
        event_type="reply",
        parent="root",
        conversation="root",
        sentiment="negative",
        stance="against",
        emotions={"anger": 0.8, "anxiety": 0.2},
    )
    reply2 = event(
        "r2",
        "I support this",
        author="b",
        minutes=2,
        event_type="reply",
        parent="root",
        conversation="root",
        sentiment="positive",
        stance="supportive",
        emotions={"joy": 0.7, "trust": 0.3},
    )
    rows = [root, reply1, reply2]
    summary = summarize_conversation(root, rows)
    assert summary["reaction_count"] == 2
    assert summary["negative_share"] == 0.5
    assert summary["positive_share"] == 0.5
    assert "polarized-opinion" in summary["flags"]
    workspace = workspace_reaction_overview(rows)
    assert workspace["captured_reactions"] == 2
    assert workspace["conversations_with_reactions"] == 1
