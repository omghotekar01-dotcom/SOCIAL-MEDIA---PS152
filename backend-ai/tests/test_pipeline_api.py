from fastapi.testclient import TestClient

from app.analytics.pipeline import analyze_events
from app.connectors.demo import load_demo_events
from app.db import store
from app.main import app


def test_seeded_pipeline_covers_official_core_components():
    events = load_demo_events()
    data = analyze_events(events)

    assert len(events) >= 15
    assert data["summary"]["events"] == len(events)
    assert set(data["evidence"]["required_platforms_present"]) == {"x", "telegram"}
    assert data["summary"]["required_platform_coverage_pct"] == 100.0
    assert data["narratives"]
    assert data["trends"]
    assert data["network"]["nodes"]
    assert data["demographics"]["publishable"] is True
    assert data["evidence"]["truthfulness_note"]
    assert any(narrative["cross_platform"] for narrative in data["narratives"])
    assert any(event["source_mode"] == "REPLAY" for event in data["events"])


def test_fastapi_seed_and_dashboard_endpoints():
    store.clear()
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    seeded = client.post("/api/demo/seed", json={"reset": True})
    assert seeded.status_code == 200
    assert seeded.json()["ingested"] >= 15

    summary = client.get("/api/dashboard/summary")
    assert summary.status_code == 200
    assert summary.json()["events"] >= 15
    assert summary.json()["mode_label"] == "REPLAY"

    narratives = client.get("/api/narratives")
    assert narratives.status_code == 200
    assert len(narratives.json()) >= 1

    network = client.get("/api/network")
    assert network.status_code == 200
    assert network.json()["metadata"]["node_count"] >= 10

    evidence = client.get("/api/evidence")
    assert evidence.status_code == 200
    assert evidence.json()["required_platform_coverage_pct"] == 100.0

    export = client.get("/api/export/events.csv")
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert "source_mode" in export.text.splitlines()[0]

    store.clear()


def test_missing_live_credentials_fail_gracefully_without_breaking_demo():
    client = TestClient(app)
    response = client.get("/api/platforms/status")
    assert response.status_code == 200
    body = response.json()
    assert "x" in body
    assert "telegram" in body
    assert body["replay"]["state"] == "READY"
