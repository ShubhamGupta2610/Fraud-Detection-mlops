# 07 — System Design Notes

This is where the infrastructure half of the project (TechSpec.md Section 6) gets turned into understanding, not just working code.

## Statelessness
- [ ] In your own words: why does a stateless API make horizontal scaling possible? What would break if the API stored per-request state in a local variable that needed to persist across requests?

## Caching
- [ ] What specifically gets cached in this system, and why does that prevent the database from becoming a bottleneck?
- [ ] What's a cache invalidation problem you'd need to think about here? (e.g. an account's rolling-window data needs to update as new transactions arrive — how do you keep the cache from going stale?)

## Connection pooling
- [ ] Why is opening a new database connection per request expensive? What does a connection pool actually do to avoid that cost?
- [ ] What happens if the pool size is too small under high concurrency? Too large?

## Load balancing
- [ ] What does a load balancer's health check actually verify, and why does `GET /health` exist specifically for this?
- [ ] What load-balancing strategy did you use or assume (round robin, least connections)? Would it matter much at this scale?

## Async I/O
- [ ] In your own words: what's the difference between a synchronous server handling one request per thread, and an async server handling many requests concurrently on fewer threads? Why does this matter for a service that's I/O-bound (waiting on database/cache calls) rather than CPU-bound?
- [ ] Is the XGBoost prediction step itself CPU-bound or I/O-bound? Does that change how you'd think about scaling it specifically? (Cross-reference TechSpec.md 6.7.)

## What you actually measured
- [ ] Once load testing is done (Phase 9), fill in: what was the real bottleneck that appeared first as concurrency increased? Was it what you expected?

## Interview-ready answers

**Q: Walk me through how your system stays fast as concurrent users increase.**
> Your answer here — this should be a clear, ordered explanation: stateless replicas, load balancer, cache, connection pool, async I/O. Practice saying this out loud.

**Q: What was the actual bottleneck when you load-tested this?**
> Your answer here, from `Tracker.md` Section 5 (Known Bottlenecks & Fixes).

**Q: How would this design change if you needed to support 1,000,000 users instead of 10,000?**
> Your answer here — this is a good place to mention the v2 upgrades already listed in earlier docs (Kafka, Redis at scale, Kubernetes) and *why* each becomes necessary at that point and not before.
