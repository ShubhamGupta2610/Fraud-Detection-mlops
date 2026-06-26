"""
Main feature engineering pipeline: takes a list of RawTransaction
(chronologically sortable, as produced by Phase 1's generator) and
produces one feature vector per transaction, using ONLY information
that would have been available at the moment that transaction needed
to be scored.

WHY PROCESSING ORDER IS THE SINGLE MOST IMPORTANT THING IN THIS FILE:
history_store.AccountHistoryStore.add() must be called in chronological
order, and a transaction's features must be computed BEFORE it is added
to the store - never after. If we accidentally added a transaction to
history before computing its own features, every feature would see
itself in its own "history," which is both a logical error (a
transaction can't be velocity-counted against itself) and a leakage bug
in spirit (docs/data_leakage.md Section 2) even though it's not
literally future data - it's "present" data leaking into a calculation
that should only reflect the past.

This is exactly the kind of mistake that's easy to make by accident and
hard to notice just by reading the code casually - which is why
tests/test_features.py asserts this ordering explicitly rather than
trusting this docstring's promise.
"""

from typing import List
from pipeline.generators.legitimate import RawTransaction
from pipeline.features.history_store import AccountHistoryStore
from pipeline.features.velocity import compute_velocity_features
from pipeline.features.geo import geo_velocity
from pipeline.features.behavioral import compute_behavioral_features
from pipeline.features.device import is_new_device, is_new_ip_or_location


def build_feature_vector(
    store: AccountHistoryStore,
    transaction: RawTransaction,
) -> dict:
    """
    Computes every feature in feature_dictionary.md for a single
    transaction, using the store's history as it exists at this point
    (i.e. BEFORE this transaction has been added to the store).

    Deliberately does NOT include transaction.is_fraud or
    transaction.fraud_type anywhere in the returned dict -
    docs/data_leakage.md Section 1 names this exact mistake explicitly
    ("does any feature directly or indirectly encode the label").
    """
    features = {}

    features.update(compute_velocity_features(
        store, transaction.account_id, transaction.timestamp,
    ))

    features["geo_velocity"] = geo_velocity(
        store, transaction.account_id, transaction.timestamp,
        transaction.location_lat, transaction.location_lng,
    )

    features.update(compute_behavioral_features(
        store, transaction.account_id, transaction.timestamp,
        transaction.amount, transaction.merchant_category,
    ))

    features["is_new_device"] = is_new_device(
        store, transaction.account_id, transaction.timestamp, transaction.device_id,
    )
    features["is_new_ip_or_location"] = is_new_ip_or_location(
        store, transaction.account_id, transaction.timestamp,
        transaction.location_lat, transaction.location_lng,
    )

    return features


def run_feature_pipeline(transactions: List[RawTransaction]) -> List[dict]:
    """
    Processes an entire dataset in chronological order, returning one
    row per transaction: the original transaction fields, the computed
    features, and the label (is_fraud) kept in a clearly separate
    section of the row rather than mixed in with feature names - so
    Phase 3's training code can trivially split features from label
    without needing to remember an exclusion list.

    REQUIRES transactions to be processable in timestamp order. Phase 1's
    generate_dataset() already returns a list sorted by timestamp - this
    function re-sorts defensively anyway, because trusting an upstream
    caller to maintain an invariant this important, without checking, is
    exactly the kind of silent assumption that causes bugs later when
    someone calls this function with differently-prepared data.
    """
    transactions_sorted = sorted(transactions, key=lambda t: t.timestamp)
    store = AccountHistoryStore()
    rows = []

    for t in transactions_sorted:
        features = build_feature_vector(store, t)

        rows.append({
            "account_id": t.account_id,
            "timestamp": t.timestamp,
            "amount": t.amount,
            "merchant_category": t.merchant_category,
            "features": features,
            "label": {
                "is_fraud": t.is_fraud,
                "fraud_type": t.fraud_type,
            },
        })

        # Added to history AFTER its own features were computed -
        # this ordering is the entire point of this function, see the
        # module docstring above.
        store.add(t)

    return rows
