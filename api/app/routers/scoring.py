"""
The /score endpoint: Phase 4's core deliverable.

Takes a transaction payload, computes real-time features, runs the
calibrated XGBoost model, generates a SHAP explanation, applies the
cost-curve threshold to make a decision, logs everything to the
database, and returns the result - all within the 100ms p99 latency
target (PRD.md Section 6).

ASYNC DESIGN (TechSpec.md Section 6.6):
The handler is async, which lets FastAPI handle many concurrent requests
without blocking on I/O. The model inference step itself (XGBoost
predict_proba) is synchronous/CPU-bound, but it's fast enough (a few
milliseconds for a single row) that it doesn't block the event loop
meaningfully - for this project's scale, we don't need to push it to
a thread pool. At much larger scale (Phase 9's load testing will tell
us if we're there), cpu_bound inference would be pushed to
asyncio.run_in_executor - noting this now so it's a known upgrade path,
not a discovery later.
"""

import sys
from pathlib import Path
# Add the project root to sys.path so the pipeline package is importable
# whether the server is launched from api/ or from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import uuid
import time
import numpy as np
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.scoring import (
    TransactionRequest, ScoreResponse, SHAPFeatureContribution,
    FeedbackRequest, MetricsResponse,
)
from app.core.decision_engine import (
    make_decision, probability_to_risk_score, get_current_threshold,
)
from app.core.feature_cache import feature_cache
from app.models.transaction import Transaction, Score, DecisionEnum as DBDecisionEnum
from app.models.operations import Feedback

from pipeline.features.pipeline import build_feature_vector
from pipeline.features.history_store import AccountHistoryStore
from pipeline.generators.legitimate import RawTransaction
from pipeline.training.dataset import FEATURE_COLUMNS

router = APIRouter()


def _txn_request_to_raw(txn: TransactionRequest) -> RawTransaction:
    """
    Converts a live /score request into a RawTransaction so Phase 2's
    feature engineering functions (which operate on RawTransaction)
    can be reused without modification.

    is_fraud and fraud_type are set to False/None because we obviously
    don't know the answer yet - that's the whole point of scoring.
    This is also why these fields must NEVER be used as model features
    (docs/data_leakage.md Section 1): here they're literally unknown.
    """
    return RawTransaction(
        account_id=txn.account_id,
        timestamp=txn.timestamp or datetime.now(timezone.utc),
        amount=txn.amount,
        merchant_category=txn.merchant_category,
        location_lat=txn.location_lat,
        location_lng=txn.location_lng,
        device_id=txn.device_id,
        is_fraud=False,
        fraud_type=None,
    )


