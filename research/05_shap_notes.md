# 05 — SHAP Notes

## What SHAP actually computes
- [ ] In your own words: what is a "Shapley value" conceptually, and where does the idea come from? (Research: cooperative game theory — fairly distributing a "payout" among players based on their contribution.)
- [ ] What does a SHAP value for a single feature on a single prediction actually represent? (How much that feature's value pushed the prediction away from the average/baseline prediction.)
- [ ] What's the difference between a global SHAP summary (feature importance across all predictions) and a local SHAP explanation (why this one transaction got this one score)? Why do you need both on the dashboard?

## Why TreeExplainer specifically
- [ ] Why is SHAP computation for tree-based models (TreeExplainer) much faster than the general-purpose KernelExplainer? (Research: it exploits the tree structure directly rather than treating the model as a black box.)

## Practical SHAP gotchas
- [ ] What happens to SHAP explanations when two features are highly correlated? Does the "credit" get split between them in a way that might mislead someone reading the explanation?
- [ ] How did you decide how many top features to show in a per-transaction explanation (e.g. top 3 vs. top 10)? What's the UX trade-off?

## Why explainability matters here beyond "it's nice to have"
- [ ] Write the compliance argument in your own words: why might a regulator or auditor specifically require a reason for an automated decline?
- [ ] Write the debugging argument: how did SHAP help you catch anything wrong with your model or features during development? (Fill this in once you actually use it — this becomes a real interview story.)

## Interview-ready answers

**Q: How does SHAP work, conceptually?**
> Your answer here.

**Q: Why did you choose SHAP over other explainability methods (e.g. LIME)?**
> Your answer here. (Research LIME briefly so you have a real comparison, not just "SHAP is popular.")

**Q: Give an example of a SHAP explanation catching something unexpected in your model.**
> Fill this in from real experience once you've built it.
