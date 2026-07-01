# Error Analysis Report

A PR-AUC number alone doesn't tell a story. This document is where you dig into *which* transactions the model got wrong and why — this is the part interviewers consistently find most impressive, because it shows judgment beyond running a metric.

## 1. False Positives Analysis (legitimate transactions wrongly flagged)

- [ ] Pull the top 20 highest-confidence false positives from your validation/test set.
- [ ] For each, look at the SHAP explanation — what feature(s) drove the score up?
- [ ] Look for a pattern across them. Common real-world patterns to check for:
  - Are they clustered around a specific merchant category?
  - Are they clustered around new-but-legitimate accounts (cold-start effect)?
  - Are they clustered around legitimate behavior that resembles a fraud pattern (e.g. genuine travel triggering geo-velocity)?
- [ ] Write your finding:

> False positives in this model tend to be: ___

## 2. False Negatives Analysis (fraud the model missed)

- [ ] Pull the false negatives — fraud cases the model scored as low-risk.
- [ ] For each, check the SHAP explanation — was there a weak signal the model underweighted, or no signal at all?
- [ ] Group by fraud type if your synthetic generator labels fraud type (card testing / account takeover / impossible travel / other). Which type is hardest for the model to catch?
- [ ] Write your finding:

> The model struggles most with: ___ fraud, likely because: ___

## 3. Which fraud type is hardest, and why

| Fraud Type | Recall | Notes |
|---|---|---|
| Card testing | 93.97% (483/514 caught, 31 missed) | **Hardest of the three.** Missed cases show a clear pattern (see Section 2 findings below): the fraudster reused a device/location already known for that account, which removed the `is_new_device`/`is_new_ip_or_location` signal the model relies on most heavily — only the velocity signal (`txn_count_1h`) remained, and the model weighted "known device" as strong evidence of legitimacy strongly enough to occasionally override it. |
| Account takeover | 96.39% (80/83 caught) | Strong recall — the device + amount-deviation combination is a reliable signal in nearly all cases. |
| Impossible travel | 100% (37/37 caught) | **Perfect recall.** `geo_velocity` produces an unambiguous, extreme signal whenever this pattern fires — there is essentially no borderline case for this fraud type as currently generated. |
| Other / unlabeled novel pattern | n/a — Isolation Forest's contribution | Isolation Forest caught 3 of XGBoost's 34 total false negatives (8.8%) — see Section 4. |

## 4. Where Isolation Forest added value beyond XGBoost

**Measured, not hypothetical:** of XGBoost's 34 false negatives at the default threshold, Isolation Forest's top 1% riskiest anomaly scores caught 3 of them (8.8%). This is a real but modest contribution — on this dataset, fraud patterns are well-separated enough that XGBoost (trained directly on the labels) rarely misses, leaving less room for an unsupervised model to add value than it might on a noisier, less cleanly-separable real-world dataset. The honest takeaway: Isolation Forest's value here is real but small, and its theoretical advantage (catching genuinely novel, unlabeled patterns) is harder to demonstrate convincingly when the labeled patterns are this learnable in the first place.

## 5. What you'd do next if you kept improving this model

Based on the false-negative pattern found in Section 2/3 (card-testing fraud that reuses a known device evades the model more often), the most promising next feature would be one that captures velocity-on-a-known-device more sharply — e.g. a feature specifically flagging a sudden spike in transaction frequency even when the device is recognized, rather than relying on `is_new_device` to carry most of the signal. This is a concrete, evidence-backed next step, not a generic "collect more data" answer.

## Interview-ready answers

**Q: Walk me through your model's errors — where does it fail?**
> Your answer here, using the findings above.

**Q: Which type of fraud was hardest to catch, and why?**
> Your answer here.

**Q: If you had another month to improve this model, what would you do first?**
> Your answer here — should come directly from Section 5 above.
