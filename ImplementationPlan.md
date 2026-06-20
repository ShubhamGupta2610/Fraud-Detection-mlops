# ImplementationPlan.md: Adaptive Fraud & Risk Scoring Engine

Ordered so each concept is understood before it's needed for the next phase. Load-testing is woven through Phases 4, 8, and 9 rather than bolted on at the end, since "scales to 10K users" needs to be proven against a real, evolving system, not retrofitted onto a finished one.

## Standing Habit: Research Notes and Experiment Logging

Throughout every phase below, two things run continuously alongside the code — they are not a separate phase, because if left until the end they get rebuilt from memory instead of captured while fresh:

- **`research/` notebook** — as each ML concept in a phase is actually learned (not just used), write your own-words notes in the matching file (`01_fraud_domain.md` through `07_system_design.md`). The test of "actually learned" is whether you can answer the interview-ready questions at the bottom of each file without looking anything up.
- **`experiment_log.csv`** — every time a model is trained or a threshold changed, add a row. This is what makes `docs/model_comparison.md` and `docs/error_analysis.md` factual instead of reconstructed from memory later.

## Scope Discipline: Don't Let MLOps Distract From ML

Drift detection (Phase 6) is explicitly placed after modeling, explainability, and the API are done. **Do not begin implementing the drift monitor until all three of the following are checked:**
- [ ] Feature engineering complete (Phase 2)
- [ ] XGBoost modeling complete, including the imbalance comparison (Phase 3)
- [ ] SHAP explainability complete (Phase 3)
- [ ] API complete (Phase 4)

This ordering exists because it's easy to get pulled into MLOps tooling before genuinely understanding the ML fundamentals underneath it — and the fundamentals are what actually get tested in an interview.

## Phase 0 — Setup
- Initialize repo: `/api`, `/dashboard`, `/pipeline`, `/data`, `/tests`, `/docker`, `/load-tests`
- Set up Python environment, requirements.txt
- Set up PostgreSQL (Supabase) and create the tables from `schema.md`
- **Deliverable:** running project skeleton with database connectivity confirmed

## Phase 1 — Data Foundations
- Load the public benchmark fraud dataset
- Build the synthetic transaction generator with injected fraud patterns
- Begin `research/01_fraud_domain.md` — work through the fraud pattern checklist as patterns are implemented in the generator
- **Deliverable:** a script that produces a realistic stream of synthetic transactions on demand

## Phase 2 — Feature Engineering
- Implement sliding-window velocity features
- Implement geo-velocity features
- Implement behavioral deviation features
- Document every feature in `docs/feature_dictionary.md` as it's built — not after
- Begin `research/02_feature_engineering.md`
- Run the temporal-leakage checks from `docs/data_leakage.md` Section 2 against this phase's features specifically (sliding windows are the most common place to accidentally leak future data)
- **Deliverable:** a unit-tested feature module taking a raw transaction + recent history → feature vector, fully documented in `docs/feature_dictionary.md`

## Phase 3 — Modeling
- Train logistic regression baseline; document the accuracy-under-imbalance trap explicitly in `research/01_fraud_domain.md`
- Log this and every subsequent run in `experiment_log.csv`
- Train XGBoost; compare class weighting vs. SMOTE vs. threshold tuning — write the reasoning in `research/03_imbalance_learning.md`, including the SMOTE-before-vs-after-split check from `docs/data_leakage.md` Section 3
- Train Isolation Forest as the unsupervised companion
- Complete `docs/model_comparison.md`, including the "why not Random Forest / why not neural networks" answers
- Build the cost curve; select a threshold deliberately
- Add SHAP explainability; write `research/05_shap_notes.md`
- Run the full `docs/data_leakage.md` checklist against the final feature set and model before calling this phase done
- Complete `docs/calibration_analysis.md` — calibration curve, Brier score, and a documented choice between raw output / Platt scaling / isotonic regression
- Complete `docs/error_analysis.md` — false positive and false negative analysis, recall broken down by fraud type
- **Deliverable:** a saved, versioned model artifact + evaluation report (PR-AUC, calibration, cost curve), with `experiment_log.csv`, `model_comparison.md`, `error_analysis.md`, and `calibration_analysis.md` all filled in with real numbers, not placeholders

## Phase 4 — API Service (Built for Scale From the Start)
- Build the FastAPI app **as async from the first line of code** — retrofitting async later is much harder than starting with it
- Wire in the feature module and model into `/score`
- Add the cache layer (in-process cache acceptable initially; Redis if time allows) per `TechSpec.md` Section 6.3
- Add connection pooling for the database from the start
- Add `GET /health` for load-balancer readiness checks
- Add pydantic input validation and the error states from `AppFlow.md`
- Begin `research/07_system_design.md` as statelessness, caching, and pooling are implemented
- **Deliverable:** a running API scoring transactions end-to-end within the 100ms target, at low load

