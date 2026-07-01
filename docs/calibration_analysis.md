# Calibration Analysis

A risk score is only meaningful if it's calibrated. "Risk score = 80" should mean roughly an 80% chance of fraud among all transactions that get that score — if it doesn't, the number is just a ranking, not a probability, and using it for cost-curve math (TechSpec.md Section 5.4 / "Threshold & Cost" dashboard panel) would be misleading.

## 1. Is your raw model output already calibrated?

- [ ] Research: why are tree-based models like XGBoost often poorly calibrated by default, even when their *ranking* (which transactions are riskier than others) is good? (Hint: the loss function optimizes ranking/separation, not probability accuracy.)
- [ ] Plot a calibration curve (also called a reliability diagram): bucket predictions by predicted probability, compare each bucket's average predicted probability to its actual observed fraud rate. Is your raw XGBoost output close to the diagonal, or systematically off?

## 2. Calibration techniques — understand both before picking one

### Platt Scaling
- [ ] What does this technique do? (Fits a logistic regression on top of the model's raw output scores to map them to calibrated probabilities.)
- [ ] When does Platt scaling work well? (Research: when the miscalibration is roughly sigmoid-shaped.)

### Isotonic Regression
- [ ] What does this technique do differently from Platt scaling? (Fits a non-parametric, monotonic step function instead of assuming a sigmoid shape.)
- [ ] When would you prefer isotonic regression over Platt scaling? (Research: more flexible, but needs more data to avoid overfitting the calibration mapping itself.)

## 3. Brier Score

- [ ] What does the Brier score measure? (Mean squared error between predicted probabilities and actual binary outcomes — lower is better.)
- [ ] Compute it for your raw model and your calibrated model. Did calibration actually improve it?

| Model Version | Brier Score | Notes |
|---|---|---|
| Raw XGBoost output | 0.000863 | Measured on the real time-based test set (class-weighted XGBoost) |
| After Platt scaling | (not run — isotonic chosen directly, see reasoning below) | |
| After isotonic regression | 0.000671 | A ~22% reduction vs. raw — calibration genuinely helped |

**Implementation note worth knowing:** scikit-learn 1.6+ removed `CalibratedClassifierCV`'s `cv="prefit"` option, replacing it with wrapping the already-fitted model in `sklearn.frozen.FrozenEstimator` first. This was discovered by actually running the code, not by reading documentation in isolation — a good example of why "I read the docs" and "I ran it" are different levels of verification.

**Calibration curve finding:** with only 5 quantile bins (reduced from a default of 10 — 10 bins mostly collapsed to `predicted=0.0000, actual=0.0000` given how extreme the class imbalance is), the raw model's largest bin showed predicted=0.0497 vs actual=0.0389 (gap of 0.0108) — reasonably close, but not perfect. After isotonic calibration, the curve collapsed to just 2 distinct bins (predicted≈0.0000/actual≈0.0004, and predicted≈0.9947/actual≈0.9617) — a known behavior of isotonic regression's step-function nature on a small positive-class count, not a bug.

## 4. Which calibration method did you choose, and why

**Isotonic regression**, fit on a held-out 20% slice of the *training* set (never the test set, to avoid leaking test information into the calibration step itself — the same leakage principle from `docs/data_leakage.md` applied specifically to calibration). Chosen over Platt scaling because the training set is large enough (326,629 rows, 625 positive) that isotonic's higher data requirement isn't a practical concern, and isotonic doesn't assume the miscalibration is sigmoid-shaped — a more flexible, fewer-assumptions choice given we had the data to support it.

## 5. Why this matters for the cost curve specifically

- [ ] Write the connection explicitly: the cost-curve threshold optimization (TechSpec.md 5.4) assumes the risk score behaves like a real probability when multiplying by cost figures. If the score isn't calibrated, the "optimal" threshold computed from it could be wrong — explain why in your own words.

## Interview-ready answers

**Q: Is your model's output score actually a calibrated probability?**
> Your answer here, backed by the calibration curve and Brier score above.

**Q: Why do tree-based models often need separate calibration?**
> Your answer here.

**Q: How does calibration affect your threshold/cost decision?**
> Your answer here.
