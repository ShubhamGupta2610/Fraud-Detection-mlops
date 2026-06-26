"""
Geo-velocity feature, per docs/feature_dictionary.md and
research/02_feature_engineering.md.

geo_velocity = distance(prev_location, current_location) / time_elapsed

Reuses pipeline.geo_utils.haversine_km and the same
MAX_PLAUSIBLE_TRAVEL_SPEED_KMH constant defined in
pipeline.generators.fraud_patterns - per the reasoning in geo_utils.py,
the generator's notion of "impossible" and this feature's notion of
"impossible" must be the same definition, not two that could drift apart.
"""

from datetime import datetime
from pipeline.features.history_store import AccountHistoryStore
from pipeline.geo_utils import haversine_km
from pipeline.generators.fraud_patterns import MAX_PLAUSIBLE_TRAVEL_SPEED_KMH


def geo_velocity(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
    current_lat: float,
    current_lng: float,
) -> float:
    """
    Implied travel speed (km/h) between this account's previous
    transaction and the current one.

    COLD-START DECISION (research/02_feature_engineering.md asks this
    explicitly): if there IS no previous transaction (this is the
    account's first-ever transaction), there is nothing to compute a
    velocity against. We return 0.0 rather than null/None - documented
    here and in feature_dictionary.md's cold-start section - because
    0.0 reads naturally as "no anomalous travel detected" to a
    downstream model, whereas a null would need special-case handling
    in every consumer of this feature. The alternative (treating
    cold-start as maximally suspicious) was considered and rejected:
    it would make every brand-new account's first transaction look
    like a geo-velocity red flag for no real reason, which would hurt
    precision specifically on the accounts we have the LEAST evidence
    about - the opposite of what we want.
    """
    previous = store.last_transaction_before(account_id, at_time)
    if previous is None:
        return 0.0

    distance_km = haversine_km(
        previous.location_lat, previous.location_lng,
        current_lat, current_lng,
    )
    hours_elapsed = (at_time - previous.timestamp).total_seconds() / 3600.0

    if hours_elapsed <= 0:
        # Two transactions logged at the exact same timestamp (or out of
        # order, which point_in_time_features.py's processing order
        # should prevent - this is a defensive guard, not the expected
        # path). Treat as maximally suspicious rather than dividing by
        # zero or returning a misleadingly small number.
        return float("inf") if distance_km > 0 else 0.0

    return round(distance_km / hours_elapsed, 2)


def is_impossible_travel(speed_kmh: float) -> bool:
    """
    Thin wrapper naming the same threshold used in fraud_patterns.py -
    exposed here so Phase 3 modeling / Phase 3 error analysis can flag
    "the rule-based version would have caught this" as a comparison
    point against the learned model, per docs/model_comparison.md's
    spirit of always having an alternative to compare against.
    """
    return speed_kmh > MAX_PLAUSIBLE_TRAVEL_SPEED_KMH
