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
    res = client.get("/api/v1/incidents/SIH-2026-001")
    assert res.status_code == 200
    data = res.json()
    assert "incident" in data
    assert "detection" in data
    assert "origin_estimate" in data
    assert "attribution_scores" in data
    assert len(data["attribution_scores"]) >= 1
    assert data["attribution_scores"][0]["vessel_name"] == "PACIFIC VOYAGER"

def test_grounded_assistant():
    payload = {
        "incident_id": "SIH-2026-001",
        "query": "Why is Pacific Voyager suspicious?"
    }
    res = client.post("/api/v1/investigation/ask", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "PACIFIC VOYAGER" in data["answer"]
    assert "HIGH INVESTIGATION PRIORITY" in data["answer"]

def test_generate_report():
    res = client.post("/api/v1/reports/SIH-2026-001")
    assert res.status_code == 200
    data = res.json()
    assert "report_id" in data
    assert "content_markdown" in data
    assert "MARITIME INCIDENT INVESTIGATION REPORT" in data["content_markdown"]
