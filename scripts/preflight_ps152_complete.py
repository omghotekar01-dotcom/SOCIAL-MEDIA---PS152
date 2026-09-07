from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend-ai"
sys.path.insert(0, str(BACKEND))

REQUIRED_FILES = [
    "backend-ai/app/advanced_analytics.py",
    "backend-ai/app/reaction_engine.py",
    "backend-ai/app/complete_overview.py",
    "backend-ai/app/complete_alerts.py",
    "backend-ai/app/complete_demo.py",
    "backend-ai/app/advanced_collector.py",
    "backend-ai/app/conversation_connectors.py",
    "backend-ai/app/x_embed_resilience.py",
    "backend-ai/tests/test_advanced_analytics.py",
    "backend-ai/tests/test_advanced_collector.py",
    "backend-ai/tests/test_complete_demo.py",
    "frontend/src/ReactionIntelligence.tsx",
    "frontend/src/AudiencePulsePanel.tsx",
    "frontend/src/LiveWatchPanel.tsx",
    "frontend/src/conversation-intelligence.css",
    "frontend/src/audience-pulse.css",
    "frontend/src/live-watch.css",
    "frontend/src/FreeConnectorPanel.tsx",
    "frontend/src/PostExplorer.tsx",
    "frontend/src/main.tsx",
    "docs/SIH26152_COMPLETE_REQUIREMENT_MAP.md",
]

TEXT_CONTRACTS = {
    "backend-ai/app/advanced_analytics.py": [
        "EMOTION_LEXICONS_V2",
        '"anxiety"',
        '"anger"',
        '"excitement"',
        '"sadness"',
        '"joy"',
        '"disgust"',
        '"surprise"',
        '"trust"',
        "explicit-self-declared-age-only",
        "predicted_next_bucket_volume",
        "forecast_scope",
    ],
    "backend-ai/app/reaction_engine.py": [
        "workspace_reaction_overview",
        "risk_score",
        "ESCALATING",
        "root-post sentiment",
    ],
    "backend-ai/app/complete_overview.py": [
        "root_sentiment_mix",
        "reaction_sentiment_mix",
        "reaction_stance_mix",
        "public opinion",
    ],
    "backend-ai/app/complete_alerts.py": [
        "complete_alerts",
        "AUDIENCE REACTION",
        "wrongdoing or intent",
    ],
    "backend-ai/app/complete_demo.py": [
        "fictional_reaction_demo",
        "demo-x-riverlink-root",
        "demo-telegram-riverlink-verified",
        "demo-reddit-techfest-root",
        'source_mode="REPLAY"',
    ],
    "backend-ai/app/advanced_collector.py": [
        "enable_telegram_public",
        "enable_bluesky",
        "enable_reddit",
        "enable_mastodon",
        "enable_x: bool = False",
        "connectors.youtube_search",
    ],
    "frontend/src/ReactionIntelligence.tsx": [
        "PUBLIC REACTION INTELLIGENCE",
        "Negative / positive",
        "STANCE",
        "reaction risk / 100",
    ],
    "frontend/src/AudiencePulsePanel.tsx": [
        "Public reaction pulse",
        "CONTENT VS AUDIENCE",
        "8-DIMENSION EMOTION LAYER",
        "overall_against_share",
    ],
    "frontend/src/LiveWatchPanel.tsx": [
        "CONTINUOUS COLLECTION",
        "Telegram monitored channels",
        "Bluesky + replies",
        "Reddit + comments",
        "X official recent search",
    ],
    "frontend/src/FreeConnectorPanel.tsx": [
        "Manual X Conversation Import",
        "manual_transcription",
        "Add post + replies to NEXUS",
        "source_mode: 'IMPORT'",
    ],
    "frontend/src/PostExplorer.tsx": [
        "ReactionIntelligence",
        "content_disclosure",
        "analyst_manual_x_import",
    ],
    "frontend/src/main.tsx": [
        "AudiencePulsePanel",
        "LiveWatchPanel",
        "FreeConnectorPanel",
        "audience-pulse.css",
        "live-watch.css",
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

    for rel in [
        "backend-ai/app/advanced_analytics.py",
        "backend-ai/app/reaction_engine.py",
        "backend-ai/app/complete_overview.py",
        "backend-ai/app/complete_alerts.py",
        "backend-ai/app/complete_demo.py",
        "backend-ai/app/advanced_collector.py",
        "backend-ai/app/conversation_connectors.py",
        "backend-ai/app/x_embed_resilience.py",
    ]:
        path = ROOT / rel
        if path.exists():
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            except SyntaxError as exc:
                failures += fail(f"Python syntax {rel}:{exc.lineno}: {exc.msg}")
            else:
                ok(f"Python syntax: {rel}")

    try:
        from app.advanced_analytics import advanced_infer_text
        from app.advanced_collector import AdvancedCollectorStartRequest
        from app.complete_demo import complete_seed_demo_events

        inferred = advanced_infer_text("I am shocked, worried and angry but I trust the verified evidence")
        emotions = inferred.get("emotion_scores", {})
        required_emotions = {"anxiety", "anger", "excitement", "sadness", "joy", "disgust", "surprise", "trust"}
        if required_emotions.issubset(emotions):
            ok("runtime emotion contract: 8 dimensions exposed")
        else:
            failures += fail("runtime emotion contract does not expose all 8 dimensions")

        config = AdvancedCollectorStartRequest(query="preflight")
        if config.enable_telegram_public and config.enable_bluesky and config.enable_reddit and config.enable_mastodon:
            ok("runtime continuous free/public collector defaults")
        else:
            failures += fail("continuous collector defaults do not cover core free/public sources")
        if not config.enable_x:
            ok("runtime cost guard: official X continuous polling is opt-in")
        else:
            failures += fail("official X continuous polling must remain opt-in")

        demo = complete_seed_demo_events()
        linked_replies = [event for event in demo if event.event_type == "reply" and event.parent_event_id]
        if len(linked_replies) >= 30 and all(event.source_mode == "REPLAY" for event in linked_replies):
            ok("runtime jury demo: linked audience reactions are present and disclosed as REPLAY")
        else:
            failures += fail("jury demo does not contain enough linked, disclosed reaction evidence")
    except Exception as exc:
        failures += fail(f"runtime SIH capability import: {exc}")

    print("\nRESULT:")
    if failures:
        print(f"SIH26152 COMPLETENESS CHECK FAILED with {failures} issue(s).")
        return 1
    print("SIH26152 COMPLETENESS CHECK PASSED: continuous collection, sentiment/emotion, demographics, trends, public reactions, explainable alerts and link-analysis contracts are present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
