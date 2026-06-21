"""
Generates the population of synthetic accounts that all transactions
belong to.

WHY THIS FILE EXISTS SEPARATELY FROM THE TRANSACTION GENERATOR:
research/02_feature_engineering.md asks: what happens to a behavioral
baseline feature for an account with very little history? That question
can't even be answered sensibly unless accounts genuinely HAVE a
baseline behavior pattern that's consistent across many transactions -
not just random noise per transaction. So we generate the account
population first, give each one a stable "personality" (typical spend
amount, typical hours active, home location), and the transaction
generator (02_transaction_generator.py) draws from that personality
when generating that account's normal transactions.

This is also where the cold-start decision gets made concrete: some
accounts are deliberately given a short history (few transactions) so
Phase 2's feature engineering has real cold-start cases to handle, not
just a hypothetical.
"""

import random
import uuid
from dataclasses import dataclass, field
from typing import List


@dataclass
class AccountProfile:
    """
    One synthetic account's stable behavioral 'personality.' The
    transaction generator uses this to produce transactions that look
    like the SAME person each time, which is what makes 'deviation from
    baseline' a meaningful feature later (research/02_feature_engineering.md).
    """
    account_id: str
    typical_amount_mean: float       # this account's normal spend size
    typical_amount_std: float        # how much it normally varies
    active_hours: List[int]          # hours of day (0-23) this account is usually active in
    home_lat: float
    home_lng: float
    usual_merchant_categories: List[str]
    history_length: str              # "new" | "short" | "established" - drives cold-start cases
    account_age_days: int


MERCHANT_CATEGORIES = [
    "grocery", "electronics", "restaurant", "travel", "fuel",
    "online_retail", "subscription", "pharmacy", "entertainment", "utilities",
]

# A handful of real-ish city coordinates, used as account "home" locations.
# Plain (lat, lng) pairs - no need for a geocoding service for synthetic data.
CITY_COORDINATES = [
    (40.7128, -74.0060),   # New York
    (34.0522, -118.2437),  # Los Angeles
    (41.8781, -87.6298),   # Chicago
    (29.7604, -95.3698),   # Houston
    (51.5074, -0.1278),    # London
    (28.6139, 77.2090),    # Delhi
    (19.0760, 72.8777),    # Mumbai
    (-33.8688, 151.2093),  # Sydney
    (35.6762, 139.6503),   # Tokyo
    (52.5200, 13.4050),    # Berlin
]


def generate_account_population(n_accounts: int, seed: int = 42) -> List[AccountProfile]:
    """
    Creates n_accounts distinct AccountProfiles.

    The history_length distribution is deliberate, not arbitrary:
    - 10% "new" (0-3 days old)       -> forces cold-start handling
    - 20% "short" (4-30 days old)    -> partial history, still a real case
    - 70% "established" (30+ days)  -> the common case, full rolling-window history available

    This ratio means Phase 2's feature code WILL hit cold-start accounts
    regularly during testing, rather than that being a rare edge case
    that only gets noticed in production.
    """
    rng = random.Random(seed)
    accounts = []

    for _ in range(n_accounts):
        account_id = str(uuid.uuid4())

        roll = rng.random()
        if roll < 0.10:
            history_length = "new"
            account_age_days = rng.randint(0, 3)
        elif roll < 0.30:
            history_length = "short"
            account_age_days = rng.randint(4, 30)
        else:
            history_length = "established"
            account_age_days = rng.randint(31, 1500)

        home_lat, home_lng = rng.choice(CITY_COORDINATES)
        # Small jitter so accounts in the "same city" aren't at the exact same point
        home_lat += rng.uniform(-0.05, 0.05)
        home_lng += rng.uniform(-0.05, 0.05)

        # Most people are active in a contiguous block of hours (e.g. 8am-11pm),
        # not literally random hours - this matters for the hour_of_day_deviation
        # feature in feature_dictionary.md to mean anything.
        wake_hour = rng.randint(5, 10)
        sleep_hour = rng.randint(20, 23)
        active_hours = list(range(wake_hour, sleep_hour + 1))

        accounts.append(AccountProfile(
            account_id=account_id,
            typical_amount_mean=round(rng.uniform(15, 250), 2),
            typical_amount_std=round(rng.uniform(5, 60), 2),
            active_hours=active_hours,
            home_lat=home_lat,
            home_lng=home_lng,
            usual_merchant_categories=rng.sample(MERCHANT_CATEGORIES, k=rng.randint(2, 5)),
            history_length=history_length,
            account_age_days=account_age_days,
        ))

    return accounts
