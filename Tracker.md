# Tracker.md: Adaptive Fraud & Risk Scoring Engine

This file has two jobs: track build progress phase-by-phase, and serve as the running evidence log for every claim made about this project (especially the scale and accuracy claims in `PRD.md` Section 5). Update it as you go — don't reconstruct it retroactively before an interview, since the whole point is that the numbers are real and dated.

## 1. Phase Progress

| Phase | Status | Date Completed | Notes |
|---|---|---|---|
| 0 — Setup | Complete | 2026-06-20 | FastAPI skeleton, all 6 schema.md tables, /health confirms DB connectivity. Verified end-to-end against a local DB. |
| 1 — Data Foundations | Complete | 2026-06-21 | Synthetic generator built: account population + legitimate history + 3 fraud patterns (card_testing, account_takeover, impossible_travel). Two real bugs found and fixed during verification — see Known Bottlenecks & Fixes below. 7 regression tests passing. |
| 2 — Feature Engineering | Complete | 2026-06-22 | Velocity, geo-velocity, behavioral deviation, and device features built in `pipeline/features/`. Strict point-in-time boundary enforced and tested. Full `docs/data_leakage.md` checklist run — no leakage found. 16 new tests passing (23 total across Phases 1-2). `haversine_km` promoted to a shared module so Phase 1's generator and Phase 2's detector can't drift apart. |
| 3 — Modeling | Not started | | |
| 4 — API Service | Not started | | |
| 5 — Dashboard | Not started | | |
| 6 — Drift & Retraining Loop | Not started | | |
| 7 — Testing | Not started | | |
| 8 — Containerization & Scaling Setup | Not started | | |
| 9 — Load Testing & Deployment | Not started | | |
| 10 — Final Polish | Not started | | |

## 2. Model Evaluation Log

Record every training run here, not just the final one — the progression itself is part of the story.

| Date | Model | PR-AUC | Precision @ chosen threshold | Recall @ chosen threshold | Notes |
|---|---|---|---|---|---|
| | Logistic Regression (baseline) | | | | |
| | XGBoost (class weighting) | | | | |
| | XGBoost (SMOTE) | | | | |
| | XGBoost (final, chosen approach) | | | | Document why this approach won |

## 3. Retraining Run Log

This is the evidence for the "model performance improves over time through the feedback loop" half of the scale/accuracy claim.

| Date | Trigger (scheduled/drift/manual) | Feedback rows used | Old PR-AUC | New PR-AUC | Promoted? |
|---|---|---|---|---|---|
| | | | | | |

## 4. Load Test Log

This is the evidence for the "responsive at 10,000 users" half of the claim. Every number quoted in an interview should be traceable to a row here.

| Date | Concurrent Users | Replica Count | p50 (ms) | p95 (ms) | p99 (ms) | Error Rate | Notes |
|---|---|---|---|---|---|---|---|
| | 10 (baseline) | | | | | | |
| | 1,000 | | | | | | |
| | 10,000 | | | | | | |

**Interview-ready summary line (fill in once real numbers exist):**
"At 10 concurrent users, p99 latency was ___ ms. At 10,000 simulated concurrent users with ___ replicas, p99 latency was ___ ms — within the same target band, with a ___% error rate."

## 5. Known Bottlenecks & Fixes

Document anything that broke under load and how it was fixed — this is often more interesting in an interview than the fact that it eventually worked.

| Issue Found | At What Scale | Root Cause | Fix Applied |
|---|---|---|---|
| Transaction-level fraud rate was ~0.04%, far below the 0.5% target | Found at n_accounts=2000 during Phase 1 verification | `fraud_rate` parameter was applied as an account-level rate, but each legitimate account contributes ~60-70 transactions while each fraud event only contributes a handful — the two rates aren't the same thing, and conflating them silently under-shot the target by ~10x | Added an empirical correction factor (9x) to scale the account-level sampling rate so the *realized transaction-level* rate lands near the target; verified by re-running `dataset_summary()` across 3 seeds, landing consistently at 0.29-0.30% |
| `impossible_travel` occasionally mislabeled a pair as fraud when the implied speed was actually *below* the plausibility threshold (695 km/h vs. 900 km/h threshold, found in 1/10 spot-check samples) | Found during a 10-sample manual spot check, confirmed at 200-sample scale (0/200 failures after fix) | The km→degrees coordinate conversion used a flat 111 km/degree for both latitude and longitude. That's only correct for latitude — longitude degrees shrink by `cos(latitude)` away from the equator, so the actual haversine distance between the two generated points was sometimes smaller than intended, especially at non-equatorial latitudes | Corrected the longitude conversion to scale by `cos(latitude)`; widened the random speed margin slightly (1.15–1.8x rather than 1.05–1.6x) for extra safety margin; added a regression test (`test_impossible_travel_always_exceeds_speed_threshold`) asserting 0 failures across 200 generated pairs |

## 6. Open Risks / Things Not Yet Proven

Keep this list honest — anything claimed in `PRD.md` that isn't yet backed by a row in Sections 2–4 above belongs here until it is.

- [ ] 10,000-user load test not yet run
- [ ] Retraining loop not yet demonstrated end-to-end
- [ ] (add more as they arise)

## 7. Security Checklist Log

Date each item in `Security.md`'s "Security Checklist Before Any Deployment" as it's actually confirmed — not all at once right before deploying.

| Date | Checklist Item | Confirmed By | Notes |
|---|---|---|---|
| | No real secrets in git history | | |
| | `.env.example` current, no real values | | |
| | All endpoints have pydantic validation | | |
| | Rate limiting active on `/score` | | |
| | HTTPS enforced at load balancer | | |
| | Database user scoped, non-superuser | | |
| | Dependency scan clean in CI | | |
| | `/health` leaks no internal detail | | |