@router.post("/score", response_model=ScoreResponse)
async def score_transaction(
    payload: TransactionRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    POST /score: the main endpoint.

    AppFlow.md Section 3 traces this flow step by step:
    1. Validate input (pydantic does this automatically before this runs)
    2. Compute real-time features from the cache
    3. Run model inference
    4. Compute SHAP explanation
    5. Apply decision threshold
    6. Log to database
    7. Update cache with this transaction
    8. Return response
    """
    start_time = time.perf_counter()
    transaction_id = str(uuid.uuid4())

    # --- Step 2: real-time feature computation ---
    raw_txn = _txn_request_to_raw(payload)
    store = feature_cache.get_store()

    # Features computed BEFORE adding this transaction to the store -
    # the same ordering rule enforced throughout Phase 2.
    features = build_feature_vector(store, raw_txn)
    X = np.array([[features[col] for col in FEATURE_COLUMNS]])

    # --- Step 3: model inference ---
    model = request.app.state.model
    model_version = request.app.state.model_version

    risk_probability = float(model.predict_proba(X)[0, 1])
    risk_score = probability_to_risk_score(risk_probability)

    # --- Step 4: SHAP explanation ---
    explainer = request.app.state.explainer
    shap_values = explainer.shap_values(X)[0]
    shap_pairs = sorted(
        zip(FEATURE_COLUMNS, shap_values),
        key=lambda p: abs(p[1]),
        reverse=True,
    )
    top_shap = [
        SHAPFeatureContribution(feature=name, shap_value=round(float(val), 4))
        for name, val in shap_pairs[:5]
    ]

    # --- Step 5: decision ---
    threshold = get_current_threshold()
    decision = make_decision(risk_probability, threshold)

    # --- Latency so far ---
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # --- Step 6: log to database ---
    db_txn = Transaction(
        transaction_id=transaction_id,
        account_id=payload.account_id,
        timestamp=raw_txn.timestamp,
        amount=payload.amount,
        merchant_category=payload.merchant_category,
        location_lat=payload.location_lat,
        location_lng=payload.location_lng,
        device_id=payload.device_id,
        raw_features_json=features,
    )
    db.add(db_txn)

    db_score = Score(
        transaction_id=transaction_id,
        model_version=model_version,
        risk_score=risk_score,
        decision=DBDecisionEnum(decision.value),
        threshold_used=threshold,
        shap_top_features_json=[
            {"feature": f.feature, "shap_value": f.shap_value}
            for f in top_shap
        ],
        latency_ms=latency_ms,
    )
    db.add(db_score)

    try:
        db.commit()
    except Exception:
        db.rollback()
        # Per AppFlow.md Section 3.6 error state: degrade gracefully -
        # the score is still returned even if DB logging fails.
        # The transaction gets served, but with a warning logged.
        import logging
        logging.warning(f"DB logging failed for transaction {transaction_id}")

    # --- Step 7: update cache ---
    feature_cache.add_transaction(raw_txn)

    # --- Update in-memory metrics for /metrics endpoint ---
    request.app.state.score_count += 1
    if decision.value in ("challenge", "block"):
        request.app.state.fraud_flagged_count += 1
    request.app.state.total_latency_ms += latency_ms

    return ScoreResponse(
        transaction_id=transaction_id,
        risk_score=risk_score,
        decision=decision,
        threshold_used=threshold,
        top_shap_features=top_shap,
        model_version=model_version,
        latency_ms=latency_ms,
    )


@router.post("/feedback")
async def record_feedback(
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
):
    """
    POST /feedback: logs a confirmed fraud/legitimate outcome for a past
    transaction, feeding Phase 6's retraining loop.
    """
    feedback = Feedback(
        transaction_id=payload.transaction_id,
        confirmed_label=payload.confirmed_label,
        source=payload.source,
    )
    db.add(feedback)
    db.commit()
    return {"status": "recorded", "transaction_id": payload.transaction_id}


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(request: Request):
    """
    GET /metrics: current session statistics for the dashboard.
    Per AppFlow.md Section 1 and TechSpec.md Section 5.
    """
    count = request.app.state.score_count
    flagged = request.app.state.fraud_flagged_count
    total_latency = request.app.state.total_latency_ms

    return MetricsResponse(
        total_scored=count,
        fraud_flagged=flagged,
        fraud_rate_pct=round(100 * flagged / count, 4) if count else 0.0,
        model_version=request.app.state.model_version,
        avg_latency_ms=round(total_latency / count, 2) if count else None,
    )


@router.get("/drift-status")
async def drift_status(db: Session = Depends(get_db)):
    """
    GET /drift-status: returns PSI values and alert state per feature.
    Placeholder in Phase 4 - the real implementation is Phase 6.
    Returns a clear "not yet implemented" response rather than a fake
    empty response, per Rules.md Rule 3 (no claim without a number).
    """
    return {
        "status": "drift_monitoring_not_yet_active",
        "message": "Drift detection is implemented in Phase 6. No PSI values available yet.",
    }


@router.post("/retrain")
async def trigger_retrain():
    """
    POST /retrain: manually triggers a retraining run.
    Placeholder in Phase 4 - the real implementation is Phase 6.
    """
    return {
        "status": "retraining_not_yet_implemented",
        "message": "Retraining pipeline is implemented in Phase 6.",
    }
