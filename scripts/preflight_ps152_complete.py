from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend-ai"
sys.path.insert(0, str(BACKEND))

REQUIRED_FILES = [
    "backend-ai/app/__init__.py",
    "backend-ai/app/advanced_analytics.py",
    "backend-ai/app/reaction_engine.py",
    "backend-ai/app/complete_overview.py",
    "backend-ai/app/complete_alerts.py",
    "backend-ai/app/advanced_collector.py",
    "backend-ai/app/telegram_rich.py",
    "backend-ai/app/youtube_official.py",
    "backend-ai/app/youtube_staged.py",
    "backend-ai/app/ps26152_timeline.py",
    "backend-ai/app/ps26152_demographics.py",
    "backend-ai/app/ps26152_network.py",
    "backend-ai/app/ps26152_demo.py",
    "backend-ai/app/ps26152_intelligence.py",
    "backend-ai/tests/test_ps26152_core.py",
    "backend-ai/tests/test_telegram_polling.py",
    "backend-ai/tests/test_youtube_official.py",
    "backend-ai/tests/test_youtube_staged.py",
    "frontend/src/ReactionIntelligence.tsx",
    "frontend/src/AudiencePulsePanel.tsx",
    "frontend/src/PS26152AuditPanel.tsx",
    "frontend/src/PrototypeSourceCenter.tsx",
    "frontend/src/TimelinePro.tsx",
    "frontend/src/NetworkPro.tsx",
    "frontend/src/PostExplorer.tsx",
    "frontend/src/main.tsx",
    "frontend/src/prototype-source-center.css",
    "frontend/src/ps26152-audit.css",
    "frontend/src/ps26152-network.css",
    "docs/SIH26152_COMPLETE_REQUIREMENT_MAP.md",
    "docs/PS26152_TRACEABILITY.md",
]

TEXT_CONTRACTS = {
    "backend-ai/app/__init__.py": [
        "telegram_rich_poll",
        "youtube_staged_search",
        "ps26152_timeline",
        "ps26152_demographics",
        "ps26152_network",
        "ps26152_seed_demo_events",
        "complete_overview",
        "complete_alerts",
    ],
    "backend-ai/app/advanced_analytics.py": [
        "EMOTION_LEXICONS_V2",
        '"anxiety"', '"anger"', '"excitement"', '"sadness"',
        '"joy"', '"disgust"', '"surprise"', '"trust"',
        "predicted_next_bucket_volume",
        "forecast_scope",
    ],
    "backend-ai/app/ps26152_timeline.py": [
        "reaction_count",
        "supportive_share",
        "against_share",
        "sarcasm_mean",
        "emotions",
    ],
    "backend-ai/app/ps26152_demographics.py": [
        "language",
        "broad_geography",
        "professional_interests",
        "age_brackets",
        "observed-public-topic-behavior",
        "k=",
    ],
    "backend-ai/app/ps26152_network.py": [
        "key_opinion_leader_candidates",
        "cross_community_flows",
        "spread_timeline",
        "edge_type_counts",
        "direct_observed_edges",
    ],
    "backend-ai/app/telegram_rich.py": [
        "telegram_linked_discussion_comment",
        "discussion_reply",
        "is_automatic_forward",
        "forward_origin",
    ],
    "backend-ai/app/youtube_staged.py": [
        "fast_first_background_full",
        "background_collection_state",
        "background_collection_token",
        "max_comments_per_video=0",
    ],
    "backend-ai/app/youtube_official.py": [
        "commentThreads",
        "parentId",
        "nextPageToken",
        "provider_exhaustive_pagination",
    ],
    "backend-ai/app/reaction_engine.py": [
        "workspace_reaction_overview",
        "risk_score",
        "ESCALATING",
        "root-post sentiment",
    ],
    "backend-ai/app/ps26152_demo.py": [
        '"instagram"',
        '"facebook"',
        'source_mode="REPLAY"',
    ],
    "frontend/src/PrototypeSourceCenter.tsx": [
        "YouTube — Full Public Conversation",
        "Telegram — Channel + Discussion Comments",
        "Append public mix",
        "Start 60s Live Watch",
        "Original Problem Statement — 5/5 Health",
    ],
    "frontend/src/PS26152AuditPanel.tsx": [
        "Continuous Data Collection & Timeline Management",
        "Multi-Dimensional Sentiment Inference",
        "Automated Demographic Profiling",
        "Real-Time Trend & Topic Detection",
        "Link Analysis & Network Topology",
    ],
    "frontend/src/main.tsx": [
        "PrototypeSourceCenter",
        "PS26152AuditPanel",
        "AudiencePulsePanel",
        "prototype-source-center.css",
        "ps26152-audit.css",
    ],
    "docs/SIH26152_COMPLETE_REQUIREMENT_MAP.md": [
        "Continuous Data Collection",
        "Multi-Dimensional Sentiment",
        "Automated Demographic Profiling",
        "Real-Time Trend",
        "Link Analysis",
    ],
}


def fail(message: str) -> int:
    print(f"[FAIL] {message}")
    return 1


def ok(message: str) -> None:
    print(f"[PASS] {message}")


