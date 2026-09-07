from __future__ import annotations

from app import analytics
from app.db import EventStore
from app.ps26152_demo import ps26152_seed_demo_events
from app.ps26152_intelligence import build_ps26152_intelligence


def _demo_store(tmp_path):
    store = EventStore(tmp_path / "ps26152-core.db")
    for incoming in ps26152_seed_demo_events():
        normalized, derived = analytics.enrich_event(incoming)
        store.insert(normalized, derived)
    analytics.assign_clusters(store)
    return store


def test_demo_represents_original_platform_priority_tiers(tmp_path):
    store = _demo_store(tmp_path)
    platforms = {event.platform for event in store.list_events(limit=None)}
    assert {"x", "telegram", "instagram", "facebook", "reddit", "youtube"} <= platforms


def test_multidimensional_timeline_contains_emotion_stance_and_reactions(tmp_path):
    store = _demo_store(tmp_path)
    rows = analytics.timeline(store.list_events(limit=None), 15)
    populated = [row for row in rows if row["count"] > 0]
    assert populated
    assert any(row.get("reaction_count", 0) > 0 for row in populated)
    assert all("emotions" in row for row in populated)
    assert all("supportive_share" in row and "against_share" in row for row in populated)
    assert all("sarcasm_mean" in row for row in populated)


def test_demographics_expose_four_required_aggregate_dimensions(tmp_path):
    store = _demo_store(tmp_path)
    result = analytics.demographics(store.list_events(limit=None))
    assert result["unique_anonymized_users"] > 0
    for key in ("language", "broad_geography", "professional_interests", "age_brackets"):
        assert key in result
        assert "coverage" in result[key]
        assert "minimum_group_size" in result[key]
    assert "behavior" in result["professional_interests"]["method"]


def test_network_contains_key_nodes_and_spread_over_time(tmp_path):
    store = _demo_store(tmp_path)
    network = analytics.build_network(store.list_events(limit=None))
    assert network["summary"]["nodes"] > 0
    assert network["summary"]["edges"] > 0
    assert "key_opinion_leader_candidates" in network
    assert "cross_community_flows" in network
    assert "spread_timeline" in network
    assert network["spread_timeline"]
    assert "edge_type_counts" in network


def test_single_audit_payload_covers_a_through_e(tmp_path):
    store = _demo_store(tmp_path)
    result = build_ps26152_intelligence(store)
    assert [item["id"] for item in result["requirements"]] == ["A", "B", "C", "D", "E"]
    assert result["collection"]["events"] == store.count()
    assert result["sentiment"]["reaction_events"] > 0
    assert result["demographics"]["unique_anonymized_users"] > 0
    assert result["trends"]["narratives"]
    assert result["links"]["summary"]["nodes"] > 0
