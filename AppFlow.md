# AppFlow.md: Adaptive Fraud & Risk Scoring Engine

This system has no consumer-facing screens in the traditional sense — its primary "users" interact with it via an API (machine-to-machine, expected to handle up to 10,000 concurrent callers) and via the dashboard (human-to-system). Both flows are specified below.

## 1. All Screens / Pages (Dashboard)

| Page | Purpose |
|---|---|
| Overview | Live transaction count, current fraud rate, alert banner if drift detected |
| Model Performance | Precision-recall curve, confusion matrix, calibration plot |
| Threshold & Cost | Interactive slider; live recompute of precision/recall/total cost |
| Drift Monitor | Feature distribution charts over time; PSI per feature; alert history |
| Business Impact | $ fraud caught, $ fraud missed, customers wrongly blocked, by time window |
| Explainability | Global SHAP summary; searchable per-transaction explanation view |
| Live Transaction Feed | Scrolling table of recent transactions, color-coded by decision |
| **System Health** *(new)* | Current replica count, p99 latency (live), requests/sec, load-test history chart |

The System Health page is the dashboard surface for the scale claim in `PRD.md` Section 5 — it shows live latency and throughput, not just a one-time load-test screenshot, so the "responsive at 10K users" claim has an ongoing, checkable home in the product itself.

## 2. Navigation Flow

Sidebar navigation (Streamlit native multi-page or `st.sidebar`). Overview is the default landing page; all other pages reachable at any time, no forced sequence.

## 3. Machine-to-Machine Flow (the /score API)

1. Caller (synthetic generator, load-test tool, or a future real integration) sends a transaction payload to `POST /score`
2. Load balancer routes the request to an available, healthy API replica (per `TechSpec.md` Section 6.5)
3. Replica checks the cache for the account's recent history; computes real-time features (velocity, geo-velocity, behavioral deviation)
4. Model returns a risk score (0–100) and SHAP-based top contributing features
5. Decision engine applies the current threshold: allow / challenge / block
6. Transaction + score + decision is logged to the database (via the pooled connection)
7. Response returned to caller — target: under 100ms, **whether this is the 10th or the 10,000th concurrent request**

## 4. Button Actions / Interactive Elements (Dashboard)

| Element | Action |
|---|---|
| Threshold slider | Recomputes precision, recall, and total cost live; doesn't change production threshold until "Apply" is clicked |
| "Apply Threshold" button | Updates the decision engine's active threshold |
| "Trigger Retrain Now" button | Calls `POST /retrain`; shows progress; on completion, shows old vs. new model metrics side by side before requiring manual confirmation to promote |
| Transaction row click (Live Feed) | Opens the per-transaction SHAP explanation |
| Time window selector (Business Impact) | Re-filters charts to the selected range (24h / 7d / 30d) |
| "Run Load Test" button (System Health) | Triggers a Locust/k6 run against the deployed API and displays the resulting latency chart |

## 5. Empty States

- No transactions yet: "No transactions scored yet. Start the transaction generator to see live data."
- No drift detected yet: calm "All features within normal range" state
- No retraining run yet: "No retraining runs yet — trigger one manually or wait for the scheduled run."
- No load test run yet: "No load test data yet — run a test to see latency at scale."

## 6. Error States

- Malformed transaction payload → HTTP 422 with a clear validation message, never a silent failure
- Model file missing/corrupted on startup → service fails to start with a clear log message
- Retraining fails validation (new model worse than current) → logged as failed, current model stays live, dashboard shows "retraining attempted, not promoted"
- Database unreachable → `/score` still returns a score (degrades gracefully) but logs a warning that the transaction wasn't persisted
- A replica becomes unhealthy under load → load balancer's health check (`GET /health`) routes traffic away from it automatically; this is itself a demonstrable resilience behavior worth showing in a demo

## 7. Success States

- Successful scoring → score + decision + explanation returned; transaction appears in the Live Feed within the dashboard's refresh interval
- Successful retraining + promotion → dashboard banner: "Model retrained and promoted at [time] — PR-AUC improved from X to Y"
- Successful load test → System Health page shows the before/after latency comparison chart described in `TechSpec.md` Section 6.8

## 8. Login / Signup Flow

None in v1 (single-user, no auth). v2 design intent: email+password or magic link, gated behind a `role` check per `schema.md`.

## 9. Payment / Upgrade Flow

Not applicable — internal tool, not a monetized product.
