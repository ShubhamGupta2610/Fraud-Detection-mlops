# Rules.md: Adaptive Fraud & Risk Scoring Engine

Operating rules for any AI coding agent (Claude Code, Cursor, etc.) working on this project. Read this alongside `PRD.md`, `TechSpec.md`, `AppFlow.md`, `Design.md`, `schema.md`, and `ImplementationPlan.md`.

## 1. Don't Build Out of Order

Follow `ImplementationPlan.md`'s phase order. Do not implement Phase 6 (drift/retraining) before Phase 3 (modeling) is solid, and do not attempt Phase 9 (load testing) before Phase 4's API is built async and statelessly from the start — retrofitting async or statelessness later is significantly more work than building it in from Phase 4.

## 2. Never Conflate the Two Scale/Accuracy Claims

This is the single most important rule in this document. The project's headline claim is:

> "The system is designed to scale to 10,000+ users while maintaining low-latency inference. Model performance improves over time through a feedback loop, drift monitoring, and scheduled retraining using newly collected labeled data."

These are **two separate claims with two separate proofs**:
- Latency-at-scale → proven by load test numbers in `Tracker.md` Section 4
- Accuracy-over-time → proven by retraining run numbers in `Tracker.md` Section 3

**Never write code, comments, docs, or dashboard copy that implies traffic volume directly causes accuracy improvement.** If asked to "make the model more accurate as users increase," implement this correctly as: more users → more transactions → more eventual feedback → more retraining data → retraining loop improves accuracy. Do not implement or describe any mechanism where request volume itself changes model weights or accuracy outside of that feedback loop.

## 3. No Claim Without a Number

Don't write "the system scales well" or "latency stays low" in any README, dashboard copy, or comment without a corresponding logged number in `Tracker.md`. If a load test hasn't been run yet, say so explicitly ("designed for, not yet load-tested") rather than implying it's already proven.

## 4. Synthetic Data Only

Never integrate real payment processor APIs, real customer PII, or real financial accounts. All transaction data is either the public Kaggle benchmark dataset or the synthetic generator built in Phase 1. This is a portfolio/learning system, not a system handling real financial risk.

## 5. Accuracy Metrics — Never Default to Plain Accuracy

Given the class imbalance described in `PRD.md`, never evaluate or report model quality using plain accuracy as the primary metric. Use precision, recall, PR-AUC, and the cost curve (per `TechSpec.md`). If a generated evaluation script defaults to `accuracy_score` as its headline metric, that's a bug, not a style choice.

## 6. Stateless API, Always

No request-handling code should store per-request or per-replica state outside of the shared cache/database (`TechSpec.md` Section 6.2–6.3). Any in-memory dict that accumulates per-request data inside the FastAPI app itself (outside the designated cache layer) breaks horizontal scaling and should be flagged, not implemented.

## 7. Every Threshold Decision Is a Business Decision

Never hardcode a 0.5 classification threshold as the final decision boundary. The threshold must come from the cost-curve calculation (`TechSpec.md`, `PRD.md` Section 5) and must be adjustable via the dashboard, not buried as a constant in code.

## 8. Explainability Is Not Optional

Every `/score` response must include a SHAP-based explanation. If a code change to the scoring pipeline would skip SHAP computation "for speed," that tradeoff must be surfaced explicitly and logged in `Tracker.md` Section 5 — not silently dropped, since explainability is a stated MVP requirement, not a nice-to-have.

## 9. Out-of-Scope Items Stay Out of Scope

Do not implement multi-user auth, real payment integrations, Kubernetes, A/B testing infrastructure, or a full model registry unless `PRD.md` Section 4 is explicitly updated to move them into scope. If asked to add one of these mid-build, flag that it contradicts the current PRD before proceeding.

## 10. Keep Tracker.md Current

After completing any phase from `ImplementationPlan.md`, or after any load test or retraining run, update the relevant table in `Tracker.md` with real dates and real numbers. An agent should treat an out-of-date `Tracker.md` as a sign that documentation work was skipped, not optional polish.

## 11. No Model Decision Without a Written Justification

Every model choice (XGBoost over Random Forest, SHAP over LIME, isotonic regression over Platt scaling, etc.) must have a corresponding entry in `docs/model_comparison.md` or the relevant `research/` file before being treated as final. "It worked" is not a justification — the comparison and reasoning must be written down.

## 12. Run the Data Leakage Checklist Before Calling Modeling Done

Phase 3 of `ImplementationPlan.md` is not complete until `docs/data_leakage.md`'s checklist has been actively run against the real feature set and train/test split — not just read. Pay special attention to: SMOTE applied before vs. after the split, time-respecting train/test splits, and no future-looking data in any rolling-window feature.

## 13. Don't Report a Metric Without Error Analysis

A PR-AUC or precision/recall number alone is not a complete deliverable for Phase 3. `docs/error_analysis.md` (false positive patterns, false negative patterns, recall by fraud type) must be filled in with real findings before modeling is considered finished.

## 14. Don't Treat the Raw Model Score as a Calibrated Probability

Unless `docs/calibration_analysis.md` has been completed and shows the raw output is already well-calibrated (check the Brier score and calibration curve), assume XGBoost's raw output needs calibration (Platt scaling or isotonic regression) before it's used in any cost-curve or dollar-impact calculation in `TechSpec.md` Section 5.4 or the Business Impact dashboard panel.

## 15. Drift Detection Is Gated, Not Optional to Skip Forward To

Per `ImplementationPlan.md` Phase 6's gate check, do not implement any part of the drift monitor or retraining loop until feature engineering, XGBoost modeling, SHAP, and the API are all complete and their corresponding research/docs files are filled in. If asked to jump ahead to drift detection early, flag the gate check before proceeding.

## 16. Research Notes Are Written By the Builder, Not Auto-Generated

If asked to "fill in" the `research/` files' interview-ready answers, do not simply generate plausible-sounding answers and call the file complete — these are meant to reflect what the person actually learned and decided while building. An AI agent can help draft a first pass or check technical accuracy, but the project owner should review and personalize every answer before treating it as interview-ready.

## 17. Security Rules Are Non-Negotiable, Not Phase-Dependent

`Security.md` is not a Phase 10 polish item. Specific rules from it apply from Phase 0 onward regardless of how early-stage the code is:
- No secret, key, or credential is ever hardcoded or committed to git, starting with the very first commit — not "added before deployment."
- Every new API endpoint gets pydantic input validation in the same commit that creates it, not as a follow-up.
- Any database query written anywhere in the codebase uses the ORM / parameterized queries — never raw string-interpolated SQL, even temporarily "to test something quickly."
- Before Phase 9's public deployment, the full "Security Checklist Before Any Deployment" in `Security.md` must be run and confirmed, not assumed.

If asked to write code that would violate any of these (e.g. "just hardcode the key for now, I'll fix it later"), flag the conflict with `Security.md` before proceeding rather than complying silently.
