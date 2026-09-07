from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTRACTS: dict[str, tuple[str, ...]] = {
    "frontend/src/TimelinePro.tsx": (
        "backendHasObservedVolume",
        "bucketEvents(events)",
        "sparse = data.length <= 4",
        "Conversation volume & sentiment movement",
        "Eight-emotion movement",
        "Emotion, stance & sarcasm fluctuation",
        "minWidth={280}",
        "isAnimationActive={false}",
        "anxiety",
        "anger",
        "excitement",
        "sadness",
        "joy",
        "disgust",
        "surprise",
        "trust",
    ),
    "frontend/src/NarrativeGraph.tsx": (
        "Narrative propagation graph",
        "ComposedChart",
        "newEvidence",
        "cumulative",
        "positive",
        "negative",
        "neutral",
        "sparse = data.length <= 4",
        "minWidth={280}",
        "isAnimationActive={false}",
    ),
    "frontend/src/AppPro.tsx": (
        "import NarrativeGraph from './NarrativeGraph'",
        "<NarrativeGraph detail={detail} />",
        "<TimelinePro points={timeline} events={events} />",
    ),
    "frontend/src/chart-visibility.css": (
        ".timeline-chart-shell",
        ".narrative-graph-shell",
        ".recharts-responsive-container",
        "visibility:visible!important",
        "min-height:320px!important",
    ),
    "frontend/src/main.tsx": (
        "import './chart-visibility.css'",
    ),
}


def main() -> int:
    print("NEXUS CHART VISIBILITY CONTRACT\n")
    failures = 0
    for rel, tokens in CONTRACTS.items():
        path = ROOT / rel
        if not path.exists():
            print(f"[FAIL] missing chart file: {rel}")
            failures += 1
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        missing = [token for token in tokens if token not in text]
        if missing:
            print(f"[FAIL] chart contract missing in {rel}: {', '.join(missing)}")
            failures += 1
        else:
            print(f"[PASS] chart contract: {rel}")

    print()
    if failures:
        print(f"CHART VISIBILITY CONTRACT FAILED with {failures} issue(s).")
        return 1
    print("CHART VISIBILITY CONTRACT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
