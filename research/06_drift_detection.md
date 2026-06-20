# 06 — Drift Detection Notes

**Reminder per the scope warning: do not start this section's implementation until Feature Engineering, XGBoost modeling, SHAP, and the API are all complete.** Reading and taking notes here early is fine — building the drift monitor early is the distraction to avoid.

## What "drift" actually means — there are two kinds, know the difference
- [ ] **Data drift / feature drift**: the distribution of input features changes over time, independent of the model. Write an example specific to fraud (e.g. average transaction amount rises due to inflation or a new merchant category, unrelated to fraud behavior).
- [ ] **Concept drift**: the relationship between features and the target changes — the same feature values now mean something different. Write a fraud-specific example (e.g. a feature that used to strongly indicate fraud, like "new device," becomes common for legitimate reasons after a product change, like a new app login flow).
- [ ] Why does this project's PSI monitor catch feature drift directly, but only catch concept drift indirectly (via declining model performance on feedback)?

## Population Stability Index (PSI) — understand the actual math
- [ ] Write out the PSI formula in your own words: it compares the distribution of a feature in a "baseline" period vs. a "current" period, bucketed, and sums a weighted log-ratio across buckets.
- [ ] What do the commonly-used PSI thresholds mean? (Research: <0.1 = no significant change, 0.1–0.25 = moderate shift worth watching, >0.25 = significant shift.) Write down which threshold you used and why.
- [ ] Why is bucketing (binning) necessary for PSI, and what happens if your bins are too coarse or too fine?

## Alternatives to PSI (know they exist, even if you didn't use them)
- [ ] KL divergence — how does it relate to PSI? (PSI is a symmetrized, scaled variant in the same family.)
- [ ] Kolmogorov-Smirnov test — when might this be preferred over PSI?

## The retraining trigger logic
- [ ] What exactly triggers a retrain in your system — a single feature crossing the alert threshold, or a combination? Write your actual logic.
- [ ] Why does the new model get validated against the current model before promotion, rather than being promoted automatically? What could go wrong without that gate?

## Interview-ready answers

**Q: How do you detect when a model is going stale in production?**
> Your answer here.

**Q: What's the difference between data drift and concept drift?**
> Your answer here.

**Q: Why not just retrain on a fixed schedule and skip drift detection entirely?**
> Your answer here. (Hint: cost of unnecessary retraining vs. risk of missing a sudden shift between scheduled runs.)