## Phase 5 — Dashboard
- Build the Streamlit app with sidebar navigation matching `AppFlow.md`'s 8 pages (including System Health)
- Build panels incrementally: Model Performance → Threshold & Cost → Live Feed → Explainability → Drift Monitor → Business Impact → System Health
- On the Model Performance / System Health panels, surface the additional monitoring metrics: prediction distribution, average risk score, live fraud rate, and threshold drift over time (not just latency/throughput)
- Apply the visual rules from `Design.md`
- **Deliverable:** a working dashboard reflecting real system state, not static mock data

## Phase 6 — Drift Monitoring & Retraining Loop

**Gate check before starting this phase — confirm all of these are true:**
- [ ] Feature engineering complete (Phase 2)
- [ ] XGBoost modeling complete, including the imbalance comparison (Phase 3)
- [ ] SHAP explainability complete (Phase 3)
- [ ] API complete (Phase 4)

- Implement PSI calculation per feature, scheduled check
- Write `research/06_drift_detection.md` as this is built — the PSI math and the data-drift-vs-concept-drift distinction specifically
- Implement alerting (dashboard banner; optionally email/webhook)
- Implement the retraining job: retrain on accumulated feedback, validate against current model, only promote if genuinely better
- Log `feedback_rows_used` per run, per `schema.md`, to make the "accuracy improves through feedback volume" claim demonstrable, not asserted
- **Deliverable:** a full drift → retrain → validate → promote loop that runs end-to-end without manual intervention at least once

## Phase 7 — Testing
- Unit tests: feature engineering correctness, API request/response contracts
- Integration test: a synthetic transaction flowing through `/score` end-to-end
- **Deliverable:** a passing test suite runnable via a single command

## Phase 8 — Containerization & Horizontal Scaling Setup
- Write Dockerfiles for the API service and dashboard
- Configure docker-compose to run **multiple API replicas** behind a lightweight load balancer (e.g. nginx or Traefik) locally
- Confirm the stateless design (Section 6.2 of `TechSpec.md`) holds — no replica-specific state breaks correctness when requests are routed round-robin
- **Deliverable:** the API running as 3+ replicas locally, load-balanced, passing the same test suite as a single instance

## Phase 9 — Load Testing & Deployment (Where the 10K Claim Gets Proven)
- Write a Locust or k6 script that simulates concurrent users hitting `/score`
- Run the baseline test: 10 concurrent users, record p50/p95/p99 latency, store the result in `load_test_runs`
- Scale up the replica count and re-run at increasing concurrency (e.g. 100 → 1,000 → 10,000 simulated users), recording each result
- Identify and fix any bottleneck that appears (most likely candidates: cache misses, DB connection pool size, replica count) before re-testing
- Deploy to a cloud platform supporting horizontal scaling (Render/Railway with multiple instances, or AWS ECS/EC2 behind a load balancer)
- Set up GitHub Actions: run tests on push, build images, deploy on merge to main
- **Deliverable:** a publicly reachable URL, a System Health dashboard page showing the real load-test comparison chart, and a `load_test_runs` table full of real, citable numbers

## Phase 10 — Final Polish
- Run the synthetic generator continuously so the dashboard shows a "living" system with real history
- Write a README documenting: the architecture, the imbalance-handling comparison results, the cost-curve threshold decision with real numbers, **and the load-test results with the actual p99-at-10-users vs. p99-at-10,000-users comparison**
- Record a short demo video/GIF, including the System Health page, for portfolio use

## Documentation Completeness Checklist

Before considering the project "interview-ready," confirm every file below is filled in with real findings, not placeholders:

- [ ] `research/01_fraud_domain.md` through `07_system_design.md` — all interview-ready answers written in your own words
- [ ] `docs/feature_dictionary.md` — every feature actually used is documented with its real formula
- [ ] `docs/model_comparison.md` — pros/cons/why-selected filled in, "why not X" answers ready
- [ ] `docs/data_leakage.md` — checklist actually run against the real pipeline, findings logged
- [ ] `docs/error_analysis.md` — false positive/negative analysis done on real model output
- [ ] `docs/calibration_analysis.md` — calibration curve and Brier score computed on the real model
- [ ] `experiment_log.csv` — every real training run logged
- [ ] `Tracker.md` — phase progress, model evaluation log, retraining log, and load test log all current
