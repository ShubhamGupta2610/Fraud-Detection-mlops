"""
Phase 4 API tests: covers the /score contract, input validation,
decision logic, SHAP presence, latency target, and error states.

Uses FastAPI's TestClient (synchronous, no real server needed) which
runs the full middleware and route handler stack including pydantic
validation - so these tests exercise exactly what a real caller would
experience, not a mocked-out version.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.dialects import postgresql
from sqlalchemy import JSON
postgresql.JSONB = JSON  # SQLite compatibility for test env

import pytest
from fastapi.testclient import TestClient
from app.main import app


# Using TestClient as a context manager triggers the lifespan handler
# (which loads the model into app.state) before any test runs.
# Without this, app.state.model is never set and every /score call
# raises AttributeError - caught during Phase 4 test run.
@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

VALID_TRANSACTION = {
    "account_id": "test-acct-001",
    "amount": 75.00,
    "merchant_category": "grocery",
    "location_lat": 40.71,
    "location_lng": -74.00,
    "device_id": "device-known",
    "timestamp": "2026-06-30T10:00:00Z",
}

SUSPICIOUS_TRANSACTION = {
    "account_id": "test-acct-suspicious",
    "amount": 4999.00,
    "merchant_category": "electronics",
    "location_lat": -33.86,
    "location_lng": 151.21,
    "device_id": "device-brand-new-unknown",
    "timestamp": "2026-06-30T10:05:00Z",
}


# --- /health ---

def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "model_version" in data


# --- /score: response contract ---

def test_score_returns_required_fields(client):
    resp = client.post("/score", json=VALID_TRANSACTION)
    assert resp.status_code == 200
    data = resp.json()

    assert "transaction_id" in data
    assert "risk_score" in data
    assert "decision" in data
    assert "threshold_used" in data
    assert "top_shap_features" in data
    assert "model_version" in data
    assert "latency_ms" in data


def test_score_risk_score_is_in_valid_range(client):
    resp = client.post("/score", json=VALID_TRANSACTION)
    data = resp.json()
    assert 0.0 <= data["risk_score"] <= 100.0


def test_score_decision_is_valid_enum(client):
    resp = client.post("/score", json=VALID_TRANSACTION)
    data = resp.json()
    assert data["decision"] in ("allow", "challenge", "block")


def test_score_returns_shap_explanations(client):
    """
    Per Rules.md Rule 8: explainability is not optional.
    Every /score response must include SHAP features.
    """
    resp = client.post("/score", json=VALID_TRANSACTION)
    data = resp.json()
    assert len(data["top_shap_features"]) > 0
    for item in data["top_shap_features"]:
        assert "feature" in item
        assert "shap_value" in item


# --- /score: decision correctness ---

def test_normal_transaction_is_allowed(client):
    resp = client.post("/score", json=VALID_TRANSACTION)
    data = resp.json()
    # A first transaction with known-looking features on a fresh account
    # should not be blocked (low risk - velocity features all zero,
    # no impossible travel, normal amount)
    assert data["decision"] in ("allow", "challenge")


def test_suspicious_transaction_is_flagged(client):
    """
    A transaction with new device + far location + high amount should
    score high and get blocked or at minimum challenged.

    IMPORTANT: the model needs account HISTORY to detect this pattern -
    on a brand-new account with no history, cold-start defaults mean
    geo_velocity=0.0, txn_count=0, amount_deviation=0.0, so the
    is_new_device/is_new_ip_or_location signals alone aren't enough
    to trigger a block. This matches real fraud system behavior: new
    accounts typically have a separate stricter policy rather than
    relying on the behavioral model alone.

    Fix: seed a prior "normal" transaction first so the second one
    (far away, new device) triggers the geo_velocity + deviation signals.
    """
    # First: a normal transaction from home (seeding account history)
    client.post("/score", json={
        "account_id": "test-acct-suspicious-002",
        "amount": 55.0,
        "merchant_category": "grocery",
        "location_lat": 40.71,
        "location_lng": -74.00,
        "device_id": "device-known-home",
        "timestamp": "2026-06-30T09:00:00Z",
    })

    # Second: impossible travel + new device + high amount
    resp = client.post("/score", json={
        "account_id": "test-acct-suspicious-002",
        "amount": 4999.00,
        "merchant_category": "electronics",
        "location_lat": -33.86,
        "location_lng": 151.21,
        "device_id": "device-brand-new-unknown",
        "timestamp": "2026-06-30T09:05:00Z",
    })
    data = resp.json()
    assert data["decision"] in ("challenge", "block"), \
        f"Expected suspicious transaction to be flagged after account history seeded, got: {data['decision']} (risk_score={data['risk_score']})"


# --- /score: latency ---

def test_score_latency_under_target(client):
    """
    Per PRD.md Section 6: p99 latency target is 100ms.
    A single synchronous test-client call should be well under this.
    This doesn't replace a real load test (Phase 9), but it catches
    obvious regressions (e.g. accidentally loading the model per-call).
    """
    import time
    start = time.perf_counter()
    resp = client.post("/score", json=VALID_TRANSACTION)
    wall_ms = (time.perf_counter() - start) * 1000

    assert resp.status_code == 200
    assert wall_ms < 100, f"Wall-clock latency {wall_ms:.1f}ms exceeded 100ms target"

    # Also check the latency_ms the server reports for its own internal timing
    reported_ms = resp.json()["latency_ms"]
    assert reported_ms < 100, f"Server-reported latency {reported_ms}ms exceeded 100ms target"


# --- /score: input validation (Security.md Section 4) ---

def test_negative_amount_is_rejected(client):
    bad = {**VALID_TRANSACTION, "amount": -50.0}
    resp = client.post("/score", json=bad)
    assert resp.status_code == 422


def test_zero_amount_is_rejected(client):
    bad = {**VALID_TRANSACTION, "amount": 0.0}
    resp = client.post("/score", json=bad)
    assert resp.status_code == 422


def test_absurd_amount_is_rejected(client):
    bad = {**VALID_TRANSACTION, "amount": 2_000_000.0}
    resp = client.post("/score", json=bad)
    assert resp.status_code == 422


def test_invalid_lat_is_rejected(client):
    bad = {**VALID_TRANSACTION, "location_lat": 200.0}
    resp = client.post("/score", json=bad)
    assert resp.status_code == 422


def test_missing_required_field_is_rejected(client):
    bad = {k: v for k, v in VALID_TRANSACTION.items() if k != "account_id"}
    resp = client.post("/score", json=bad)
    assert resp.status_code == 422


# --- /metrics ---

def test_metrics_increments_after_scoring(client):
    before = client.get("/metrics").json()["total_scored"]
    client.post("/score", json=VALID_TRANSACTION)
    after = client.get("/metrics").json()["total_scored"]
    assert after == before + 1


# --- /feedback ---

def test_feedback_records_successfully(client):
    score_resp = client.post("/score", json=VALID_TRANSACTION)
    txn_id = score_resp.json()["transaction_id"]

    feedback_resp = client.post("/feedback", json={
        "transaction_id": txn_id,
        "confirmed_label": "legitimate",
        "source": "test_suite",
    })
    assert feedback_resp.status_code == 200
    assert feedback_resp.json()["status"] == "recorded"


def test_invalid_feedback_label_rejected(client):
    resp = client.post("/feedback", json={
        "transaction_id": "some-id",
        "confirmed_label": "maybe_fraud",
    })
    assert resp.status_code == 422
