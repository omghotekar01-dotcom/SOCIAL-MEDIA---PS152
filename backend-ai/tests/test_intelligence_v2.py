from __future__ import annotations

from datetime import datetime, timezone

from app.intelligence_v2 import analyze_text, enrich_event_v2, intelligence_summary
from app.schemas import SocialEvent, SocialEventIn


EXPECTED_EMOTIONS = {
    "joy_excitement",
    "anger_frustration",
    "sadness",
    "fear_anxiety",
    "surprise_shock",
    "trust_confidence",
    "disgust_aversion",
    "neutral_informational",
}


def test_eight_emotion_contract_is_stable():
    result = analyze_text("I am worried and anxious about this dangerous situation")
    assert set(result["emotion_scores"]) == EXPECTED_EMOTIONS
    assert abs(sum(result["emotion_scores"].values()) - 1.0) < 0.01
    assert result["primary_emotion"] == "fear_anxiety"
    assert 0 <= result["confidence"] <= 1


def test_stance_and_sarcasm_are_separate_dimensions():
    result = analyze_text("Amazing work guys, another brilliant decision. Yeah right, totally unacceptable 🙃")
    assert result["stance_label"] == "against"
    assert result["sarcasm_probability"] >= 0.5
    assert result["primary_emotion"] in EXPECTED_EMOTIONS
    assert "toxicity_label" in result


def test_hinglish_code_mix_is_detected():
    result = analyze_text("Bhai ye decision bahut galat hai, I am really worried", "en")
    assert result["code_mix"]["code_mixed"] is True
    assert result["code_mix"]["language_family"] == "indic-english-code-mixed"
    assert result["stance_label"] == "against"


def test_enrichment_preserves_evidence_fields_and_eight_emotions():
    event = SocialEventIn(
        platform="replay",
        source_event_id="v2-1",
        author_display="analyst-demo",
        text="This is shocking and I strongly oppose this wrong decision #Policy @agency",
        created_at=datetime.now(timezone.utc),
        source_mode="REPLAY",
    )
    normalized, derived = enrich_event_v2(event)
    assert "policy" in normalized.hashtags
    assert "agency" in normalized.mentions
    assert set(derived["emotion_scores"]) == EXPECTED_EMOTIONS
    assert derived["stance_label"] == "against"
    assert derived["inference_method"] == "nexus-multidimensional-offline-v2"


def test_intelligence_summary_aggregates_without_personal_demographic_map():
    now = datetime.now(timezone.utc)
    events = [
        SocialEvent(
            platform="replay",
            source_event_id="a",
            author_display="a",
            author_pseudo_id="anon-a",
            text="I am worried and afraid about this risk",
            language="en",
            created_at=now,
            source_mode="REPLAY",
        ),
        SocialEvent(
            platform="telegram",
            source_event_id="b",
            author_display="b",
            author_pseudo_id="anon-b",
            text="Bhai this is galat and unacceptable",
            language="en",
            created_at=now,
            source_mode="IMPORT",
        ),
    ]
    result = intelligence_summary(events)
    assert result["total_events"] == 2
    assert set(result["emotion_mix"]) == EXPECTED_EMOTIONS
    assert result["code_mixed_events"] >= 1
    assert "stance_mix" in result
    assert "platforms" in result
    assert "users" not in result
