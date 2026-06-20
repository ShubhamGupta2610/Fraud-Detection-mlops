# Security.md: Adaptive Fraud & Risk Scoring Engine

This document covers six areas: authentication, data access protection, secrets management, input validation, abuse/bot prevention, and deployment security. Each section states the honest v1 reality (often "not built, not needed yet") alongside the v2 design intent, so this never overstates what's actually implemented — consistent with `Rules.md` Rule 3 ("No Claim Without a Number").

---

## 1. Secure Authentication

**v1 reality:** No authentication exists. Single operator, local/demo use only. This is stated plainly rather than dressed up — there is nothing to defend here yet, and pretending otherwise would be a worse look than an honest gap.

**v2 design intent** (already implied by `schema.md`'s `users` table and `role` column):

- [ ] Passwords are never stored raw — bcrypt or argon2 hashing only, never MD5/SHA1, never reversible encryption
- [ ] Supabase Auth (already in the stack) handles JWT-based sessions and password hashing out of the box — this is one reason Supabase was chosen over rolling custom auth
- [ ] Session tokens are short-lived with refresh tokens, not long-lived static API keys
- [ ] Role checks happen on every protected endpoint (`/retrain`, threshold changes) **server-side** — a hidden UI button is not a security boundary; the API must reject the request regardless of what the frontend shows

**Interview-ready answer:**
> "I didn't build auth in v1 because it wasn't needed for a single-user demo, but the schema and API are structured so adding it later means plugging in Supabase Auth and adding a dependency-injected role check — not a rewrite."

---

## 2. Protect User Data Access

This project's strongest position here is structural: **there is no real user data**, by design.

- [ ] All transaction data is synthetic or from a public benchmark dataset — per `Rules.md` Rule 4 and `PRD.md` Section 7
- [ ] `account_id` and `device_id` are synthetic identifiers, never real PII — per `schema.md` Section 9
- [ ] v2 design intent: row-level access control so a `compliance_viewer` role can read but not write `scores` / `drift_checks`; Postgres Row-Level Security (RLS), natively supported by Supabase, is the right primitive if multi-tenancy is ever added
- [ ] **Named boundary:** if this system were ever connected to real transaction data, it would require a PCI-DSS scoping review before proceeding further. This project is explicitly out of that scope — naming the line matters even when staying behind it.

---

## 3. Protect Secrets & API Keys

- [ ] Secrets are never committed to git — `.env` is in `.gitignore`; `.env.example` is committed instead, showing variable names with no real values
- [ ] All secrets (database URL, Supabase keys, any future third-party keys) are loaded via environment variables / pydantic Settings — never hardcoded
- [ ] Local dev, CI, and production each use different credentials — never shared
- [ ] GitHub Actions secrets are stored in repo/org secret settings, injected at build time, never printed in logs — no `print(os.environ)` or equivalent debug line ever ships
- [ ] Rotation: if a key leaks, it can be rotated via an env var change alone, with no code change required

**Common failure mode to actively guard against:** pasting a real key into a notebook cell "just to test quickly." This is the most likely way a secret actually leaks during fast iteration — treat it as a real rule, not a hypothetical.

---

## 4. Input Validation

- [ ] Schema-level validation via pydantic models on every endpoint — rejects malformed types and missing fields automatically (per `TechSpec.md` Section 8)
- [ ] Range/sanity validation beyond type-checking — e.g. a transaction `amount` of `-50000` or `999999999999` is a technically valid float but nonsensical; explicit bounds are enforced
- [ ] Reject, don't silently coerce — an unexpected `merchant_category` enum value returns a 422, never a silent default. Silent defaults cause confusing bugs and, in fraud specifically, could be exploited (e.g. sending an unrecognized category specifically to dodge a category-based feature)
- [ ] No raw string-interpolated SQL anywhere in the codebase — all database access goes through an ORM / parameterized queries (SQLAlchemy), making SQL injection a non-issue by construction, not by vigilance

---

## 5. Prevent Abuse & Bot Attacks

The realistic interview question here: *"Someone is hammering your `/score` endpoint — what happens?"*

- [ ] Rate limiting per-IP and/or per-API-key on `/score` (e.g. `slowapi` for FastAPI, or enforced at the load balancer/reverse-proxy level)
- [ ] **Load vs. abuse are distinguished, not conflated:** the 10,000-concurrent-user load test (`TechSpec.md` Section 6.8) represents legitimate scale and is handled by horizontal scaling; a bot hammering the endpoint is abuse and is handled by rate limiting and blocking. These look similar at the infrastructure layer but require different responses — this distinction should be explicit in any discussion of the system, not blurred.
- [ ] Layered defense: rate limiting at the load balancer/reverse proxy (cheap, fast, drops obvious abuse before it reaches API replicas) plus finer-grained application-level limits (e.g. per-account scoring frequency)
- [ ] **Abuse itself is a fraud signal:** a bot probing `/score` repeatedly to map the model's decision boundary is fraud-adjacent behavior in its own right — worth logging and potentially feeding back into the system's own fraud signals, not just blocking and forgetting

---

## 6. Secure Deployment

- [ ] No secrets baked into Docker images — env vars injected at runtime only (ties back to Section 3)
- [ ] Minimal container images — slim Python base images, multi-stage builds, no dev dependencies in the production image
- [ ] HTTPS only — TLS termination at the load balancer/reverse proxy; the API is never served over plain HTTP in production
- [ ] Principle of least privilege — the database user the API connects as has permissions scoped only to the tables it needs, never superuser/admin access
- [ ] Dependency scanning in CI — `pip-audit` or GitHub Dependabot alerts, so a known-vulnerable XGBoost/FastAPI/etc. version is flagged automatically rather than discovered later
- [ ] Health checks are isolated from sensitive exposure — `GET /health` exists for the load balancer but never leaks internal details (stack traces, DB connection strings) if something is wrong

---

## Security Checklist Before Any Deployment

Run through this before deploying to a live, publicly reachable instance — not after:

- [ ] No real secrets in git history (check with `git log -p` or a secret-scanning tool, not just the current working tree)
- [ ] `.env.example` is current and contains no real values
- [ ] All endpoints have pydantic input validation
- [ ] Rate limiting is active on `/score`
- [ ] HTTPS is enforced at the load balancer
- [ ] Database user has scoped, non-superuser permissions
- [ ] Dependency scan has run cleanly in CI
- [ ] `/health` does not leak internal error detail

## Interview-Ready Answers

**Q: How do you handle authentication in this project?**
> Your answer here — should reference the honest v1 gap and the concrete v2 plan from Section 1.

**Q: What happens if someone tries to brute-force or abuse your scoring API?**
> Your answer here — should reference rate limiting, the load-vs-abuse distinction, and the fraud-signal callout from Section 5.

**Q: How do you make sure your API keys never leak?**
> Your answer here — should reference the env var discipline and the notebook-paste failure mode from Section 3.

**Q: This system has no real user data — does that mean you didn't have to think about data protection?**
> Your answer here — the point to make is the opposite: having no real PII was a deliberate scoping decision, and the RLS / PCI-DSS boundary in Section 2 shows you know what *would* be required if that changed.
