"""
Tests for Phase 2 feature engineering.

Per Rules.md Rule 3 and the Phase 1 precedent (manual verification
caught two real bugs there), every behavior confirmed by hand above is
turned into a permanent regression test here.
"""

from datetime import datetime, timedelta

from pipeline.generators.legitimate import RawTransaction
from pipeline.features.history_store import AccountHistoryStore
from pipeline.features.velocity import compute_velocity_features
from pipeline.features.geo import geo_velocity, is_impossible_travel
from pipeline.features.behavioral import (
    amount_deviation_from_avg,
    hour_of_day_deviation,
    merchant_category_novelty,
    MIN_HISTORY_FOR_BASELINE,
)
from pipeline.features.device import is_new_device, is_new_ip_or_location
from pipeline.features.pipeline import build_feature_vector, run_feature_pipeline
from pipeline.generators.transaction_stream import generate_dataset


def make_txn(account_id, ts, amount=50.0, merchant="grocery", lat=40.0, lng=-74.0, device="d1"):
    return RawTransaction(
        account_id=account_id, timestamp=ts, amount=amount,
        merchant_category=merchant, location_lat=lat, location_lng=lng,
        device_id=device, is_fraud=False, fraud_type=None,
    )


# --- Core correctness: never see the future ---

def test_history_store_never_returns_future_transactions():
    """
    The single most important property in this entire phase
    (docs/data_leakage.md Section 2). A transaction added AFTER the
    query time must never appear in transactions_before().
    """
    store = AccountHistoryStore()
    base = datetime(2026, 1, 1, 12, 0, 0)

    store.add(make_txn("acct1", base - timedelta(hours=1)))
    store.add(make_txn("acct1", base + timedelta(hours=1)))  # future relative to `base`

    history = store.transactions_before("acct1", base)
    assert len(history) == 1
    assert all(t.timestamp < base for t in history)


def test_history_store_excludes_exact_timestamp_match():
    """
    A transaction must never see ITSELF in its own history - the
    boundary must be strictly < , never <=.
    """
    store = AccountHistoryStore()
    t = datetime(2026, 1, 1, 12, 0, 0)
    store.add(make_txn("acct1", t))

    history = store.transactions_before("acct1", t)
    assert len(history) == 0


def test_pipeline_computes_features_before_adding_to_history():
    """
    Regression test for the exact ordering bug described in
    pipeline.py's module docstring: a transaction's own feature
    computation must never include itself.
    """
    base = datetime(2026, 1, 1, 0, 0, 0)
    txns = [make_txn("acct1", base, amount=100.0)]
    rows = run_feature_pipeline(txns)

    assert rows[0]["features"]["txn_count_1h"] == 0, \
        "a transaction must not count itself in its own velocity window"


# --- Velocity ---

def test_velocity_counts_climb_correctly_across_a_burst():
    """
    Regression test for the manually-verified card-testing burst:
    txn_count_1h should climb by exactly 1 for each subsequent
    transaction within the window.
    """
    store = AccountHistoryStore()
    base = datetime(2026, 1, 1, 0, 0, 0)
    counts = []

    for i in range(4):
        t = base + timedelta(seconds=i * 30)
        features = compute_velocity_features(store, "acct1", t)
        counts.append(features["txn_count_1h"])
        store.add(make_txn("acct1", t))

    assert counts == [0, 1, 2, 3]


def test_velocity_window_excludes_old_transactions():
    """A transaction more than the window length ago should not count."""
    store = AccountHistoryStore()
    base = datetime(2026, 1, 1, 12, 0, 0)
    store.add(make_txn("acct1", base - timedelta(hours=2)))  # outside the 1h window

    features = compute_velocity_features(store, "acct1", base)
    assert features["txn_count_1h"] == 0
    assert features["txn_count_24h"] == 1  # but inside the 24h window


# --- Geo-velocity ---

def test_geo_velocity_cold_start_returns_zero():
    """First-ever transaction has no previous location to compare against."""
    store = AccountHistoryStore()
    speed = geo_velocity(store, "acct1", datetime(2026, 1, 1), 40.0, -74.0)
    assert speed == 0.0


def test_geo_velocity_matches_fraud_pattern_generator_definition():
    """
    Confirms Phase 1's impossible_travel injector and Phase 2's
    geo_velocity feature agree on what 'impossible' means - the whole
    point of promoting haversine_km to a shared module (geo_utils.py).
    """
    from pipeline.generators.accounts import generate_account_population
    from pipeline.generators.fraud_patterns import inject_impossible_travel
    import random

    accounts = generate_account_population(5, seed=1)
    rng = random.Random(42)
    first, second = inject_impossible_travel(accounts[0], datetime(2026, 6, 1), rng)

    store = AccountHistoryStore()
    store.add(first)

    speed = geo_velocity(store, first.account_id, second.timestamp, second.location_lat, second.location_lng)
    assert is_impossible_travel(speed), \
        "geo_velocity feature should flag the same pair the generator created as impossible travel"


