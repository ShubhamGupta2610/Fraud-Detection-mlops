# 03 — Imbalanced Learning Notes

This is the conceptual core of the whole project. Spend real time here.

## Why accuracy lies
- [ ] Compute, by hand, on paper: if fraud is 0.5% of transactions and a model predicts "legitimate" for everything, what's its accuracy? Write the number. This is the example you'll use in interviews.

## The three techniques you compared — understand each, don't just run each

### Class weighting (`scale_pos_weight` in XGBoost)
- [ ] What does this parameter actually do to the loss function during training? (Research: it multiplies the loss contribution of the minority class.)
- [ ] What value did you set it to, and how did you derive that number (commonly: ratio of negative to positive class counts)?
- [ ] What's the failure mode if you set it too high?

### SMOTE (Synthetic Minority Oversampling)
- [ ] Explain in your own words how SMOTE generates new minority-class examples (interpolating between real minority points — not just duplicating them).
- [ ] What's the actual risk with SMOTE on fraud data specifically? (Research: it can generate synthetic points that don't correspond to any real fraud pattern, especially in high-dimensional feature space — "smearing" the decision boundary.)
- [ ] Did you apply SMOTE before or after your train/test split? Why does this order matter enormously? (This is a classic interview trap — SMOTE before splitting causes data leakage, see `docs/data_leakage.md`.)

### Threshold tuning
- [ ] Why does moving the decision threshold not require retraining the model at all — what's actually changing?
- [ ] How does this connect to the cost curve in `TechSpec.md`?

## Which one did you end up using, and why
- [ ] Write your actual decision and the evidence (PR-AUC, precision/recall at a fixed threshold) that justified it. Don't write "I tried all three" — write "I chose X because Y, supported by Z numbers in experiment_log.csv."

## Interview-ready answers

**Q: How would you handle a dataset where the positive class is 0.5% of the data?**
> Your answer here.

**Q: What's wrong with using SMOTE carelessly?**
> Your answer here.

**Q: Why not just use accuracy as your metric?**
> Your answer here.
