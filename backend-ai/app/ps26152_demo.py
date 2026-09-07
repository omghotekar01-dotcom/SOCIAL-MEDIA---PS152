from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .complete_demo import complete_seed_demo_events
from .schemas import SocialEventIn


def ps26152_seed_demo_events(now: datetime | None = None) -> list[SocialEventIn]:
    """Full five-component demo with all original platform-priority tiers represented.

    Instagram/Facebook records are fictional REPLAY evidence. They never imply
    that Meta credentials or live access exist on the analyst machine.
    """
    now = (now or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    rows = list(complete_seed_demo_events(now))
    base = now - timedelta(minutes=44)

    def profile(index: int, interest: str) -> dict:
        age = 22 if index % 2 == 0 else 28
        return {
            "language": "en",
            "region": "Pune, Maharashtra, India",
            "bio": f"I am {age}, public demo profile interested in {interest}, technology and city updates.",
            "professional_interest": interest,
            "collection_scope": "fictional_meta_replay_demo",
            "demo_disclosure": "Fictional deterministic SIH jury data; not a real social-media claim.",
        }

    def add_conversation(platform: str, root_id: str, author: str, text: str, minute: int, replies: list[str]) -> None:
        rows.append(
            SocialEventIn(
                platform=platform,  # type: ignore[arg-type]
                source_event_id=root_id,
                event_type="post",
                author_platform_id=f"{platform}-{author}",
                author_display=author,
                text=text,
                created_at=base + timedelta(minutes=minute),
                url=f"https://example.invalid/{platform}/{root_id}",
                conversation_id=root_id,
                engagement={"likes": 42 + minute, "comments": len(replies), "shares": 5},
                public_profile=profile(minute, "media_creative" if platform == "instagram" else "public_policy"),
                source_mode="REPLAY",
                connector_run_id="demo-meta-coverage-v1",
            )
        )
        for index, reply in enumerate(replies, start=1):
            rows.append(
                SocialEventIn(
                    platform=platform,  # type: ignore[arg-type]
                    source_event_id=f"{root_id}-comment-{index:02d}",
                    event_type="comment",
                    author_platform_id=f"{platform}-{root_id}-user-{index:02d}",
                    author_display=f"{platform}_demo_user_{index:02d}",
                    text=reply,
                    created_at=base + timedelta(minutes=minute + index),
                    url=f"https://example.invalid/{platform}/{root_id}/comment/{index}",
                    parent_event_id=root_id,
                    conversation_id=root_id,
                    engagement={"likes": index + 1},
                    public_profile=profile(index, "technology" if index % 2 else "education_student"),
                    source_mode="REPLAY",
                    connector_run_id="demo-meta-coverage-v1",
                )
            )

    add_conversation(
        "instagram",
        "demo-instagram-riverlink",
        "city_visual_demo",
        "RiverLink clarification card: maintenance is limited to 01:00-04:00. Full-day closure screenshots are unverified. #RiverLinkUpdate",
        8,
        [
            "This clarification is useful and the exact timing makes it credible.",
            "I was worried earlier; glad the full-day shutdown claim was corrected.",
            "Please keep the official source in the caption so people can verify it.",
            "Great visual summary, but the old screenshot is still spreading in stories.",
            "I support the correction. People should stop forwarding the unverified version.",
            "Surprised how quickly the wrong timing became the dominant version.",
        ],
    )

    add_conversation(
        "facebook",
        "demo-facebook-riverlink",
        "community_page_demo",
        "Community update: verified RiverLink maintenance window is 01:00-04:00. Morning service remains scheduled. #RiverLinkUpdate",
        20,
        [
            "Confirmed, this matches the service notice I checked.",
            "Thank you. Our local group was anxious because of the earlier forwarded message.",
            "Please pin this correction; the false full-day claim is still circulating.",
            "Good update. Exact source links build trust.",
            "I agree with the correction, but communication should have happened sooner.",
            "This is much clearer than the screenshots people were sharing.",
        ],
    )

    return rows
