"""
Device-related features, per docs/feature_dictionary.md:
is_new_device, is_new_ip_or_location.
"""

from datetime import datetime
from pipeline.features.history_store import AccountHistoryStore
from pipeline.geo_utils import haversine_km

# Distance (km) from the account's known locations beyond which a
# transaction counts as "new location" rather than ordinary local
# movement. Named here as a parameter rather than a buried literal -
# 50km comfortably covers normal intra-city movement while still
# flagging a genuinely different area.
NEW_LOCATION_THRESHOLD_KM = 50.0


def is_new_device(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
    current_device_id: str,
) -> int:
    """
    feature_dictionary.md: is_new_device.
    1 if this device_id has never been seen before for this account.

    COLD-START NOTE: an account's very first-ever transaction will
    always have is_new_device=1, for the same honest reason as
    merchant_category_novelty in behavioral.py - there's no prior
    device to compare against, so "new" is simply true, not a special
    case to suppress.
    """
    known = store.known_devices(account_id, at_time)
    return 0 if current_device_id in known else 1


def is_new_ip_or_location(
    store: AccountHistoryStore,
    account_id: str,
    at_time: datetime,
    current_lat: float,
    current_lng: float,
) -> int:
    """
    feature_dictionary.md: is_new_ip_or_location.
    1 if the current location is more than NEW_LOCATION_THRESHOLD_KM
    from EVERY previously seen location for this account, else 0.

    Distinguished from geo_velocity (features/geo.py): geo_velocity asks
    "is the IMPLIED SPEED to get here physically plausible." This
    feature asks a simpler question that doesn't involve time at all -
    "have we ever seen this account anywhere near here before." A
    legitimate slow road trip would NOT trigger geo_velocity's
    impossible-speed check, but WOULD correctly trigger this feature -
    they catch different things and that's intentional, not redundant.

    COLD-START: with no prior transactions, every location is "new" by
    definition - same honest-novelty reasoning as is_new_device above.
    """
    history = store.transactions_before(account_id, at_time)
    if not history:
        return 1

    min_distance = min(
        haversine_km(t.location_lat, t.location_lng, current_lat, current_lng)
        for t in history
    )
    return 1 if min_distance > NEW_LOCATION_THRESHOLD_KM else 0
