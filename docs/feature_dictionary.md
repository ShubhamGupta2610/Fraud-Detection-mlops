# Feature Dictionary

Every feature the model uses, with its exact definition. Keep this file as the single source of truth — if a feature's formula changes during development, update it here immediately, not after the project is "done."

| Feature | Formula / Definition | Category | Notes |
|---|---|---|---|
| `txn_count_1min` | Count of transactions on this account in the last 1 minute | Velocity | Catches card-testing bursts |
| `txn_count_1h` | Count of transactions on this account in the last 1 hour | Velocity | |
| `txn_count_24h` | Count of transactions on this account in the last 24 hours | Velocity | |
| `total_amount_1h` | Sum of transaction amounts in the last 1 hour | Velocity | |
| `total_amount_24h` | Sum of transaction amounts in the last 24 hours | Velocity | |
| `distinct_merchants_24h` | Count of distinct merchant categories in the last 24 hours | Velocity | Unusual merchant variety can indicate testing |
| `geo_velocity` | distance(prev_location, current_location) ÷ time_elapsed | Geo | Implied travel speed; flagged if it exceeds a plausible travel speed ceiling |
| `is_new_device` | 1 if `device_id` has not been seen before for this account, else 0 | Device | |
| `is_new_ip_or_location` | 1 if location/IP differs significantly from the account's recent history, else 0 | Device/Geo | |
| `amount_deviation_from_avg` | (current `amount` − account's rolling average amount) ÷ account's rolling standard deviation | Behavioral | A z-score; large values indicate an unusual transaction size for this account |
| `hour_of_day_deviation` | How unusual the current transaction's hour-of-day is relative to the account's typical active hours | Behavioral | |
| `merchant_category_novelty` | 1 if this merchant category is new for this account, else 0 | Behavioral | |

## Cold-start handling

Implemented in Phase 2 (`pipeline/features/`), the actual decisions made — deliberately asymmetric, not one blanket rule:

| Feature group | Cold-start behavior | Why |
|---|---|---|
| Velocity (`txn_count_*`, `total_amount_*`, `distinct_merchants_24h`) | Returns 0 | No prior transactions exist in the window — honestly zero, not a special case |
| `geo_velocity` | Returns 0.0 | No previous transaction to compare location against |
| `amount_deviation_from_avg`, `hour_of_day_deviation` | Returns 0.0 below `MIN_HISTORY_FOR_BASELINE` (5 transactions) | A mean/stdev computed from 1-4 points is noise, not a real baseline. Treating cold-start as "automatically suspicious" would systematically hurt new accounts' precision with no real justification |
| `merchant_category_novelty`, `is_new_device`, `is_new_ip_or_location` | Returns 1 (novel/new) even on the very first transaction | This is honestly correct, not a default to suppress — a first transaction genuinely is in a new category, on a new device, at a new location. Unlike the statistical features above, there's no noise problem here to guard against |

This asymmetry — some cold-start cases default to "not suspicious," others correctly remain "novel" — is intentional and documented in `research/02_feature_engineering.md`.

## Implementation notes (Phase 2)

- All sliding-window lookups go through `pipeline/features/history_store.py`'s `transactions_before()`, which enforces a single boundary rule everywhere: strictly `timestamp < at_time`, never `<=`. This is the one piece of logic every feature depends on for leakage safety — see `docs/data_leakage.md` Section 2.
- `geo_velocity` and the `impossible_travel` fraud-pattern generator (Phase 1) share one `haversine_km()` implementation, in `pipeline/geo_utils.py`, specifically so the generator's definition of "impossible" and the detector's definition can never silently drift apart.
- `BASELINE_WINDOW` (behavioral features) = 90 days; `MIN_HISTORY_FOR_BASELINE` = 5 transactions; `NEW_LOCATION_THRESHOLD_KM` (device features) = 50km. All defined as named constants in their respective modules, not buried literals.

## Feature versioning

If a feature's formula changes after the model has been trained on it once, increment a `feature_set_version` and note the change below — this matters for explaining any sudden change in model behavior later.

| Date | Feature Changed | Old Definition | New Definition | Reason |
|---|---|---|---|---|
| | | | | |
