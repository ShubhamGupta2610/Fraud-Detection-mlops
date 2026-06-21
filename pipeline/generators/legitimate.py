"""
Generates LEGITIMATE transactions for a given account, consistent with
its AccountProfile.

This file deliberately knows nothing about fraud. Fraud injection lives
in fraud_patterns.py and gets layered on afterward by the orchestrator
(transaction_stream.py). Keeping them separate means:
  1) the "normal" distribution is honest and not secretly shaped by
     fraud-injection logic, which would make fraud trivially easy to
     find (a giveaway pattern, the failure mode described at the top
     of this build).
  2) we can change/add fraud patterns later without touching this file.
"""

import math
import random
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional

from pipeline.generators.accounts import AccountProfile


@dataclass
class RawTransaction:
    """
    Mirrors the columns in schema.md's transactions table (Section 1) -
    intentionally the same shape, so writing these to the database later
    is a direct field-for-field mapping, not a translation step.
    """
    account_id: str
    timestamp: datetime
    amount: float
    merchant_category: str
    location_lat: float
    location_lng: float
    device_id: str
    is_fraud: bool                  # ground truth label - lives in our generator only;
                                      # NEVER becomes a feature (see docs/data_leakage.md Section 1)
    fraud_type: Optional[str] = None  # None for legitimate; else "card_testing"/"account_takeover"/"impossible_travel"


def _pick_hour_near_active_hours(rng: random.Random, account: AccountProfile) -> int:
    """
    Most transactions happen in the account's normal active hours; a
    small fraction happen outside them, because real people occasionally
    do shop at odd hours - if EVERY transaction respected active_hours
    perfectly, "hour_of_day_deviation" would be a perfect, unrealistically
    easy signal in Phase 3 modeling.
    """
    if rng.random() < 0.92:
        return rng.choice(account.active_hours)
    return rng.randint(0, 23)


def generate_legitimate_transaction(
    account: AccountProfile,
    timestamp: datetime,
    rng: random.Random,
) -> RawTransaction:
    """
    One normal transaction for this account, at the given timestamp.
    Amount and merchant are drawn from the account's own personality
    (typical_amount_mean/std, usual_merchant_categories) so that an
    individual account's behavior is internally consistent - which is
    exactly what makes "deviation from this account's own baseline"
    (feature_dictionary.md) a meaningful signal rather than noise.
    """
    amount = max(1.0, rng.gauss(account.typical_amount_mean, account.typical_amount_std))

    # 85% of the time, a merchant category this account normally uses;
    # 15% something new - legitimate accounts DO try new merchants
    # sometimes, so "new merchant category" alone can't be a perfect
    # fraud tell, same reasoning as the hour-of-day jitter above.
    if rng.random() < 0.85:
        merchant_category = rng.choice(account.usual_merchant_categories)
    else:
        from pipeline.generators.accounts import MERCHANT_CATEGORIES
        merchant_category = rng.choice(MERCHANT_CATEGORIES)

    # Small jitter around home location - legitimate transactions
    # mostly happen near home, with occasional local travel.
    lat = account.home_lat + rng.uniform(-0.3, 0.3)
    lng = account.home_lng + rng.uniform(-0.3, 0.3)

    device_id = f"device-{account.account_id[:8]}"  # most transactions: same device

    return RawTransaction(
        account_id=account.account_id,
        timestamp=timestamp,
        amount=round(amount, 2),
        merchant_category=merchant_category,
        location_lat=round(lat, 6),
        location_lng=round(lng, 6),
        device_id=device_id,
        is_fraud=False,
        fraud_type=None,
    )


def generate_legitimate_history(
    account: AccountProfile,
    end_time: datetime,
    rng: random.Random,
) -> list[RawTransaction]:
    """
    Generates an account's transaction history leading up to end_time,
    with a frequency and span driven by account.history_length -
    this is the concrete implementation of the cold-start design
    decided in accounts.py: "new" accounts get very few transactions,
    "established" accounts get a realistic, longer history.
    """
    if account.history_length == "new":
        n_transactions = rng.randint(0, 3)
        span_days = min(account.account_age_days, 3)
    elif account.history_length == "short":
        n_transactions = rng.randint(3, 15)
        span_days = account.account_age_days
    else:
        # Established accounts: roughly 1 transaction every 1-3 days on average
        span_days = min(account.account_age_days, 180)  # cap history window for generation cost
        n_transactions = max(5, int(span_days / rng.uniform(1, 3)))

    transactions = []
    for _ in range(n_transactions):
        days_ago = rng.uniform(0, span_days)
        hour = _pick_hour_near_active_hours(rng, account)
        minute = rng.randint(0, 59)
        txn_time = end_time - timedelta(days=days_ago)
        txn_time = txn_time.replace(hour=hour, minute=minute, second=rng.randint(0, 59))

        transactions.append(generate_legitimate_transaction(account, txn_time, rng))

    transactions.sort(key=lambda t: t.timestamp)
    return transactions
