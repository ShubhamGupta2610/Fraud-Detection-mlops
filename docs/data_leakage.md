# Data Leakage Notes

Data leakage is one of the most common ML interview topics, and one of the easiest ways to accidentally produce a model that looks great offline and fails completely in production. This document exists to force you to actively check for it, not just know the definition.

## What data leakage actually is

Leakage happens when information that wouldn't be available at real prediction time accidentally makes it into training — causing the model to "cheat" by learning a shortcut that won't exist in production.

## Specific leakage risks in THIS project — check each one explicitly

### 1. Label leakage via the outcome itself
- [ ] Does any feature directly or indirectly encode the chargeback/fraud label? Example of the bug: including a `chargeback_filed` flag as an input feature when that flag is only ever set *after* the fraud determination is already known — the model would learn to just read the label back to itself.
- [ ] Check: for every feature in `feature_dictionary.md`, could you have computed this value at the actual moment the transaction needed to be scored — before any human or system confirmed fraud or not? If no, it's leakage.

### 2. Temporal leakage — using future information
- [ ] Are any rolling-window features (`txn_count_24h`, etc.) accidentally computed using transactions that happened *after* the transaction being scored? This is easy to introduce by accident with a careless groupby/window function that doesn't respect chronological order.
- [ ] Did your train/test split respect time order, or did you randomly shuffle? For a fraud system, a random split can leak future patterns into training in a way a real production system would never have access to — a time-based split (train on earlier data, test on later data) is more honest.

### 3. SMOTE-before-split leakage
- [ ] Cross-reference `research/03_imbalance_learning.md`: did you apply SMOTE before or after the train/test split? Applying it before causes synthetic points derived from test-set examples to leak into training, inflating your test performance artificially. Confirm and document your actual order here.

### 4. Feature scaling leakage
- [ ] If any feature was scaled/normalized (less relevant for tree-based XGBoost, but check if you used logistic regression too), was the scaler fit only on the training set, or accidentally fit on the full dataset including test data?

### 5. Account-level leakage across train/test split
- [ ] Could the same account appear in both the training set and the test set? If so, the model may be learning account-specific quirks rather than generalizable fraud patterns, and your test performance will look better than it would on a genuinely new account.

## How to actively test for leakage (don't just reason about it — check)

- [ ] Pick one feature you're most suspicious of. Manually trace through your code: at the exact moment a real transaction would need to be scored in production, is this feature's value actually computable from only past data?
- [ ] If your model's offline PR-AUC seems suspiciously high compared to realistic published fraud-detection benchmarks, that's a signal to actively hunt for leakage before celebrating the number.

## Findings Log

Document anything you actually find and fix here — a documented leakage bug you caught and fixed is a strong interview story.

| Date | Leakage Found | How It Was Introduced | Fix Applied | Impact on PR-AUC (before/after fix) |
|---|---|---|---|---|
| | | | | |

## Interview-ready answers

**Q: What is data leakage and how do you check for it?**
> Your answer here.

**Q: Did you find any leakage in this project?**
> Your answer here — either a real finding from the table above, or an honest "I checked X, Y, Z specifically and didn't find any, here's how I verified that."
