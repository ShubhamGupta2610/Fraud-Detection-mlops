"""
Velocity features, per docs/feature_dictionary.md.

Each function takes the account's history (already correctly bounded to
"strictly before this transaction" by history_store.py) and computes a
single feature value. Kept as small, independently testable functions
rather than one large "compute everything" function, so each one can be
verified in isolation (research/02_feature_engineering.md's question
about WHY these specific window lengths matters here - each window
length is a parameter, not a magic number buried in logic).
"""

from datetime import datetime, timedelta
from pipeline.features.history_store import AccountHistoryStore


def txn_count_in_window(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
    window: timedelta,
) -> int:
    """feature_dictionary.md: txn_count_1min / txn_count_1h / txn_count_24h"""
    return len(store.transactions_before(account_id, at_time, window=window))


def total_amount_in_window(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
    window: timedelta,
) -> float:
    """feature_dictionary.md: total_amount_1h / total_amount_24h"""
    history = store.transactions_before(account_id, at_time, window=window)
    return round(sum(t.amount for t in history), 2)


def distinct_merchants_in_window(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
    window: timedelta,
) -> int:
    """feature_dictionary.md: distinct_merchants_24h"""
    history = store.transactions_before(account_id, at_time, window=window)
    return len(set(t.merchant_category for t in history))


# Window lengths chosen and named here, once, rather than scattered as
# literals through calling code - matches feature_dictionary.md exactly.
WINDOW_1MIN = timedelta(minutes=1)
WINDOW_1H = timedelta(hours=1)
WINDOW_24H = timedelta(hours=24)


def compute_velocity_features(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
) -> dict:
    """
    Computes the full velocity feature set for one transaction, matching
    feature_dictionary.md's velocity rows exactly by name.
    """
    return {
        "txn_count_1min": txn_count_in_window(store, account_id, at_time, WINDOW_1MIN),
        "txn_count_1h": txn_count_in_window(store, account_id, at_time, WINDOW_1H),
        "txn_count_24h": txn_count_in_window(store, account_id, at_time, WINDOW_24H),
        "total_amount_1h": total_amount_in_window(store, account_id, at_time, WINDOW_1H),
        "total_amount_24h": total_amount_in_window(store, account_id, at_time, WINDOW_24H),
        "distinct_merchants_24h": distinct_merchants_in_window(store, account_id, at_time, WINDOW_24H),
    }
