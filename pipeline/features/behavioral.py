"""
Behavioral deviation features, per docs/feature_dictionary.md.

All three features measure deviation from THIS account's own history -
not a global population baseline. This is deliberate: a $2,000
transaction is normal for one account and wildly anomalous for another,
per the project's whole premise (PRD.md's Developer A / Developer B
style contrast, applied here to spending behavior instead of commits).
"""

import statistics
from datetime import datetime, timedelta
from pipeline.features.history_store import AccountHistoryStore

# Lookback window for computing "this account's typical behavior."
# 90 days chosen as a reasonable amount of history without going so far
# back that very old, possibly stale behavior dominates the baseline -
# documented here as a parameter, not a hidden literal, exactly per
# research/02_feature_engineering.md's instruction to be deliberate
# about window lengths.
BASELINE_WINDOW = timedelta(days=90)

# Minimum number of prior transactions needed before we trust a
# statistical baseline (mean/stdev) for this account. Below this, we
# are in cold-start territory - see the per-function docstrings below
# for how each feature handles that case differently, because "not
# enough history" doesn't mean the same default is right for every
# feature.
MIN_HISTORY_FOR_BASELINE = 5


def amount_deviation_from_avg(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
    current_amount: float,
) -> float:
    """
    feature_dictionary.md: (current amount - account's rolling average)
    / account's rolling standard deviation. This is a z-score.

    COLD-START DECISION: with fewer than MIN_HISTORY_FOR_BASELINE prior
    transactions, there isn't enough data for a meaningful mean/stdev -
    a stdev computed from 1-2 points is not a real estimate of spread,
    it's noise. We return 0.0 (no deviation detected) rather than a
    z-score computed on a near-meaningless sample, for the same reason
    given in geo.py: treating cold-start as automatically suspicious
    would systematically hurt new accounts' precision without real
    justification. This decision is recorded in
    research/02_feature_engineering.md - re-derive it there in your own
    words rather than just copying this comment.
    """
    history = store.transactions_before(account_id, at_time, window=BASELINE_WINDOW)
    if len(history) < MIN_HISTORY_FOR_BASELINE:
        return 0.0

    amounts = [t.amount for t in history]
    mean = statistics.mean(amounts)
    stdev = statistics.stdev(amounts) if len(amounts) > 1 else 0.0

    if stdev == 0:
        # Every prior transaction was the exact same amount (rare, but
        # possible for e.g. a subscription-only account). Avoid
        # division by zero; treat any different amount as a full
        # deviation rather than infinite.
        return 0.0 if current_amount == mean else 5.0

    return round((current_amount - mean) / stdev, 4)


def hour_of_day_deviation(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
) -> float:
    """
    feature_dictionary.md: how unusual the current transaction's
    hour-of-day is relative to the account's typical active hours.

    Implementation: fraction of this account's prior transactions that
    did NOT occur within +/-2 hours of the current transaction's hour.
    Returns a value in [0.0, 1.0] - higher means this hour is more
    unusual for this account. Circular hour-of-day wraparound (e.g. 23
    and 1 are only 2 hours apart, not 22) is handled explicitly, since
    naive subtraction would treat midnight-adjacent hours as maximally
    different when they're actually close.

    COLD-START DECISION: with no prior history at all, there's no
    "typical hour" to compare against - returns 0.0 (not unusual),
    consistent with the same cold-start philosophy as the other
    features in this file.
    """
    history = store.transactions_before(account_id, at_time, window=BASELINE_WINDOW)
    if len(history) < MIN_HISTORY_FOR_BASELINE:
        return 0.0

    current_hour = at_time.hour
    unusual_count = 0
    for t in history:
        hour_diff = abs(t.timestamp.hour - current_hour)
        circular_diff = min(hour_diff, 24 - hour_diff)  # handles the midnight wraparound
        if circular_diff > 2:
            unusual_count += 1

    return round(unusual_count / len(history), 4)


def merchant_category_novelty(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
    current_merchant_category: str,
) -> int:
    """
    feature_dictionary.md: 1 if this merchant category is new for this
    account, else 0.

    COLD-START DECISION: a brand-new account's very first transaction
    is, by definition, in a "new" merchant category, since it has no
    history at all. Unlike the other two features above, here we
    deliberately do NOT special-case this to 0 - novelty is genuinely
    and correctly 1 for a first transaction, and that's a fine, honest
    signal rather than something to suppress. This asymmetry (some
    cold-start cases default to "not suspicious," this one legitimately
    can be 1) is exactly the kind of nuance that should be written out
    in research/02_feature_engineering.md, not glossed over.
    """
    history = store.transactions_before(account_id, at_time, window=BASELINE_WINDOW)
    seen_categories = {t.merchant_category for t in history}
    return 0 if current_merchant_category in seen_categories else 1


def compute_behavioral_features(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
    current_amount: float,
    current_merchant_category: str,
) -> dict:
    """Computes the full behavioral feature set, matching feature_dictionary.md by name."""
    return {
        "amount_deviation_from_avg": amount_deviation_from_avg(store, account_id, at_time, current_amount),
        "hour_of_day_deviation": hour_of_day_deviation(store, account_id, at_time),
        "merchant_category_novelty": merchant_category_novelty(store, account_id, at_time, current_merchant_category),
    }
