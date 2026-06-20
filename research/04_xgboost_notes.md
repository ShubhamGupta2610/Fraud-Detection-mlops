# 04 — XGBoost Notes

The goal here is to stop treating `xgboost.fit()` as a black box. If you can't explain how a single tree split happens, you don't understand the model yet — keep working this document until you can.

## Gradient boosting fundamentals
- [ ] In your own words: how does gradient boosting differ from bagging (e.g. Random Forest)? (Sequential, each tree corrects the previous ensemble's residual errors — vs. parallel, independent trees averaged together.)
- [ ] What is being "boosted" — what exactly does the next tree in the sequence try to fix?
- [ ] What is a "residual" in this context?

## Why XGBoost specifically (not plain gradient boosting, not LightGBM, not CatBoost)
- [ ] What does XGBoost add on top of vanilla gradient boosting? (Research: regularization terms in the objective, second-order gradient information, built-in handling of missing values, efficient split-finding.)
- [ ] What's the practical difference between XGBoost and LightGBM that would matter for this dataset size? (Research: histogram-based splitting, training speed on smaller tabular datasets — write your own honest assessment of whether it would have mattered here.)

## Key hyperparameters — explain what each one actually controls
- [ ] `max_depth` — what happens if this is too high? Too low?
- [ ] `learning_rate` (`eta`) — what's the trade-off with `n_estimators`?
- [ ] `scale_pos_weight` — already covered in `03_imbalance_learning.md`, cross-reference here
- [ ] `min_child_weight` and `gamma` — how do these act as regularization against overfitting on a small minority class?

## Why not Random Forest? (write this answer fully — interviewers ask this constantly)
- [ ] Your honest comparison: where would Random Forest have been roughly as good? Where would it likely underperform on this specific problem?

## Why not a neural network? (also commonly asked)
- [ ] Write your honest answer. (Likely points: tabular data with engineered features generally doesn't need deep learning's representation learning; gradient boosted trees are the established strong baseline for tabular fraud data; neural nets need more data and tuning to beat trees here; interpretability via SHAP is more mature/stable for tree models.)

## Interview-ready answers

**Q: Why XGBoost over Random Forest?**
> Your answer here — cross-reference `model_comparison.md`.

**Q: Why not deep learning for this?**
> Your answer here.

**Q: What hyperparameters mattered most for your results, and why?**
> Your answer here, backed by `experiment_log.csv`.
