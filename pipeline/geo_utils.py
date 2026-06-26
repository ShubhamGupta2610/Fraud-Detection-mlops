"""
Shared geographic distance utility.

WHY THIS WAS PROMOTED OUT OF fraud_patterns.py:
Phase 1's fraud_patterns.py originally defined _haversine_km() as a
private helper for generating impossible_travel examples. Phase 2 needs
the EXACT same distance calculation for the geo_velocity feature - if
each phase had its own copy, they could silently drift apart (e.g. one
gets updated/fixed and the other doesn't), which would mean the
generator's definition of "impossible" and the detector's definition of
"impossible" stop agreeing with each other. That mismatch would be a
subtle, hard-to-notice bug: the model might fail to flag exactly the
cases the generator intended to be detectable.

Single source of truth lives here now; fraud_patterns.py imports from
this module instead of defining its own copy (see the updated import
there).
"""

import math


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two lat/lng points, in kilometers."""
    R = 6371.0
    lat1r, lng1r, lat2r, lng2r = map(math.radians, [lat1, lng1, lat2, lng2])
    dlat = lat2r - lat1r
    dlng = lng2r - lng1r
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1r) * math.cos(lat2r) * math.sin(dlng / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))
