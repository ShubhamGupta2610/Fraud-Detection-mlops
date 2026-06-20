# schema.md: Adaptive Fraud & Risk Scoring Engine

This system's core data model is transactions, scores, feedback, model run history, and (new) load-test results — not a typical app's user-content tables.

## 1. Table: transactions

| Column | Type | Notes |
|---|---|---|
| transaction_id | UUID, primary key | |
| account_id | VARCHAR, indexed | Synthetic account identifier |
| timestamp | TIMESTAMP, indexed | When the transaction occurred |
| amount | DECIMAL | |
| merchant_category | VARCHAR | |
| location_lat / location_lng | FLOAT | Used for geo-velocity features |
| device_id | VARCHAR | |
| raw_features_json | JSONB | Snapshot of computed features at scoring time |

## 2. Table: scores

| Column | Type | Notes |
|---|---|---|
| score_id | UUID, primary key | |
| transaction_id | UUID, FK → transactions.transaction_id | |
| model_version | VARCHAR, indexed | References model_runs.version |
| risk_score | FLOAT (0–100) | |
| decision | ENUM: allow / challenge / block | |
| threshold_used | FLOAT | Threshold active at decision time |
| shap_top_features_json | JSONB | Top contributing features and SHAP values |
| scored_at | TIMESTAMP | |
| replica_id | VARCHAR | Which API replica served this request — useful for diagnosing load-related issues |
| latency_ms | FLOAT | Time taken to score this transaction — feeds the System Health page directly |

## 3. Table: feedback

| Column | Type | Notes |
|---|---|---|
| feedback_id | UUID, primary key | |
| transaction_id | UUID, FK → transactions.transaction_id | |
| confirmed_label | ENUM: fraud / legitimate | Ground truth — feeds retraining |
| source | VARCHAR | e.g. 'synthetic_generator', 'manual_review' |
| recorded_at | TIMESTAMP | |

## 4. Table: model_runs

| Column | Type | Notes |
|---|---|---|
| run_id | UUID, primary key | |
| version | VARCHAR, unique, indexed | Timestamp-based version tag |
| trained_at | TIMESTAMP | |
| trigger_type | ENUM: scheduled / drift_triggered / manual | |
| pr_auc | FLOAT | Validation metric used for the promotion gate |
| promoted | BOOLEAN | Whether this version became the live model |
| artifact_path | VARCHAR | Filesystem/volume path to the saved model |
| feedback_rows_used | INTEGER | How much accumulated feedback fed this retraining — ties directly to the "accuracy improves through feedback volume" claim in PRD.md |

## 5. Table: drift_checks

| Column | Type | Notes |
|---|---|---|
| check_id | UUID, primary key | |
| checked_at | TIMESTAMP | |
| feature_name | VARCHAR | |
| psi_value | FLOAT | |
| alert_fired | BOOLEAN | |

## 6. Table: load_test_runs *(new)*

| Column | Type | Notes |
|---|---|---|
| test_id | UUID, primary key | |
| run_at | TIMESTAMP | |
| concurrent_users | INTEGER | e.g. 10, 1000, 10000 |
| p50_latency_ms | FLOAT | |
| p95_latency_ms | FLOAT | |
| p99_latency_ms | FLOAT | |
| replica_count | INTEGER | Number of API replicas active during this test |
| error_rate | FLOAT | Percentage of failed requests during the test |
| notes | TEXT | e.g. "baseline run", "10K scale-test run" |

This table is the literal evidence store behind the scale claim — every number quoted in an interview about "10,000 users, same responsiveness" should trace back to a row here, not to a remembered or estimated figure.

## 7. Table: users *(v2 design intent, not built in v1)*

| Column | Type | Notes |
|---|---|---|
| user_id | UUID, primary key | |
| email | VARCHAR, unique | |
| role | ENUM: operator / compliance_viewer / admin | |
| created_at | TIMESTAMP | |

## 8. Relationships

- `transactions` 1–1 `scores` in practice (modeled as FK for clarity and future re-scoring support)
- `transactions` 1–1 `feedback` (a transaction eventually gets at most one confirmed label)
- `scores.model_version` → `model_runs.version` (logical reference)
- `drift_checks` has no FK to `transactions` — it's an aggregate feature-level check
- `load_test_runs` is standalone — it records infrastructure behavior, not transaction-level data

## 9. Permissions & Data Ownership

- v1: no user-level ownership — single operator has full access via the dashboard and API
- v2 design intent: `compliance_viewer` role gets read-only access to `scores`, `drift_checks`, `model_runs`, `load_test_runs`; no write access to threshold or retraining triggers
- No real PII is stored — `account_id` and `device_id` are synthetic identifiers
