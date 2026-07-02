"""
Pydantic schemas for the /score endpoint.

WHY PYDANTIC SCHEMAS ARE THE FIRST THING BUILT IN PHASE 4:
Security.md Section 4 and Rules.md Rule 17 require input validation on
every endpoint in the same commit that creates it, never as a follow-up.
The schema IS the validation - FastAPI runs pydantic validation
automatically before any route handler code even executes, so a
malformed request gets a clean 422 before it can reach the model or
the feature pipeline.

Every field below has both a type constraint AND a range/sanity
constraint where applicable (Security.md Section 4: "range/sanity
validation beyond type-checking" - a transaction amount of -50000 or
999999999999 is technically a valid float but nonsensical).
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class DecisionEnum(str, Enum):
    allow = "allow"
    challenge = "challenge"
    block = "block"


class TransactionRequest(BaseModel):
    """
    Everything the caller must supply to score a transaction.
    Mirrors schema.md's transactions table columns closely, but is NOT
    identical - the API contract is what callers need to provide, not
    what the database stores (those differ: e.g. transaction_id is
    generated server-side, not provided by the caller).
    """
    account_id: str = Field(..., min_length=1, max_length=128)
    amount: float = Field(..., gt=0, lt=1_000_000,
        description="Transaction amount in USD. Must be positive and below $1M.")
    merchant_category: str = Field(..., min_length=1, max_length=64)
    location_lat: float = Field(..., ge=-90.0, le=90.0)
    location_lng: float = Field(..., ge=-180.0, le=180.0)
    device_id: str = Field(..., min_length=1, max_length=128)
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Transaction timestamp. Defaults to server time if not provided. "
                    "Callers should provide this for accurate sliding-window feature computation."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "account_id": "acct-abc123",
                "amount": 149.99,
                "merchant_category": "electronics",
                "location_lat": 40.7128,
                "location_lng": -74.0060,
                "device_id": "device-xyz789",
                "timestamp": "2026-06-30T10:00:00Z"
            }
        }
    }


class SHAPFeatureContribution(BaseModel):
    feature: str
    shap_value: float


class ScoreResponse(BaseModel):
    """
    What /score returns - per AppFlow.md Section 3 and
    Security.md Section 5 (explainability is not optional).
    """
    transaction_id: str
    risk_score: float = Field(..., ge=0.0, le=100.0,
        description="Risk score from 0 (definitely legitimate) to 100 (definitely fraud).")
    decision: DecisionEnum
    threshold_used: float
    top_shap_features: list[SHAPFeatureContribution]
    model_version: str
    latency_ms: float

    model_config = {"protected_namespaces": ()}


class FeedbackRequest(BaseModel):
    """
    For POST /feedback - logging a confirmed outcome for a past
    transaction, feeding the Phase 6 retraining loop.
    """
    transaction_id: str
    confirmed_label: str = Field(..., pattern="^(fraud|legitimate)$")
    source: str = Field(default="manual_review", max_length=64)


class MetricsResponse(BaseModel):
    total_scored: int
    fraud_flagged: int
    fraud_rate_pct: float
    model_version: str
    avg_latency_ms: Optional[float]

    model_config = {"protected_namespaces": ()}
