# 01 — Fraud Domain Notes

Fill this in as you learn, in your own words. The goal isn't to copy definitions — it's that when an interviewer asks "why does fraud detection need a different approach than normal classification," you answer from understanding, not memory.

## What I need to understand before modeling anything

### Why fraud is rare and what that does to a model
- [ ] What does "base rate" mean and why does a <1% fraud rate break naive accuracy as a metric?
- [ ] Write your own one-paragraph explanation of why a model that predicts "never fraud" can look 99%+ accurate and still be useless.

### Common real-world fraud patterns (research each, write a plain-English summary)
- [ ] **Card testing** — what is it, why does it produce a recognizable pattern, what features would catch it?
- [ ] **Account takeover** — what changes in behavior when an account is taken over? (device, location, spending pattern)
- [ ] **Impossible travel** — what's the actual math behind detecting it? (distance / time vs. plausible travel speed)
- [ ] **Friendly fraud / chargeback fraud** — why is this one of the hardest fraud types to catch with behavioral features alone?
- [ ] **Synthetic identity fraud** — why doesn't this look like "anomalous" behavior at all, and why is it a known weak spot for behavior-based models?

### The business trade-off
- [ ] In your own words: why is a false positive (blocking a real customer) sometimes more costly to a business than a false negative (missing fraud)? Give a concrete dollar-cost example using made-up but realistic numbers.
- [ ] Why can't this trade-off be solved with a single "best" model — why is it fundamentally a threshold/business decision, not a pure ML problem?

### Regulatory/compliance angle
- [ ] Why do compliance teams require explanations for declined transactions? What regulation or principle is this tied to (research: adverse action notices, fair lending principles as an analogy)?

## Interview-ready answers (write these last, after the above)

**Q: Why is fraud detection harder than a typical classification problem?**
> Your answer here, in your own words.

**Q: What's the single biggest mistake people make when first building a fraud model?**
> Your answer here.
