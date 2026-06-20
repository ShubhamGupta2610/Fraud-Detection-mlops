# TechSpec.md: Adaptive Fraud & Risk Scoring Engine

## 1. Frontend / Dashboard Stack

Streamlit (Python). Chosen to keep the dashboard and ML pipeline in one codebase with no separate frontend build step. React + Recharts is a reasonable v2 upgrade once the system works end-to-end.

## 2. Backend Stack

| Layer | Technology | Reason |
|---|---|---|
| API service | FastAPI (async) | Native async support is required for the scaling design in Section 6 — a sync framework would bottleneck under concurrent load |
| ML libraries | XGBoost, scikit-learn (Isolation Forest), SHAP | Industry-standard for tabular fraud modeling and explainability |
| Feature computation | Pandas + cache layer (Section 6.3) | Sliding-window features must be fast to compute repeatedly under load |
| Scheduling (drift checks, retraining) | Python `schedule` library or cron | Runs independently of the API service so it never competes with request latency |

## 3. Database

| Purpose | Choice | Reason |
|---|---|---|
| Transaction & feedback log | PostgreSQL (Supabase) with connection pooling | SQLite cannot handle concurrent writes at any real scale; pooling (pgbouncer or SQLAlchemy's pool) prevents the database from being the bottleneck once concurrency increases |
| Model artifacts | Local filesystem / Docker volume, versioned by filename + timestamp | A model registry (MLflow) is a clean v2 upgrade |

## 4. Authentication Method

v1: none required (single-user, demo deployment). Designed-for v2: email+password or magic-link auth with a `role` column, per `schema.md`.

## 5. APIs Needed

- `POST /score` — accepts a transaction payload, returns risk score, decision, and SHAP explanation
- `GET /metrics` — current model performance stats for the dashboard
- `GET /drift-status` — current PSI values and alert state
- `POST /feedback` — logs a confirmed outcome (fraud / not fraud) for a past transaction, feeding retraining
- `POST /retrain` (internal/admin only) — manually triggers a retraining run
- `GET /health` — lightweight liveness/readiness check, used by the load balancer to know which replicas are healthy

## 6. Scalability Architecture — Designing for 10,000 Concurrent Users

This section exists because of one explicit project requirement: **the system must remain just as responsive at 10,000 users as it is at 10, with no degradation in latency or accuracy.** This is split into two genuinely different engineering problems, addressed separately below.

### 6.1 The Two Claims, Engineered Separately

| Claim | Type of problem | Where it's solved |
|---|---|---|
| Latency holds steady at 10,000 concurrent users | Infrastructure / systems engineering | Sections 6.2–6.6 below |
| Accuracy holds steady (and improves) as usage grows | ML / data engineering | The feedback loop + retraining pipeline (Section 7), **not** the infrastructure layer |

These are never conflated. More concurrent traffic does not, by itself, make a model more accurate — it makes more feedback data *available*, which the retraining loop then uses to improve accuracy over time. The infrastructure's job is purely to keep serving fast and correct regardless of load.

### 6.2 Statelessness

The FastAPI service holds no per-request state in memory between calls beyond the cache (6.3). This is what makes horizontal scaling possible at all — any replica can serve any request, so adding replicas linearly adds capacity.

### 6.3 Caching Layer

Feature computation (Section in `AppFlow.md`) requires recent transaction history per account. Recomputing this from the database on every request under high concurrency would make the database the bottleneck. A cache (Redis, or an in-process LRU cache for v1/lower scale) stores each account's recent rolling-window data, refreshed incrementally as new transactions arrive, so feature lookups stay fast independent of total request volume.

### 6.4 Connection Pooling

Both the database and the cache layer use connection pooling (SQLAlchemy pool / pgbouncer for Postgres) so that 10,000 concurrent requests don't each try to open a new raw connection — pooling reuses a bounded set of connections efficiently.

### 6.5 Horizontal Scaling Behind a Load Balancer

```
                     ┌─────────────────┐
 Incoming Requests → │  Load Balancer   │
                     └────────┬─────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
   │ API Replica │     │ API Replica │     │ API Replica │
   │  (FastAPI)  │     │  (FastAPI)  │     │  (FastAPI)  │
   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
          │                   │                   │
          └─────────┬─────────┴─────────┬─────────┘
                     ▼                   ▼
            ┌────────────────┐  ┌────────────────┐
            │  Cache (Redis)  │  │ PostgreSQL Pool │
            └────────────────┘  └────────────────┘
```

Because the API is stateless (6.2), the load balancer can route requests to any replica. Adding more replicas under load is how the system absorbs 10,000 concurrent users without each individual request getting slower — this is the core mechanism behind the "same responsiveness at 10K users" claim.

### 6.6 Async I/O

FastAPI's async request handling means a single replica can hold many requests in flight concurrently (rather than blocking one thread per request), so each replica's effective capacity is much higher than a synchronous framework's — fewer replicas are needed to hit the same target, which keeps the v1 deployment realistically affordable for a solo build.

### 6.7 Model Inference Performance

XGBoost inference on a single transaction's feature vector is computationally cheap (microseconds, not milliseconds) — the model itself is not the bottleneck at any realistic scale. The bottleneck, if any appears under load testing, will be in feature computation or I/O, not in the model's `.predict()` call. This is worth stating explicitly because it's a common, reasonable interview follow-up ("isn't the model itself slow under load?") — it isn't, here.

### 6.8 Load Testing Plan

Use Locust or k6 to simulate concurrent users hitting `/score`:
1. Baseline run: 10 concurrent simulated users, record p50/p95/p99 latency
2. Scaled run: 10,000 concurrent simulated users, record the same percentiles
3. Compare side by side — the deliverable is a chart showing these two runs with comparable latency, plus the replica count and resource usage at each level
4. This chart, with real numbers, is the actual proof behind the scale claim — not an assertion

## 7. The Accuracy-Over-Time Mechanism (Distinct From Scale)

Model accuracy improves through this loop, independent of traffic volume:

```
More usage → More transactions scored → More outcomes eventually confirmed (feedback)
   → Feedback stored → Drift monitor checks for feature/score distribution shift
   → Scheduled or drift-triggered retraining on accumulated feedback
   → New model validated against current model (PR-AUC comparison)
   → Promoted only if genuinely better → Repeat
```

More users *can* accelerate this loop, because more transactions means more feedback data accumulates faster — but the mechanism is the feedback loop, not the request volume itself. This distinction is what `PRD.md` Section 5 captures and what should be repeated consistently anywhere this project is discussed.

## 8. Security Requirements

- No real PII or real payment data — synthetic and public benchmark data only
- API keys/secrets via environment variables, never hardcoded or committed
- Rate limiting on `/score` to prevent abuse, layered with the load balancer's own throttling
- Input validation on every endpoint (pydantic models)

## 9. Performance Requirements

| Requirement | Target |
|---|---|
| Scoring latency (p99), low load | < 100ms |
| Scoring latency (p99), 10,000 concurrent simulated users | Within the same band as low load — no meaningful degradation |
| Dashboard refresh | Polling every 2–5 seconds is acceptable for v1 |
| Retraining job duration | Comfortably within its scheduled interval (e.g. under 10 minutes for a daily job) |

## 10. Third-Party Integrations

- Kaggle "Credit Card Fraud Detection" dataset (or equivalent) for offline training/evaluation
- Supabase (managed PostgreSQL + optional v2 auth)
- GitHub Actions for CI/CD
- Locust or k6 for load testing (Section 6.8)
