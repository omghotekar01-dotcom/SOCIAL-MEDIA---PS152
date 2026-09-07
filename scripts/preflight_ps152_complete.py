from __future__ import annotations

import ast
import sys
import tempfile
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

TEXT_CONTRACTS: dict[str, tuple[str, ...]] = {
    "backend-ai/app/__init__.py": (
        "telegram_rich_poll",
        "youtube_staged_search",
        "ps26152_timeline",
        "ps26152_demographics",
        "ps26152_network",
        "ps26152_seed_demo_events",
        "complete_overview",
        "complete_alerts",
    ),
    "backend-ai/app/telegram_rich.py": (
        "telegram_linked_discussion_comment",
        "discussion_reply",
        "is_automatic_forward",
        "forward_origin",
    ),
    "backend-ai/app/youtube_official.py": (
        "commentThreads",
        "parentId",
        "nextPageToken",
        "provider_exhaustive_pagination",
    ),
    "backend-ai/app/youtube_staged.py": (
        "fast_first_background_full",
        "background_collection_state",
        "background_collection_token",
        "max_comments_per_video=0",
    ),
    "backend-ai/app/ps26152_timeline.py": (
        "reaction_count",
        "supportive_share",
        "against_share",
        "sarcasm_mean",
        "emotions",
    ),
    "backend-ai/app/ps26152_demographics.py": (
        "language",
        "broad_geography",
        "professional_interests",
        "age_brackets",
        "observed-public-topic-behavior",
    ),
    "backend-ai/app/ps26152_network.py": (
        "key_opinion_leader_candidates",
        "cross_community_flows",
        "spread_timeline",
        "edge_type_counts",
        "direct_observed_edges",
    ),
    "frontend/src/PrototypeSourceCenter.tsx": (
        "YouTube — Full Public Conversation",
        "Telegram — Channel + Discussion Comments",
        "Append public mix",
        "Start 60s Live Watch",
        "5/5 requirement health",
    ),
    "frontend/src/TimelinePro.tsx": (
        "Conversation volume & sentiment movement",
        "Eight-emotion movement",
        "Emotion, stance & sarcasm fluctuation",
        "anxiety",
        "anger",
        "excitement",
        "sadness",
        "joy",
        "disgust",
        "surprise",
        "trust",
    ),
    "frontend/src/PS26152AuditPanel.tsx": (
        "Continuous Data Collection & Timeline Management",
        "Multi-Dimensional Sentiment Inference",
        "Automated Demographic Profiling",
        "Real-Time Trend & Topic Detection",
        "Link Analysis & Network Topology",
    ),
    "frontend/src/main.tsx": (
        "PrototypeSourceCenter",
        "PS26152AuditPanel",
        "AudiencePulsePanel",
        "prototype-source-center.css",
        "ps26152-audit.css",
    ),
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
            failures += fail(f"capability contract missing in {rel}: {', '.join(missing)}")
        else:
            ok(f"capability contract: {rel}")

    syntax_targets = [
        rel for rel in REQUIRED_FILES
        if rel.endswith(".py") and (ROOT / rel).exists()
    ]
    for rel in syntax_targets:
        try:
            ast.parse((ROOT / rel).read_text(encoding="utf-8"), filename=rel)
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

        runtime_modules = {
            "timeline": (analytics.timeline, "ps26152_timeline"),
            "demographics": (analytics.demographics, "ps26152_demographics"),
            "network": (analytics.build_network, "ps26152_network"),
            "demo": (analytics.seed_demo_events, "ps26152_demo"),
        }
        for label, (function, expected_module) in runtime_modules.items():
            if function.__module__.endswith(expected_module):
                ok(f"active runtime: {label} uses {expected_module}")
            else:
                failures += fail(
                    f"active runtime {label} is stale: {function.__module__}.{function.__name__}"
                )

        inferred = analytics.infer_text(
            "I am shocked, worried and angry but I trust the verified evidence"
        )
        required_emotions = {
            "anxiety", "anger", "excitement", "sadness",
            "joy", "disgust", "surprise", "trust",
        }
        emotions = set((inferred.get("emotion_scores") or {}).keys())
        if required_emotions.issubset(emotions):
            ok("runtime B: all 8 emotion dimensions exposed")
        else:
            failures += fail(
                "runtime B: missing emotion dimensions: "
                + ", ".join(sorted(required_emotions - emotions))
            )

        collector = AdvancedCollectorStartRequest(query="preflight")
        if (
            collector.enable_telegram_public
            and collector.enable_bluesky
            and collector.enable_reddit
            and collector.enable_mastodon
        ):
            ok("runtime A: continuous free/public collector defaults are enabled")
        else:
            failures += fail("runtime A: continuous free/public collector defaults are incomplete")
        if not collector.enable_x:
            ok("runtime A: official X continuous polling remains explicit opt-in")
        else:
            failures += fail("runtime A: official X polling must remain opt-in")

        with tempfile.TemporaryDirectory(prefix="nexus-preflight-") as tmp:
            store = EventStore(Path(tmp) / "ps26152.db")
            demo = ps26152_seed_demo_events()
            for incoming in demo:
                normalized, derived = analytics.enrich_event(incoming)
                store.insert(normalized, derived)
            analytics.assign_clusters(store)
            events = store.list_events(limit=None)

            platforms = {event.platform for event in events}
            required_platforms = {
                "x", "telegram", "instagram", "facebook", "reddit", "youtube"
            }
            if required_platforms.issubset(platforms):
                ok("runtime A: disclosed six-platform jury dataset is represented")
            else:
                failures += fail(
                    "runtime A: jury dataset missing platforms: "
                    + ", ".join(sorted(required_platforms - platforms))
                )

            reactions = [event for event in events if event.parent_event_id]
            if reactions:
                ok(f"runtime A/B: {len(reactions)} linked comments/replies available")
            else:
                failures += fail("runtime A/B: no linked reaction evidence in demo")

            timeline = analytics.timeline(events, 15)
            populated = [row for row in timeline if int(row.get("count", 0)) > 0]
            if populated and all(
                "emotions" in row
                and "supportive_share" in row
                and "against_share" in row
                and "sarcasm_mean" in row
                for row in populated
            ):
                ok("runtime B: nuanced timeline exposes emotion + stance + sarcasm")
            else:
                failures += fail("runtime B: nuanced timeline output is incomplete")

            demographics = analytics.demographics(events)
            demographic_keys = {
                "language", "broad_geography", "professional_interests", "age_brackets"
            }
            if demographic_keys.issubset(demographics.keys()):
                ok("runtime C: four privacy-safe demographic dimensions exposed")
            else:
                failures += fail("runtime C: demographic dimensions are incomplete")

            narratives = analytics.narrative_summaries(store)
            if narratives:
                ok(f"runtime D: {len(narratives)} ranked narrative(s) produced")
            else:
                failures += fail("runtime D: no narrative/trend output produced")

            network = analytics.build_network(events)
            summary = network.get("summary") or {}
            if int(summary.get("nodes", 0)) > 0 and int(summary.get("edges", 0)) > 0:
                ok(
                    "runtime E: network has "
                    f"{summary.get('nodes', 0)} nodes / {summary.get('edges', 0)} edges"
                )
            else:
                failures += fail("runtime E: interaction network has no usable topology")
            for key in (
                "key_opinion_leader_candidates",
                "cross_community_flows",
                "spread_timeline",
                "edge_type_counts",
            ):
                if key not in network:
                    failures += fail(f"runtime E: network missing {key}")

            intelligence = build_ps26152_intelligence(store)
            ids = [item.get("id") for item in intelligence.get("requirements", [])]
            if ids == ["A", "B", "C", "D", "E"]:
                ok("runtime A-E: unified requirement intelligence payload is complete")
            else:
                failures += fail(f"runtime A-E: requirement payload ids are {ids}")

    except Exception as exc:
        failures += fail(f"runtime SIH26152 validation crashed: {type(exc).__name__}: {exc}")

    print("\nRESULT:")
    if failures:
        print(f"SIH26152 COMPLETENESS CHECK FAILED with {failures} issue(s).")
        return 1

    print(
        "SIH26152 COMPLETENESS CHECK PASSED: A-E runtime wiring, reactions, "
        "8-emotion sentiment, privacy-safe demographics, trends and network spread are active."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
