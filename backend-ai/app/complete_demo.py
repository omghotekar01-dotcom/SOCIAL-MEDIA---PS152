from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .analytics import seed_demo_events as _base_seed_demo_events
from .schemas import SocialEventIn


def complete_seed_demo_events(now: datetime | None = None) -> list[SocialEventIn]:
    """Extend the deterministic demo with linked root posts + public reactions.

    All added records are fictional and REPLAY-labelled. Their purpose is to make
    the SIH26152 distinction between root-content NLP and audience-opinion NLP
    visible even when external providers are unavailable during judging.
    """
    now = (now or datetime.now(timezone.utc)).replace(second=0, microsecond=0)
    rows = list(_base_seed_demo_events(now))
    base = now - timedelta(minutes=48)
    run_id = "demo-reaction-v2"

    def profile(index: int, *, location: str = "Pune, Maharashtra, India") -> dict:
        age = 20 + (index % 4)
        return {
            "language": "en",
            "region": location,
            "bio": f"I am {age}, engineering student interested in AI, technology and public information.",
            "professional_interest": "technology",
            "collection_scope": "fictional_reaction_demo",
            "demo_disclosure": "Fictional deterministic SIH jury data; not a real social-media claim.",
        }

    def add_root(platform: str, source_id: str, text: str, author: str, minute: int, likes: int, replies: int) -> None:
        rows.append(
            SocialEventIn(
                platform=platform,  # type: ignore[arg-type]
                source_event_id=source_id,
                event_type="channel_post" if platform == "telegram" else "post",
                author_platform_id=f"{platform}-{author}",
                author_display=author,
                text=text,
                created_at=base + timedelta(minutes=minute),
                url=f"https://example.invalid/{platform}/{source_id}",
                conversation_id=source_id,
                engagement={"likes": likes, "replies": replies, "shares": max(1, likes // 7)},
                public_profile=profile(0),
                source_mode="REPLAY",
                connector_run_id=run_id,
            )
        )

    def add_reply(platform: str, root_id: str, number: int, text: str, author: str, minute: int, likes: int = 0) -> None:
        rows.append(
            SocialEventIn(
                platform=platform,  # type: ignore[arg-type]
                source_event_id=f"{root_id}-reply-{number:02d}",
                event_type="reply",
                author_platform_id=f"{platform}-{author}",
                author_display=author,
                text=text,
                created_at=base + timedelta(minutes=minute),
                url=f"https://example.invalid/{platform}/{root_id}/reply/{number}",
                parent_event_id=root_id,
                conversation_id=root_id,
                engagement={"likes": likes},
                public_profile=profile(number),
                source_mode="REPLAY",
                connector_run_id=run_id,
            )
        )

    # Conversation 1: an unverified claim receives a tense, polarized audience response.
    x_root = "demo-x-riverlink-root"
    add_root(
        "x",
        x_root,
        "Unconfirmed claim: RiverLink may remain fully shut tomorrow. Has anyone seen an official notice? #RiverLinkUpdate",
        "city_update_demo",
        0,
        94,
        14,
    )
    x_replies = [
        "This is worrying. People need the official timing before making travel plans.",
        "Stop spreading this. The full-day shutdown claim looks wrong and has no proof.",
        "I am anxious because my exam commute depends on this route tomorrow.",
        "Yeah right, another completely reliable forwarded message with zero source. Great job.",
        "I support asking for verification, but please do not present the shutdown as confirmed.",
        "This is unacceptable if someone knowingly changed a maintenance notice into a full closure claim.",
        "I checked the service page and cannot find a full-day closure. This seems false.",
        "People are panicking in our group. Please share the verified notice, not screenshots without context.",
        "I am shocked how fast this spread. Is there any credible evidence at all?",
        "The actual maintenance window is limited. The viral wording is misleading.",
        "I disagree with the claim, but the confusion is understandable because the notice was late.",
        "Verified update is out now. Please correct the earlier message and share the exact hours.",
        "Good, the clarification finally gives commuters something reliable to plan around.",
        "I still do not trust random forwarded images. Link the official source directly.",
    ]
    for index, text in enumerate(x_replies, start=1):
        add_reply("x", x_root, index, text, f"x_reactor_{index:02d}", index * 2, likes=2 + index)

    # Conversation 2: a verified Telegram update produces mostly supportive reaction.
    tg_root = "demo-telegram-riverlink-verified"
    add_root(
        "telegram",
        tg_root,
        "Verified RiverLink notice: maintenance affects only 01:00-04:00. Morning service is scheduled normally. #RiverLinkUpdate",
        "NexusSIHDemo",
        18,
        61,
        12,
    )
    tg_replies = [
        "Thanks, this exact timing is helpful and clears the confusion.",
        "Confirmed. I checked the same notice and the morning service is normal.",
        "Great to finally have a reliable source instead of rumours.",
        "I support pinning this verified update so people see the correction first.",
        "This is good. Please keep the official link attached for trust.",
        "Glad the full-day shutdown message was corrected quickly.",
        "Useful update. Our group can stop worrying about the morning commute now.",
        "Verified information like this should be shared more than forwarded screenshots.",
        "Thank you. This is clear and credible.",
        "I was anxious earlier, but this clarification resolves it.",
        "Good correction. Please mention that the earlier viral message was unconfirmed.",
        "Support this update. Exact source and timing make it much easier to trust.",
    ]
    for index, text in enumerate(tg_replies, start=1):
        add_reply("telegram", tg_root, index, text, f"tg_reactor_{index:02d}", 19 + index, likes=1 + index // 2)

    # Conversation 3: neutral/mixed Reddit discussion demonstrates cross-platform opinions.
    reddit_root = "demo-reddit-techfest-root"
    add_root(
        "reddit",
        reddit_root,
        "TechFest demo registration opened today. What workshop track are students actually interested in? #TechFestLocal",
        "campus_forum_demo",
        30,
        37,
        10,
    )
    reddit_replies = [
        "AI and cybersecurity would be useful, but only if the workshop is hands-on.",
        "I would prefer AR/VR. The last session was fun and practical.",
        "The registration page is clear. No issue from my side.",
        "Please add an entrepreneurship track too; not everyone wants only coding.",
        "I am excited for the robotics track if hardware is actually available.",
        "Neutral on the tracks, but timings matter because they clash with labs.",
        "Good initiative. A beginner track would make it more inclusive.",
        "I disagree with keeping all sessions on one day. It becomes too rushed.",
        "Surprised data science is missing from the first list.",
        "The idea is good; publish final mentors before asking students to choose.",
    ]
    for index, text in enumerate(reddit_replies, start=1):
        add_reply("reddit", reddit_root, index, text, f"reddit_reactor_{index:02d}", 31 + index, likes=index % 5)

    return rows
