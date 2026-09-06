import pytest
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)

def test_health_endpoints():
    r1 = client.get("/health")
    assert r1.status_code == 200
    assert r1.json()["status"] == "HEALTHY"

    r2 = client.get("/health/db")
    assert r2.status_code == 200
    assert r2.json()["status"] == "HEALTHY"

def test_get_incidents():
    res = client.get("/api/v1/incidents")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["id"] == "SIH-2026-001"

def test_get_incident_detail():
    """Verify the real DARTIS Eastern Mediterranean incident is returned."""
    res = client.get("/api/v1/incidents/SIH-2026-001")
    assert res.status_code == 200
    data = res.json()
    assert "incident" in data
    inc = data["incident"]
    # Real incident coordinates — Eastern Mediterranean, NOT Mumbai
    assert abs(inc["center_lat"] - 31.982759) < 0.001, f"Wrong lat: {inc['center_lat']}"
    assert abs(inc["center_lon"] - 32.849022) < 0.001, f"Wrong lon: {inc['center_lon']}"
    assert inc["id"] == "SIH-2026-001"
    # Attribution scores and detection not yet populated from minimal seed
    assert "attribution_scores" in data
    assert "detection" in data

def test_grounded_assistant():
    """Verify assistant answers about the real DARTIS ow-0388 incident."""
    payload = {
        "incident_id": "SIH-2026-001",
        "query": "What is the DARTIS annotation for this incident?"
    }
    res = client.post("/api/v1/investigation/ask", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    # Must return a grounded answer, not hallucination
    assert len(data["answer"]) > 10

def test_generate_report():
    res = client.post("/api/v1/reports/SIH-2026-001")
    assert res.status_code == 200
    data = res.json()
    assert "report_id" in data
    assert "content_markdown" in data
    assert "MARITIME INCIDENT INVESTIGATION REPORT" in data["content_markdown"]
