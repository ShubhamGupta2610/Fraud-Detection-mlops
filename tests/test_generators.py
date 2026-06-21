"""
Tests for the Phase 1 synthetic transaction generator.

These exist specifically BECAUSE manual verification during development
caught two real bugs (a fraud-rate miscalibration and a label-correctness
bug in impossible_travel). Per ImplementationPlan.md Phase 7 and Rules.md
Rule 3 ("no claim without a number"), those checks belong in an automated
test, not just a one-time terminal command - otherwise a future change to
this generator could silently reintroduce either bug.
"""

import random
from datetime import datetime

from pipeline.generators.accounts import generate_account_population
from pipeline.generators.fraud_patterns import (
    inject_impossible_travel,
    inject_card_testing,
    inject_account_takeover,
    verify_impossible_travel_speed,
    MAX_PLAUSIBLE_TRAVEL_SPEED_KMH,
)
from pipeline.generators.transaction_stream import generate_dataset, dataset_summary


def test_impossible_travel_always_exceeds_speed_threshold():
    """
    Regression test for the latitude/longitude conversion bug found
    during Phase 1 verification: every injected impossible_travel pair
    must genuinely imply a speed above the plausibility threshold. If
    this regresses, training labels would be silently wrong.
    """
    accounts = generate_account_population(50, seed=1)
    rng = random.Random(123)

    failures = 0
    n_test = 200
    for i in range(n_test):
        acct = accounts[i % len(accounts)]
        first, second = inject_impossible_travel(acct, datetime(2026, 6, 1), rng)
        speed = verify_impossible_travel_speed(first, second)
        if speed <= MAX_PLAUSIBLE_TRAVEL_SPEED_KMH:
            failures += 1

    assert failures == 0, f"{failures}/{n_test} impossible_travel pairs did NOT exceed the speed threshold"


def test_impossible_travel_first_transaction_is_legitimate():
    """
    research/01_fraud_domain.md's account-takeover question applies
    here too: only the SECOND transaction in an impossible-travel pair
    is the fraud attempt. The first is the genuine transaction the
    fraud is being compared against - mislabeling it would teach the
    model a false signal.
    """
    accounts = generate_account_population(10, seed=2)
    rng = random.Random(5)
    first, second = inject_impossible_travel(accounts[0], datetime(2026, 6, 1), rng)

    assert first.is_fraud is False
    assert second.is_fraud is True
    assert second.fraud_type == "impossible_travel"


def test_card_testing_produces_multiple_rapid_small_transactions():
    """
    Card testing's defining structural feature is velocity + small
    amounts, per research/01_fraud_domain.md - verify the generator
    actually produces that shape, not just a label.
    """
    accounts = generate_account_population(10, seed=3)
    rng = random.Random(7)
    transactions = inject_card_testing(accounts[0], datetime(2026, 6, 1), rng)

    assert len(transactions) >= 4, "card testing should produce multiple attempts"
    assert all(t.is_fraud for t in transactions)
    assert all(t.amount < 10 for t in transactions), "card testing amounts should be small"

    # Verify rapid succession: gaps between consecutive transactions are short
    sorted_txns = sorted(transactions, key=lambda t: t.timestamp)
    for a, b in zip(sorted_txns, sorted_txns[1:]):
        gap_seconds = (b.timestamp - a.timestamp).total_seconds()
        assert gap_seconds < 120, "card testing transactions should be close together in time"


def test_account_takeover_uses_new_device_and_unusual_amount():
    """
    Verifies the behavioral-shift mechanism described in
    research/01_fraud_domain.md: device changes, and at least one
    transaction deviates well above the account's typical amount.
    """
    accounts = generate_account_population(10, seed=4)
    account = accounts[0]
    rng = random.Random(11)
    transactions = inject_account_takeover(account, datetime(2026, 6, 1), rng)

    assert all(t.is_fraud for t in transactions)
    assert all(t.device_id != f"device-{account.account_id[:8]}" for t in transactions), \
        "account takeover should use a device different from the account's normal device"

    max_amount = max(t.amount for t in transactions)
    assert max_amount > account.typical_amount_mean + account.typical_amount_std * 2, \
        "at least one account-takeover transaction should clearly deviate from this account's baseline"


def test_dataset_fraud_rate_is_low_and_stable_across_seeds():
    """
    Regression test for the fraud-rate miscalibration bug found during
    Phase 1 verification. PRD.md and research/03_imbalance_learning.md
    require fraud to be rare (<1%) - this test fails loudly if a future
    change pushes the rate far outside a realistic band, in either
    direction, instead of that drift being discovered later by accident
    during Phase 3 modeling.
    """
    for seed in [42, 99, 7]:
        txns = generate_dataset(n_accounts=1500, fraud_rate=0.005, end_time=datetime(2026, 6, 1), seed=seed)
        summary = dataset_summary(txns)

        assert summary["fraud_rate_pct"] > 0.05, \
            f"seed={seed}: fraud rate too low ({summary['fraud_rate_pct']}%) - generator may be miscalibrated"
        assert summary["fraud_rate_pct"] < 2.0, \
            f"seed={seed}: fraud rate too high ({summary['fraud_rate_pct']}%) - no longer a realistic imbalanced problem"


def test_dataset_contains_all_three_fraud_patterns():
    """
    Regression test for the pattern-coverage issue found during Phase 1
    verification (impossible_travel was absent by chance at low sample
    sizes). With the round-robin guarantee in transaction_stream.py,
    all three patterns should reliably appear at a reasonable scale.
    """
    txns = generate_dataset(n_accounts=2000, fraud_rate=0.005, end_time=datetime(2026, 6, 1), seed=42)
    summary = dataset_summary(txns)

    assert "card_testing" in summary["fraud_by_pattern"]
    assert "account_takeover" in summary["fraud_by_pattern"]
    assert "impossible_travel" in summary["fraud_by_pattern"]


def test_no_fraud_label_leaks_into_required_fields():
    """
    Lightweight check related to docs/data_leakage.md Section 1: the
    is_fraud / fraud_type fields exist on RawTransaction for generator
    bookkeeping and training-label purposes only. This test documents
    that expectation so Phase 2's feature engineering code is written
    knowing these two fields must NEVER be copied into the feature
    vector - they ARE the answer, not an input.
    """
    txns = generate_dataset(n_accounts=200, fraud_rate=0.01, end_time=datetime(2026, 6, 1), seed=1)
    txn = txns[0]
    # This isn't a behavioral assertion (Python can't enforce "don't use
    # this field" by itself) - it's a documentation-as-test marker.
    assert hasattr(txn, "is_fraud")
    assert hasattr(txn, "fraud_type")