# --- Behavioral ---

def test_amount_deviation_cold_start_returns_zero():
    """Fewer than MIN_HISTORY_FOR_BASELINE transactions -> not enough data to trust a z-score."""
    store = AccountHistoryStore()
    base = datetime(2026, 1, 1)
    for i in range(MIN_HISTORY_FOR_BASELINE - 1):
        store.add(make_txn("acct1", base - timedelta(days=i + 1), amount=50.0))

    deviation = amount_deviation_from_avg(store, "acct1", base, current_amount=10000.0)
    assert deviation == 0.0


def test_amount_deviation_detects_large_purchase_after_established_baseline():
    """Once a real baseline exists, a much larger purchase should show a large positive z-score."""
    store = AccountHistoryStore()
    base = datetime(2026, 1, 1)
    for i in range(10):
        store.add(make_txn("acct1", base - timedelta(days=i + 1), amount=50.0 + (i % 3)))  # tight, consistent baseline

    deviation = amount_deviation_from_avg(store, "acct1", base, current_amount=500.0)
    assert deviation > 3.0, "a purchase 10x the baseline should register as a strong positive deviation"


def test_merchant_novelty_is_one_for_first_ever_transaction():
    """
    Deliberate asymmetry documented in behavioral.py: unlike the
    statistical deviation features, novelty is honestly 1 on a first
    transaction, not suppressed to 0.
    """
    store = AccountHistoryStore()
    novelty = merchant_category_novelty(store, "acct1", datetime(2026, 1, 1), "electronics")
    assert novelty == 1


def test_merchant_novelty_is_zero_for_previously_seen_category():
    store = AccountHistoryStore()
    base = datetime(2026, 1, 1)
    store.add(make_txn("acct1", base - timedelta(days=1), merchant="electronics"))

    novelty = merchant_category_novelty(store, "acct1", base, "electronics")
    assert novelty == 0


# --- Device ---

def test_new_device_flag_for_first_transaction():
    store = AccountHistoryStore()
    flag = is_new_device(store, "acct1", datetime(2026, 1, 1), "device-A")
    assert flag == 1


def test_new_device_flag_false_for_known_device():
    store = AccountHistoryStore()
    base = datetime(2026, 1, 1)
    store.add(make_txn("acct1", base - timedelta(days=1), device="device-A"))

    flag = is_new_device(store, "acct1", base, "device-A")
    assert flag == 0


def test_new_location_flag_respects_distance_threshold():
    store = AccountHistoryStore()
    base = datetime(2026, 1, 1)
    store.add(make_txn("acct1", base - timedelta(days=1), lat=40.0, lng=-74.0))

    # Nearby (same city, ~5km away) - should NOT count as new
    nearby_flag = is_new_ip_or_location(store, "acct1", base, 40.04, -74.0)
    assert nearby_flag == 0

    # Far away (different continent) - SHOULD count as new
    far_flag = is_new_ip_or_location(store, "acct1", base, -33.87, 151.21)  # Sydney
    assert far_flag == 1


# --- No label leakage into features ---

def test_feature_vector_never_contains_label_fields():
    """
    Direct check against docs/data_leakage.md Section 1: the returned
    feature dict must never contain is_fraud or fraud_type, under any
    key name.
    """
    txns = generate_dataset(n_accounts=50, fraud_rate=0.05, end_time=datetime(2026, 6, 1), seed=3)
    rows = run_feature_pipeline(txns)

    for row in rows:
        feature_keys_lower = {k.lower() for k in row["features"].keys()}
        assert "is_fraud" not in feature_keys_lower
        assert "fraud_type" not in feature_keys_lower
        assert "fraud" not in " ".join(feature_keys_lower), \
            "no feature key should even contain the word 'fraud' - that would itself be a smell worth investigating"


def test_full_pipeline_runs_without_error_on_real_generated_dataset():
    """
    End-to-end smoke test: the whole Phase 1 -> Phase 2 chain should run
    cleanly on a realistically sized dataset, with every row containing
    all expected feature keys.
    """
    txns = generate_dataset(n_accounts=300, fraud_rate=0.01, end_time=datetime(2026, 6, 1), seed=10)
    rows = run_feature_pipeline(txns)

    expected_keys = {
        "txn_count_1min", "txn_count_1h", "txn_count_24h",
        "total_amount_1h", "total_amount_24h", "distinct_merchants_24h",
        "geo_velocity", "amount_deviation_from_avg", "hour_of_day_deviation",
        "merchant_category_novelty", "is_new_device", "is_new_ip_or_location",
    }
    assert len(rows) == len(txns)
    for row in rows:
        assert set(row["features"].keys()) == expected_keys
