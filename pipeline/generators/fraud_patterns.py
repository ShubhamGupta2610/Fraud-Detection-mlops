"""
Implements the three fraud patterns named throughout PRD.md, AppFlow.md,
and research/01_fraud_domain.md: card testing, account takeover, and
impossible travel.

DESIGN PRINCIPLE FOR THIS WHOLE FILE:
Each function below implements the actual MECHANISM of the fraud
pattern (what a real fraudster's transactions would structurally look
like), not just "flip is_fraud=True and randomize a few fields." If we
cheated here, Phase 3's model would learn a fake, oversimplified signal
that wouldn't transfer to anything resembling reality - the model would
"work" on this dataset and teach us nothing.

Each pattern is deliberately injected with some noise/imperfection
(see comments in each function) so detecting it isn't trivial -
research/01_fraud_domain.md's domain notes should be filled in by
actually studying why each of these mechanisms looks the way it does.
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import List

from pipeline.generators.accounts import AccountProfile, MERCHANT_CATEGORIES
from pipeline.generators.legitimate import RawTransaction
from pipeline.geo_utils import haversine_km


# Roughly the speed of a commercial flight, in km/h. Used by
# impossible_travel below AND reused in Phase 2 as the actual
# geo_velocity feature threshold (feature_dictionary.md) - defining it
# once, here, means the generator and the eventual detector agree on
# what "impossible" means, which matters when we get to error analysis
# in Phase 3 (docs/error_analysis.md).
MAX_PLAUSIBLE_TRAVEL_SPEED_KMH = 900.0


def inject_card_testing(
    account: AccountProfile,
    around_time: datetime,
    rng: random.Random,
) -> List[RawTransaction]:
    """
    CARD TESTING: a fraudster who has stolen card details runs many
    small transactions in rapid succession to verify the card still
    works before attempting a larger purchase. The defining structural
    feature is VELOCITY (many transactions, very short time apart) and
    SMALL, similar amounts - not one big anomalous purchase.

    Imperfection injected on purpose: amounts vary a bit (not identical)
    and merchant categories vary, because real card-testing scripts hit
    different small merchants, not the exact same one repeatedly -
    making "amount is suspiciously round" alone an unreliable tell.
    """
    n_attempts = rng.randint(4, 12)
    small_amount_base = rng.uniform(1.0, 5.0)  # card testing uses tiny amounts to avoid limits/detection

    transactions = []
    current_time = around_time
    device_id = f"fraud-device-{uuid.uuid4().hex[:8]}"  # new/unrecognized device - real signal, not the only one

    for _ in range(n_attempts):
        current_time += timedelta(seconds=rng.uniform(5, 90))  # rapid succession
        amount = round(max(0.5, small_amount_base + rng.uniform(-1.5, 1.5)), 2)
        merchant_category = rng.choice(MERCHANT_CATEGORIES)

        # Card testing often hits a DIFFERENT location than the account's
        # home, but not always wildly far - sometimes the attacker is
        # geographically nearby (e.g. same city, different device).
        lat = account.home_lat + rng.uniform(-2.0, 2.0)
        lng = account.home_lng + rng.uniform(-2.0, 2.0)

        transactions.append(RawTransaction(
            account_id=account.account_id,
            timestamp=current_time,
            amount=amount,
            merchant_category=merchant_category,
            location_lat=round(lat, 6),
            location_lng=round(lng, 6),
            device_id=device_id,
            is_fraud=True,
            fraud_type="card_testing",
        ))

    return transactions


def inject_account_takeover(
    account: AccountProfile,
    around_time: datetime,
    rng: random.Random,
) -> List[RawTransaction]:
    """
    ACCOUNT TAKEOVER: an attacker has gained control of a legitimate
    account and starts transacting AS that account. The defining
    structural feature is a BEHAVIORAL SHIFT relative to THIS account's
    own baseline - new device, often a new/distant location, and
    transaction amounts and merchant categories that deviate from this
    specific account's normal pattern (research/01_fraud_domain.md asks
    exactly this: "what changes when an account is taken over?").

    Imperfection injected on purpose: the attacker sometimes makes a
    small "test" purchase first (similar in spirit to card testing, but
    on an already-compromised account) before a larger one - real ATO
    behavior is rarely just one clean anomalous transaction.
    """
    transactions = []
    new_device_id = f"fraud-device-{uuid.uuid4().hex[:8]}"

    # Attacker is often geographically distant from the account's home -
    # but with real variance, not a fixed huge distance every time.
    distance_deg = rng.uniform(5, 60)  # roughly hundreds to thousands of km depending on latitude
    angle = rng.uniform(0, 360)
    import math
    lat = account.home_lat + distance_deg * math.cos(math.radians(angle))
    lng = account.home_lng + distance_deg * math.sin(math.radians(angle))

    n_transactions = rng.randint(1, 4)
    current_time = around_time

    for i in range(n_transactions):
        current_time += timedelta(minutes=rng.uniform(2, 45))

        if i == 0 and rng.random() < 0.4:
            # small test purchase first
            amount = round(rng.uniform(1, 20), 2)
        else:
            # then a purchase well above this account's typical amount
            amount = round(account.typical_amount_mean + account.typical_amount_std * rng.uniform(3, 8), 2)

        # merchant category often NOT in this account's usual list
        merchant_category = rng.choice(MERCHANT_CATEGORIES)

        transactions.append(RawTransaction(
            account_id=account.account_id,
            timestamp=current_time,
            amount=amount,
            merchant_category=merchant_category,
            location_lat=round(lat, 6),
            location_lng=round(lng, 6),
            device_id=new_device_id,
            is_fraud=True,
            fraud_type="account_takeover",
        ))

    return transactions


def inject_impossible_travel(
    account: AccountProfile,
    around_time: datetime,
    rng: random.Random,
) -> List[RawTransaction]:
    """
    IMPOSSIBLE TRAVEL: two transactions on the same account, close
    together in time, but geographically too far apart for the SAME
    person to have traveled between them. The defining structural
    feature is the implied speed (distance / time), not the absolute
    distance alone - this is why MAX_PLAUSIBLE_TRAVEL_SPEED_KMH is the
    actual check, not just "is the second location far away."

    Imperfection injected on purpose: the implied speed is set to
    EXCEED the plausible threshold by a random margin, not always by
    an enormous, obvious amount - sometimes just barely impossible,
    which is the harder, more realistic detection case and exactly the
    kind of borderline example docs/error_analysis.md should dig into.
    """
    # First transaction: normal, near home.
    first = RawTransaction(
        account_id=account.account_id,
        timestamp=around_time,
        amount=round(max(1.0, rng.gauss(account.typical_amount_mean, account.typical_amount_std)), 2),
        merchant_category=rng.choice(account.usual_merchant_categories),
        location_lat=round(account.home_lat + rng.uniform(-0.2, 0.2), 6),
        location_lng=round(account.home_lng + rng.uniform(-0.2, 0.2), 6),
        device_id=f"device-{account.account_id[:8]}",
        is_fraud=False,   # the FIRST transaction is the genuine one - only the second is the fraud attempt
        fraud_type=None,
    )

    # Second transaction: far enough away that the implied speed exceeds
    # the plausible ceiling, within a short time gap.
    time_gap_minutes = rng.uniform(5, 90)
    # distance needed to exceed the speed threshold, then add a random margin
    min_distance_km = MAX_PLAUSIBLE_TRAVEL_SPEED_KMH * (time_gap_minutes / 60.0)
    distance_km = min_distance_km * rng.uniform(1.15, 1.8)  # margin widened after the latitude bug fix below - see comment

    import math
    angle = rng.uniform(0, 360)

    # CORRECTNESS NOTE (found by actually testing this function, not by
    # inspection - see Phase 1 verification run): a flat "1 degree ~
    # 111 km" conversion is only accurate for LATITUDE. Longitude
    # degrees shrink toward the poles by a factor of cos(latitude).
    # The original version used 111 km/degree for both lat and lng,
    # which silently UNDER-distanced points generated mostly-eastward
    # at higher latitudes, occasionally producing a "fraud" pair whose
    # real haversine distance implied a speed BELOW the threshold -
    # i.e. a mislabeled non-impossible "impossible travel" example.
    # This would have quietly poisoned Phase 3's training labels.
    lat_delta_deg = (distance_km * math.cos(math.radians(angle))) / 111.0
    lng_km_per_deg = 111.0 * math.cos(math.radians(first.location_lat)) or 1e-6  # guard against pole edge case
    lng_delta_deg = (distance_km * math.sin(math.radians(angle))) / lng_km_per_deg

    second_lat = first.location_lat + lat_delta_deg
    second_lng = first.location_lng + lng_delta_deg

    second = RawTransaction(
        account_id=account.account_id,
        timestamp=first.timestamp + timedelta(minutes=time_gap_minutes),
        amount=round(max(1.0, rng.gauss(account.typical_amount_mean, account.typical_amount_std)), 2),
        merchant_category=rng.choice(MERCHANT_CATEGORIES),
        location_lat=round(second_lat, 6),
        location_lng=round(second_lng, 6),
        device_id=f"fraud-device-{uuid.uuid4().hex[:8]}",
        is_fraud=True,
        fraud_type="impossible_travel",
    )

    return [first, second]


def verify_impossible_travel_speed(first: RawTransaction, second: RawTransaction) -> float:
    """
    Utility used by tests (and reusable later by the real detector in
    Phase 2) to compute the implied travel speed between two
    transactions, in km/h. Exists so we can assert in tests that
    inject_impossible_travel() actually produces a speed above the
    threshold - proving the mechanism works, not just trusting it.
    """
    distance_km = haversine_km(
        first.location_lat, first.location_lng,
        second.location_lat, second.location_lng,
    )
    hours = (second.timestamp - first.timestamp).total_seconds() / 3600.0
    if hours <= 0:
        return float("inf")
    return distance_km / hours
