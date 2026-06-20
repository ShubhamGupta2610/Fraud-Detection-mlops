# PRD: Adaptive Fraud & Risk Scoring Engine

## 1. Problem Statement

**What problem does this solve?**
Payment platforms must approve or decline transactions within milliseconds with very little direct evidence of fraudulent intent. Fixed rule-based systems ("block if amount > $1000") can't keep pace with fraud patterns that shift constantly. Naive ML approaches fail silently too — with fraud often under 1% of transactions, a model that predicts "never fraud" already looks 99%+ accurate while catching nothing. This system replaces both approaches with a model that is evaluated correctly under class imbalance, explains every decision, detects when its own accuracy is decaying, and is built to hold up under real production load.

**Who experiences this problem?**
Fraud analysts and risk managers at fintech/payments companies, who currently rely on static rules or black-box models that can't be trusted, explained, or relied on to stay accurate as both fraud patterns and traffic volume grow.

**Why does this problem matter now?**
Fraud patterns evolve weekly as bad actors adapt. A model trained once and never monitored becomes a liability, not an asset. Compliance increasingly demands explainable declines, not just accurate ones. And any system that can't maintain its latency and reliability as traffic scales is not actually production-viable, no matter how good its offline metrics look.

## 2. Target User

**Primary user:** A fraud analyst (simulated persona) who reviews flagged transactions, needs to understand *why* a transaction was flagged, and occasionally overrides decisions.

**Secondary user:** A risk/compliance manager (simulated persona) who monitors fraud trends, model health, and the dollar cost impact of the current decision threshold — including how the system behaves under load.

**Goals:** Catch fraud early, avoid blocking legitimate customers, trust the system will flag it if something changes, trust it won't slow down or degrade as usage grows.
**Frustrations:** Black-box scores with no explanation; models that quietly get worse over time with no alert; systems that work fine in a demo but fall over under real traffic.
**Behaviors:** Checks a dashboard regularly rather than digging through raw logs; needs a fast, scannable view at any traffic level, not just at demo scale.

## 3. Core Features (MVP Only)

1. **Real-time transaction scoring API** — A FastAPI `/score` endpoint that accepts a transaction and returns a risk score (0–100) plus a decision (allow/challenge/block) in under 100ms, designed to hold that latency under concurrent load, not just on a single request.
2. **Real-time feature engineering** — Computes velocity, geo-velocity, and behavioral-deviation features over a sliding window from a synthetic transaction stream.
3. **Fraud classifier with imbalance handling** — XGBoost as the primary supervised model, with Isolation Forest as an unsupervised companion for catching novel fraud patterns with no labeled history.
4. **Per-transaction explainability** — SHAP values returned with every score, showing which features drove the decision.
5. **Cost-curve threshold selection** — A dashboard panel that lets the threshold be tuned against a live-computed cost trade-off (missed fraud $ vs. wrongly-blocked-customer $), rather than defaulting to 0.5.

**Nice to Have (not needed for launch):**
- Drift monitoring (PSI-based) and automated retraining loop
- Multi-user roles/auth
- Full Business Impact and Live Transaction Feed dashboard panels

## 4. Out of Scope

- Multi-user accounts, login, or role-based permissions (designed for in the schema, not built in v1)
- Real payment processor integration — synthetic data and a public benchmark dataset only
- Kafka or true streaming infrastructure for v1 — a simulated stream + load-tested API stands in for it
- Kubernetes for v1 — horizontal scaling is designed for and load-tested, but orchestrated via docker-compose + a load balancer, not a full K8s cluster, to keep solo-build scope realistic
- A/B testing of model versions on live traffic
- Model registry tooling (e.g., MLflow) — manual versioning is sufficient
- Monetization, payments, or billing of any kind — this is an internal/portfolio tool

## 5. Scale & Performance Commitment

> **The system is designed to scale to 10,000+ users while maintaining low-latency inference. Model performance improves over time through a feedback loop, drift monitoring, and scheduled retraining using newly collected labeled data.**

This statement has two distinct, separately-verifiable parts — see `TechSpec.md` Section 6 for the architecture and `Tracker.md` for the load-test results that prove each one:

| Claim | What it means | What proves it |
|---|---|---|
| Scales to 10,000+ concurrent users, same latency | Infrastructure/engineering claim — async I/O, caching, horizontal scaling, connection pooling | A load test (e.g. Locust/k6) showing p99 latency at 10 users vs. 10,000 simulated concurrent users, side by side |
| Model performance improves over time | ML/data claim — driven by the feedback loop and retraining, not by traffic volume itself | Before/after PR-AUC across retraining runs as feedback data accumulates |

These two claims are never merged into one in any document, demo, or conversation about this project — they are proven independently, because they come from different parts of the system.

## 6. Success Metrics

- **Scoring latency (p99) at low load:** Under 100ms per transaction
- **Scoring latency (p99) at 10,000 simulated concurrent users:** Within the same target band as low load (no meaningful degradation) — this is the headline load-test number for interviews
- **Precision-Recall AUC:** Meaningfully above the logistic-regression baseline on the benchmark dataset
- **Model improvement over time:** Demonstrable PR-AUC increase across at least 2 retraining cycles as feedback data accumulates
- **Explainability coverage:** 100% of flagged transactions return a SHAP-based explanation
- **Deployment:** A live, publicly reachable URL serving the dashboard, backed by the deployed, load-tested API in Docker

## 7. Technical Assumptions

- **Frontend/Dashboard:** Streamlit (Python)
- **Backend:** FastAPI (async), XGBoost, scikit-learn (Isolation Forest), SHAP
- **Database:** PostgreSQL (Supabase free tier), with connection pooling (pgbouncer or SQLAlchemy pool) so it doesn't become the bottleneck under load
- **Caching:** In-memory or Redis cache for frequently-accessed feature lookups (account history) to keep feature computation fast under concurrent load
- **Scaling approach:** Stateless FastAPI service behind a load balancer, horizontally scaled (multiple container replicas) — see `TechSpec.md` Section 6 for the full design
- **Platform:** Web only, desktop-first
- **Deployment:** Docker + docker-compose locally; deployed to a cloud platform that supports horizontal scaling (Render/Railway with multiple instances, or AWS ECS/EC2 behind a load balancer)
- **Integrations:** Public benchmark dataset (Kaggle Credit Card Fraud Detection) for offline training; load-testing tool (Locust or k6) for the 10K-user proof; no third-party auth/payment integrations in v1

## 8. Open Questions

1. What's the target PR-AUC improvement over baseline that counts as "meaningfully better"?
2. Is a simulated 10,000-concurrent-user load test (via Locust/k6 against the deployed API) sufficient proof for the scale claim, or is real traffic needed — and if simulated, what's the honest way to describe this in an interview ("load-tested to handle," not "served")?
3. Should the cache layer be Redis from day one, or start as an in-process cache and only add Redis once the load test shows it's actually needed?
4. At what feedback-data volume does the retraining loop produce a measurable PR-AUC improvement — should this be estimated before building, or discovered empirically?
5. Should horizontal scaling be demonstrated via multiple Docker containers on one VM (cheap, simple) or genuinely separate instances behind a real load balancer (more realistic, more setup)?
