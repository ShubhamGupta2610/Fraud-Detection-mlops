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

Document your actual decision here once made (per `research/02_feature_engineering.md`):

> For an account with no prior history, the following defaults are used: ___

## Feature versioning

If a feature's formula changes after the model has been trained on it once, increment a `feature_set_version` and note the change below — this matters for explaining any sudden change in model behavior later.

| Date | Feature Changed | Old Definition | New Definition | Reason |
|---|---|---|---|---|
| | | | | |
