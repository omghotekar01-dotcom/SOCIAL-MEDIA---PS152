from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


BASE = "http://127.0.0.1:8000"


def request(path: str, *, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        method=method,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def check(name: str, condition: bool, detail: str = ""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))
    if not condition:
        raise AssertionError(name)


def main() -> int:
    try:
        health = request("/health")
        check("health", health.get("status") == "ok")

        seed = request("/api/demo/seed", method="POST", body={"reset": True})
        check("demo seed", seed.get("inserted", 0) >= 50, f"inserted={seed.get('inserted')}")

        overview = request("/api/overview")
        check("overview events", overview.get("total_events", 0) >= 50)
        check("multiple platforms", len(overview.get("platform_mix", {})) >= 3)

        narratives = request("/api/narratives").get("narratives", [])
        check("narratives", len(narratives) >= 3, f"count={len(narratives)}")

        timeline = request("/api/timeline").get("points", [])
        check("timeline", len(timeline) >= 3, f"buckets={len(timeline)}")

        network = request("/api/network")
        check("network nodes", network.get("summary", {}).get("nodes", 0) >= 10)
        check("network edges", network.get("summary", {}).get("edges", 0) >= 1)

        demographics = request("/api/demographics")
        check("aggregate demographics", "language" in demographics and "privacy_note" in demographics)
        check("no individual demographic table", "users" not in demographics)

        alert_payload = request("/api/alerts")
        alerts = alert_payload.get("alerts", [])
        print(f"[INFO] explainable alerts generated: {len(alerts)}")
        if alerts:
            check("alert evidence", len(alerts[0].get("evidence_event_ids", [])) > 0)
            check("alert explanation", len(alerts[0].get("why_triggered", [])) > 0)

        statuses = request("/api/connectors/status").get("connectors", [])
        names = {row.get("platform") for row in statuses}
        check("X connector declared", "x" in names)
        check("Telegram connector declared", "telegram" in names)
        check("YouTube connector declared", "youtube" in names)
        check("Instagram connector declared", "instagram" in names)

        print("\nNEXUS smoke test passed. Core SIH26152 demo path is operational.")
        return 0
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"[FAIL] Cannot reach NEXUS at {BASE}: {exc}")
        return 2
    except AssertionError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
