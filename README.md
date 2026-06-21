# 🛡️ Adaptive Fraud & Risk Scoring Engine

> A production-inspired Machine Learning & MLOps system for real-time fraud detection, explainability, drift monitoring, and automated retraining.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![XGBoost](https://img.shields.io/badge/XGBoost-ML_Model-orange)
![SHAP](https://img.shields.io/badge/SHAP-Explainable_AI-red)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)
![MLOps](https://img.shields.io/badge/MLOps-Production-purple)
![Status](https://img.shields.io/badge/Status-In_Progress-yellow)

---

# 📌 Project Status

**This project is in the planning/build phase — it is not yet complete.** This README documents the architecture, scope, and learning goals as designed, and will be updated phase by phase as each part is actually built. See `Tracker.md` for live, dated progress and real numbers (no placeholder metrics are claimed anywhere in this repo until they're measured).

---

# 📌 Overview

Adaptive Fraud & Risk Scoring Engine is a production-inspired machine learning system designed to detect fraudulent financial transactions in real time.

Unlike a typical fraud-detection portfolio notebook that stops at model training, this project is scoped to cover the complete ML lifecycle:

* Real-time transaction scoring
* Streaming feature engineering
* Imbalanced learning, done rigorously (not just "tried SMOTE")
* Explainable AI using SHAP
* Drift detection
* Automated retraining pipelines
* Load testing and horizontal scalability
* Monitoring dashboards
* Production deployment practices

The objective is to learn — deeply, not just superficially — how modern fraud detection systems are designed, deployed, monitored, and continuously improved in real-world financial organizations, and to have the research notes and experiment logs to prove that understanding in an interview.

---

# 🚨 Problem Statement

Fraud detection is one of the most challenging machine learning domains because:

* Fraud is extremely rare (often <1% of transactions)
* Fraud patterns evolve continuously as fraudsters adapt
* False positives carry a real business cost (blocked legitimate customers)
* Models must respond within milliseconds
* Regulatory and compliance requirements often demand explainable decisions

This project addresses these challenges through a combination of supervised learning, unsupervised anomaly detection, explainability, cost-sensitive threshold selection, and MLOps principles — see `PRD.md` for the full problem statement and `research/01_fraud_domain.md` for the underlying domain notes.

---

# 🎯 Project Goals

* Detect fraudulent transactions in real time
* Minimize false positives without ignoring the cost of false negatives
* Generate explainable risk scores, not black-box numbers
* Monitor model performance in production
* Detect data and concept drift before they cause silent decay
* Automate retraining workflows with a validation gate before promotion
* Build a scalable, production-ready architecture — explicitly proven, not just claimed

---

# 📈 Scale & Performance Commitment

> **The system is designed to scale to 10,000+ users while maintaining low-latency inference. Model performance improves over time through a feedback loop, drift monitoring, and scheduled retraining using newly collected labeled data.**

This is two separate, separately-proven claims — they are never merged into one in this project:

| Claim | Type | Proof |
|---|---|---|
| Latency holds steady at 10,000 concurrent users | Infrastructure engineering — stateless API, caching, connection pooling, horizontal scaling behind a load balancer | A real Locust/k6 load test comparing p99 latency at 10 vs. 10,000 simulated concurrent users, logged in `Tracker.md` |
| Model accuracy improves as usage grows | ML/data engineering — driven by the feedback loop and scheduled retraining, **not** by request volume itself | Before/after PR-AUC across retraining runs, logged in `Tracker.md` |

Full architecture for the scale claim is in `TechSpec.md` Section 6. No latency or scale number is stated anywhere in this repo without a corresponding logged measurement.

---

# 🏗️ System Architecture

```text
Transaction Stream
        │
        ▼
Feature Engineering (real-time, sliding window)
        │
        ▼
Load Balancer → Stateless API Replicas (FastAPI, async)
        │
        ▼
XGBoost + Isolation Forest
        │
        ▼
Risk Scoring Engine
        │
        ▼
SHAP Explainability
        │
        ▼
Decision Engine (cost-curve threshold)
        │
        ▼
Allow / Challenge / Block
        │
        ▼
Feedback Collection
        │
        ▼
Drift Detection (PSI)
        │
        ▼
Retraining Pipeline (validate → promote)
        │
        ▼
Dashboard (Streamlit) — visualizes every stage above
```

---

# ⚙️ Core Features (Planned for v1)

## Real-Time Risk Scoring
* FastAPI-based prediction service, async, designed for horizontal scaling
* Fraud probability scoring, calibrated (see `docs/calibration_analysis.md`)
* Risk score (0–100)
* Target: <100ms p99 latency, at both low load and 10,000 concurrent simulated users

## Feature Engineering

**Velocity Features** — transactions per minute / hour / day, total amount per window

**Geo-Velocity Features** — impossible travel detection, location change analysis

**Behavioral Features** — spending deviation, time-of-day deviation, merchant novelty

**Device Intelligence** — new device detection, IP/location change flags

Full formulas for every feature live in `docs/feature_dictionary.md` — kept as the single source of truth, updated the moment a formula changes.

---

# 🤖 Machine Learning Models

| Model | Purpose |
|---|---|
| Logistic Regression | Baseline — establishes an honest floor before reaching for anything more complex |
| XGBoost | Primary fraud classifier |
| Isolation Forest | Unsupervised detector for novel fraud patterns with no labeled history |

Full pros/cons and "why not Random Forest / why not a neural network" answers are in `docs/model_comparison.md`.

---

# 🧠 Explainable AI

The system uses SHAP (SHapley Additive exPlanations) to explain predictions.

**Global explanations** — which features drive fraud detection overall
**Local explanations** — why one specific transaction was flagged

Example shape of a local explanation (illustrative, not yet measured):

| Feature | Contribution |
|---|---|
| New Device | +35% |
| High Velocity | +25% |
| Unusual Location | +20% |
| High Amount | +12% |

Deeper notes on how and why SHAP works here: `research/05_shap_notes.md`.

---

# 📊 ML Concepts This Project Is Built to Cover

* Feature Engineering (real-time, sliding-window)
* Imbalanced Learning (class weighting vs. SMOTE vs. threshold tuning, compared)
* Logistic Regression, XGBoost, Isolation Forest
* SHAP Explainability
* Probability Calibration (Platt scaling / isotonic regression, Brier score)
* Cost-Sensitive Threshold Optimization
* Data Leakage Prevention
* Error Analysis (false positive/negative patterns, recall by fraud type)
* Drift Detection (PSI)
* Model Monitoring

Each of these has a dedicated, actively-maintained notes file — see **Research & Learning Notes** below.

---

# 🔄 MLOps Components

**Drift Detection** — PSI per feature, scheduled checks, alerting. *Deliberately gated to start only after modeling, SHAP, and the API are complete — see `ImplementationPlan.md` Phase 6 gate check. Built early on purpose, not by accident of getting distracted.*

**Retraining Pipeline** — feedback ingestion, scheduled or drift-triggered retraining, validation against the current model, promotion only if genuinely better.

**Monitoring** — latency, throughput, prediction distribution, average risk score, live fraud rate, threshold drift over time.

---

# 🚀 Production Engineering Concepts

* Stateless API architecture
* Horizontal scaling behind a load balancer
* Async FastAPI
* Connection pooling (database + cache)
* Caching layer for feature lookups
* Docker containerization
* CI/CD via GitHub Actions
* Load testing (Locust / k6) — the actual evidence behind the 10K-user claim
* Monitoring & alerting

---

<<<<<<< HEAD
# 🔒 Security

Security is treated as a non-negotiable, from-day-one concern (`Rules.md` Rule 17), not a Phase 10 add-on. Full detail in `Security.md`, covering:

* **Authentication** — none in v1 (honest gap, single-user demo); Supabase Auth + role-based checks designed for v2
* **Data access protection** — no real PII anywhere in this project by design; synthetic identifiers only; Row-Level Security planned if multi-tenancy is ever added
* **Secrets & API keys** — environment variables only, never committed, rotate-able without a code change
* **Input validation** — pydantic schema validation plus range/sanity checks, reject-don't-coerce on unexpected values
* **Abuse & bot prevention** — rate limiting, with legitimate load explicitly distinguished from abuse, and abuse patterns treated as a fraud signal in their own right
* **Secure deployment** — HTTPS-only, least-privilege database access, dependency scanning in CI, no internal detail leaked via health checks

A pre-deployment security checklist (also in `Security.md`) is run before any public deployment — not assumed to be fine by default.

---

=======
>>>>>>> 014e4aac363df9c8df2426d90bf48aa933c3e642
# 🛠️ Technology Stack

**Backend** — Python, FastAPI, scikit-learn, XGBoost, SHAP
**Database** — PostgreSQL (Supabase), connection-pooled
**Dashboard** — Streamlit
**Infrastructure** — Docker, GitHub Actions
**Load Testing** — Locust, k6

---

# 📂 Project Structure

```text
adaptive-fraud-risk-scoring-engine/
│
├── api/                          # FastAPI service
├── dashboard/                    # Streamlit app
├── pipeline/                     # Feature engineering, training, retraining
├── data/                         # Synthetic generator + benchmark dataset
│
├── docs/                         # Supporting analysis documents
│   ├── feature_dictionary.md
│   ├── model_comparison.md
│   ├── data_leakage.md
│   ├── error_analysis.md
│   └── calibration_analysis.md
│
├── research/                     # Concept-by-concept learning notes
│   ├── 01_fraud_domain.md
│   ├── 02_feature_engineering.md
│   ├── 03_imbalance_learning.md
│   ├── 04_xgboost_notes.md
│   ├── 05_shap_notes.md
│   ├── 06_drift_detection.md
│   └── 07_system_design.md
│
├── tests/                        # Unit + integration tests
├── load-tests/                   # Locust / k6 scripts
├── docker/                       # Dockerfiles, docker-compose
│
├── PRD.md
├── TechSpec.md
├── AppFlow.md
├── Design.md
├── schema.md
├── ImplementationPlan.md
├── Rules.md
<<<<<<< HEAD
├── Security.md
=======
>>>>>>> 014e4aac363df9c8df2426d90bf48aa933c3e642
├── Tracker.md
├── experiment_log.csv
├── README.md
├── requirements.txt
└── .gitignore
```

**Note:** `docs/` and `research/` are deliberately separate. `research/` is concept-learning notes (in the builder's own words, with interview-ready Q&A). `docs/` is project-specific analysis artifacts (the actual feature list, the actual model comparison, the actual leakage findings). Keeping them apart avoids exactly the kind of folder-structure drift that makes a repo hard to navigate later.

---

# 📚 Research & Learning Notes

This repo includes dedicated, actively-maintained learning notes — not generated summaries, but the builder's own understanding, checked against interview-style questions at the bottom of each file:

* `01_fraud_domain.md` — fraud patterns, the business cost trade-off, compliance reasoning
* `02_feature_engineering.md` — sliding windows, velocity/geo/behavioral features
* `03_imbalance_learning.md` — class weighting vs. SMOTE vs. threshold tuning
* `04_xgboost_notes.md` — gradient boosting internals, why XGBoost over alternatives
* `05_shap_notes.md` — how Shapley values work, why TreeExplainer
* `06_drift_detection.md` — PSI math, data drift vs. concept drift
* `07_system_design.md` — statelessness, caching, pooling, load balancing, async I/O

The goal isn't only a working project — it's being able to answer "why did you do X" from real understanding, not memory. See `Rules.md` Rule 16: these notes are written and personalized by the builder, not auto-generated.

---

# 🗺️ Development Roadmap

This roadmap is the single source of truth and matches `ImplementationPlan.md` exactly — no duplicate or conflicting phase list exists elsewhere in this repo.

| Phase | Focus | Status |
|---|---|---|
| 0 | Setup — repo structure, environment, database tables | Start |
| 1 | Data Foundations — benchmark dataset, synthetic generator | Not started |
| 2 | Feature Engineering — velocity, geo-velocity, behavioral features, leakage checks | Not started |
| 3 | Modeling — baseline, XGBoost, Isolation Forest, SHAP, calibration, error analysis | Not started |
| 4 | API Service — async FastAPI, caching, pooling, built stateless from the start | Not started |
| 5 | Dashboard — Streamlit, all panels including System Health | Not started |
| 6 | Drift Monitoring & Retraining Loop *(gated — see ImplementationPlan.md)* | Not started |
| 7 | Testing — unit + integration | Not started |
| 8 | Containerization & Horizontal Scaling Setup | Not started |
| 9 | Load Testing & Deployment — where the 10K-user claim gets proven | Not started |
| 10 | Final Polish — README, demo video, documentation completeness check | Not started |

Live, dated status updates: `Tracker.md`.

---

# 🔮 Future Enhancements (v2+, Explicitly Out of Scope for v1)

* Kafka-based transaction streaming
* Redis feature store at larger scale
* Kubernetes deployment
* Multi-user auth and role-based permissions
* A/B testing of model versions on live traffic
* A formal model registry (e.g. MLflow)
* LLM-powered fraud investigation assistant

See `PRD.md` Section 4 for the full out-of-scope list and reasoning.

---

# 🎓 Learning Outcomes

By completing this project, the goal is hands-on, defensible-in-an-interview experience in:

* Machine learning engineering under real constraints (imbalance, calibration, explainability)
* Feature engineering on streaming/real-time data
* Fraud analytics and domain reasoning
* Explainable AI (SHAP)
* MLOps — drift detection, automated retraining with a validation gate
* Production system design — statelessness, caching, pooling, horizontal scaling
* FastAPI, Docker, CI/CD
* Load testing and honestly proving a scalability claim with real numbers

---

# 👨‍💻 Author

**Shubham Gupta**
Machine Learning • AI Engineering • MLOps

---

⭐ This project is being built in the open, phase by phase. Follow `Tracker.md` for real progress, or check back as phases are completed.
