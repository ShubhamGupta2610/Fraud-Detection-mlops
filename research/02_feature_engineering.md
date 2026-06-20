# 02 — Feature Engineering Notes

## Core concept to understand deeply: sliding windows on a live stream

- [ ] Explain in your own words why "transactions in the last hour" is fundamentally harder to compute than a column that already exists in a static CSV.
- [ ] What data structure would you use to maintain a rolling window efficiently per-account, without recomputing from full history on every request? (research: deque, time-bucketed counters)
- [ ] What happens to a sliding-window feature the first time you ever see a brand-new account? How should "cold start" be handled — zero, null, or a population-average default? Write down your decision and why.

## Velocity features
- [ ] Why does velocity (transactions per unit time) tend to spike for card-testing fraud specifically?
- [ ] What window lengths did you choose (1 min / 1 hr / 24 hr) and why those specific lengths rather than others?

## Geo-velocity
- [ ] Write out the actual formula you used: distance between two points ÷ time between two transactions = implied speed.
- [ ] What's the threshold you used for "impossible travel," and how did you justify that number (e.g. commercial flight speed ceiling)?
- [ ] What's a legitimate (non-fraud) scenario that could trigger a false positive on this feature? (e.g. shared family card, VPN)

## Behavioral deviation features
- [ ] How did you define an account's "baseline" (average amount, typical time-of-day)? Over what time window?
- [ ] What happens to this feature for an account with very little history? Same cold-start question as above, but specific to behavioral baselines.

## Feature scaling / preprocessing
- [ ] Did your chosen model (XGBoost) actually require feature scaling? Why or why not? (Tree-based models vs. linear/distance-based models — write the difference in your own words.)

## Interview-ready answers

**Q: Walk me through how you computed a real-time feature like "transactions in the last hour."**
> Your answer here.

**Q: Why did you choose these specific window lengths?**
> Your answer here.

**Q: What's a feature you considered but didn't include, and why?**
> Your answer here.