def main() -> int:
    print("NEXUS / SIH26152 REQUIREMENT-COMPLETENESS CHECK\n")
    failures = 0

    for rel in REQUIRED_FILES:
        path = ROOT / rel
        if path.exists():
            ok(f"required capability file: {rel}")
        else:
            failures += fail(f"missing capability file: {rel}")

    for rel, tokens in TEXT_CONTRACTS.items():
        path = ROOT / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        missing = [token for token in tokens if token not in text]
        if missing:
            failures += fail(f"SIH contract missing in {rel}: {', '.join(missing)}")
        else:
            ok(f"SIH contract: {rel}")

    syntax_targets = [rel for rel in REQUIRED_FILES if rel.endswith(".py")]
    for rel in syntax_targets:
        path = ROOT / rel
        if not path.exists():
            continue
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except SyntaxError as exc:
            failures += fail(f"Python syntax {rel}:{exc.lineno}: {exc.msg}")
        else:
            ok(f"Python syntax: {rel}")

    try:
        from app import analytics
        from app.advanced_collector import AdvancedCollectorStartRequest
        from app.db import EventStore
        from app.ps26152_demo import ps26152_seed_demo_events
        from app.ps26152_intelligence import build_ps26152_intelligence

        # Verify the package actually wired the SIH-specific implementations,
        # rather than merely having those files present in the repository.
        if analytics.timeline.__module__.endswith("ps26152_timeline"):
            ok("active runtime: PS26152 nuanced timeline is wired")
        else:
            failures += fail(f"active timeline is stale: {analytics.timeline.__module__}.{analytics.timeline.__name__}")
        if analytics.demographics.__module__.endswith("ps26152_demographics"):
            ok("active runtime: PS26152 demographics is wired")
        else:
            failures += fail(f"active demographics is stale: {analytics.demographics.__module__}.{analytics.demographics.__name__}")
        if analytics.build_network.__module__.endswith("ps26152_network"):
            ok("active runtime: PS26152 network/spread analysis is wired")
        else:
            failures += fail(f"active network is stale: {analytics.build_network.__module__}.{analytics.build_network.__name__}")
        if analytics.seed_demo_events.__module__.endswith("ps26152_demo"):
            ok("active runtime: six-platform disclosed jury demo is wired")
        else:
            failures += fail(f"active demo seed is stale: {analytics.seed_demo_events.__module__}.{analytics.seed_demo_events.__name__}")

        inferred = analytics.infer_text("I am shocked, worried and angry but I trust the verified evidence")
        emotions = inferred.get("emotion_scores", {})
        required_emotions = {"anxiety", "anger", "excitement", "sadness", "joy", "disgust", "surprise", "trust"}
        if required_emotions.issubset(emotions):
            ok("runtime B: all 8 emotion dimensions exposed")
        else:
            failures += fail("runtime B: 8-emotion contract incomplete")

        config = AdvancedCollectorStartRequest(query="preflight")
        if config.enable_telegram and config.enable_telegram_public and config.enable_bluesky and config.enable_reddit and config.enable_mastodon:
            ok("runtime A: Telegram Bot + public/multi-source collector defaults available")
        else:
            failures += fail("runtime A: continuous collector defaults are incomplete")
        if not config.enable_x:
            ok("runtime source integrity: official X continuous polling remains explicit opt-in")
        else:
            failures += fail("official X continuous polling must remain opt-in")

        store = EventStore(ROOT / ".preflight-ps26152.db")
        store.reset()
        for incoming in ps26152_seed_demo_events():
            normalized, derived = analytics.enrich_event(incoming)
            store.insert(normalized, derived)
        analytics.assign_clusters(store)

        events = store.list_events(limit=None)
        platforms = {event.platform for event in events}
        required_platforms = {"x", "telegram", "instagram", "facebook", "reddit", "youtube"}
        if required_platforms <= platforms:
            ok("runtime A: original source-priority tiers represented in disclosed demo")
        else:
            failures += fail("runtime A: demo missing platforms: " + ", ".join(sorted(required_platforms - platforms)))

        timeline_rows = [row for row in analytics.timeline(events, 15) if row.get("count", 0) > 0]
        if timeline_rows and any(row.get("reaction_count", 0) > 0 for row in timeline_rows) and all("emotions" in row and "sarcasm_mean" in row for row in timeline_rows):
            ok("runtime B: timeline carries reaction/emotion/stance/sarcasm fields")
        else:
            failures += fail("runtime B: nuanced sentiment timeline fields are not active")

        demographics = analytics.demographics(events)
        demo_dims = {"language", "broad_geography", "professional_interests", "age_brackets"}
        if demo_dims <= set(demographics):
            ok("runtime C: four aggregate demographic dimensions exposed")
        else:
            failures += fail("runtime C: demographic dimensions incomplete")

        narratives = analytics.narrative_summaries(store)
        if narratives and "predicted_next_bucket_volume" in narratives[0]["trend"]:
            ok("runtime D: ranked narratives + near-term forecast fields exposed")
        else:
            failures += fail("runtime D: trend/forecast output incomplete")

        network = analytics.build_network(events)
        required_network_fields = {"key_opinion_leader_candidates", "cross_community_flows", "spread_timeline", "edge_type_counts"}
        if network.get("summary", {}).get("edges", 0) > 0 and required_network_fields <= set(network):
            ok("runtime E: influence/community/spread link analysis exposed")
        else:
            failures += fail("runtime E: link-analysis propagation output incomplete")

        intelligence = build_ps26152_intelligence(store)
        if [item["id"] for item in intelligence.get("requirements", [])] == ["A", "B", "C", "D", "E"]:
            ok("runtime 5/5: single audit payload covers A through E")
        else:
            failures += fail("runtime 5/5 audit payload is incomplete")

        try:
            (ROOT / ".preflight-ps26152.db").unlink(missing_ok=True)
        except Exception:
            pass
    except Exception as exc:
        failures += fail(f"runtime SIH capability import/execution: {exc}")

    print("\nRESULT:")
    if failures:
        print(f"SIH26152 COMPLETENESS CHECK FAILED with {failures} issue(s).")
        return 1
    print("SIH26152 COMPLETENESS CHECK PASSED: A-E runtime wiring, comments/reactions, nuanced sentiment, demographics, trend prediction and link-propagation outputs are active.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
