from datetime import datetime, timezone

from app.schemas import SocialEvent
from app.stable_views import stable_network, stable_timeline


def make_event(event_id: str, author: str, text: str, *, hashtags=None, topics=None, platform='telegram') -> SocialEvent:
    return SocialEvent(
        id=event_id,
        platform=platform,
        source_event_id=f'src-{event_id}',
        event_type='post',
        author_platform_id=author,
        author_pseudo_id=author,
        author_display=author,
        text=text,
        created_at=datetime(2026, 9, 7, 16, 0, tzinfo=timezone.utc),
        hashtags=hashtags or [],
        topic_terms=topics or [],
        engagement={},
        public_profile={},
        source_mode='LIVE',
        emotion_scores={},
    )


def test_single_bucket_timeline_is_padded_for_visible_chart():
    event = make_event('1', 'alpha', 'RiverLink update')
    event.sentiment_label = 'neutral'
    rows = stable_timeline([event], 15)
    assert len(rows) == 3
    assert [row['count'] for row in rows] == [0, 1, 0]
    assert rows[1]['platforms']['telegram'] == 1


def test_network_adds_only_explainable_codiscussion_edges():
    one = make_event('1', 'alpha', 'Shinchan nostalgia discussion', hashtags=['shinchan'], topics=['shinchan', 'nostalgia'])
    two = make_event('2', 'beta', 'Shinchan nostalgia fans', hashtags=['shinchan'], topics=['shinchan', 'nostalgia'])
    result = stable_network([one, two])
    assert result['summary']['nodes'] == 2
    assert result['summary']['edges'] >= 1
    assert any('shared-hashtag' in edge['types'] or 'shared-topic' in edge['types'] for edge in result['edges'])


def test_network_does_not_invent_edge_without_shared_signal():
    one = make_event('1', 'alpha', 'Topic A', topics=['alpha', 'one'])
    two = make_event('2', 'beta', 'Topic B', topics=['beta', 'two'])
    result = stable_network([one, two])
    assert result['summary']['nodes'] == 2
    assert result['summary']['edges'] == 0
