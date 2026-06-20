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

- [ ] Break down recall specifically by fraud subtype (not just overall recall). A model can have decent overall recall while completely missing one entire fraud category — this breakdown is what reveals that.

| Fraud Type | Recall | Notes |
|---|---|---|
| Card testing | | |
| Account takeover | | |
| Impossible travel | | |
| Other / unlabeled novel pattern | | (This is where Isolation Forest's contribution matters — cross-reference how many of these it caught that XGBoost alone missed) |

## 4. Where Isolation Forest added value beyond XGBoost

- [ ] Find at least one example where Isolation Forest flagged something XGBoost scored as low-risk. What made it anomalous? Does this look like a genuinely novel fraud pattern, or noise?

## 5. What you'd do next if you kept improving this model

- [ ] Based on the patterns found above, what's your top suggested next step? (e.g. "add a feature for X because false negatives cluster around accounts missing that signal")

## Interview-ready answers

**Q: Walk me through your model's errors — where does it fail?**
> Your answer here, using the findings above.

**Q: Which type of fraud was hardest to catch, and why?**
> Your answer here.

**Q: If you had another month to improve this model, what would you do first?**
> Your answer here — should come directly from Section 5 above.
