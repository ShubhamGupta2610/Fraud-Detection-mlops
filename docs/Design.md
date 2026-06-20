# Design.md: Adaptive Fraud & Risk Scoring Engine

## 1. Design Style

Clean, data-dense, "mission control" aesthetic — closer to a trading-desk or SOC (security operations center) dashboard than a consumer app. Function over decoration: every element should communicate a number, a trend, or a state.

## 2. Color Palette

| Color | Hex | Use |
|---|---|---|
| Deep Teal (primary) | `#1F4E5C` | Headers, primary buttons, active nav |
| Background | `#F7F9FA` | Page background — light, not stark white |
| Risk Red | `#C0392B` | High risk / blocked transactions, drift alerts, latency-degradation warnings |
| Caution Amber | `#E0A800` | Medium risk / challenged transactions, approaching-threshold warnings |
| Safe Green | `#2E8B57` | Low risk / allowed transactions, healthy drift status, latency within target |
| Neutral Grey | `#595959` | Secondary text, captions, axis labels |

The red/amber/green mapping is used consistently everywhere a status appears — risk level, drift status, **and system latency health** — so the System Health page reuses the same visual language as the fraud-risk panels rather than inventing a new one.

## 3. Typography

- Primary font: Inter or system-ui sans-serif (Streamlit default)
- Numbers/metrics: larger, bold weight, scannable at a glance — this matters especially on the System Health page where a single p99 latency number is the headline
- No more than 2 font sizes per page beyond the metric/heading distinction

## 4. Component Style

- Metric cards: bordered, light-shaded boxes with a label, a large number, and a trend indicator (↑/↓ vs. previous period)
- Charts: minimal gridlines, no 3D effects, consistent risk-color mapping
- Tables (Live Feed): zebra-striped rows, risk-level badge as the leftmost column
- Alerts (drift, retraining, latency degradation): a persistent top-of-page banner, not a disappearing toast
- Load-test comparison chart (System Health): a simple side-by-side bar or line chart — "10 users" vs. "10,000 users" — with the latency target line overlaid, so the claim is visually self-evident

## 5. Layout Rules

- Sidebar navigation, fixed width, always visible
- Each page: KPI summary row at top, detail charts/tables below — consistent across every page including System Health
- Maximum content width capped for readability on large monitors

## 6. Mobile / Desktop Behavior

Desktop-first by design intent — this is an analyst/operator tool. Streamlit's default responsive stacking is acceptable for v1; no custom mobile layout needed.

## 7. Inspiration References

- Trading platform dashboards (Bloomberg Terminal-style density, without the visual noise)
- Stripe Radar's dashboard — strong reference for tone and information hierarchy
- Grafana — for the drift-monitoring and latency/throughput time-series panels specifically

## 8. Dashboard Design Direction

Each panel should answer one question at a glance before requiring interaction:
- "Is the model performing well?"
- "What does this threshold cost us?"
- "Is anything drifting?"
- "What's the dollar impact?"
- "Why was this flagged?"
- "What's happening right now?"
- **"Does this hold up under load?"** — answered by the System Health page's latency-at-scale chart

## 9. Overall User Experience Principle

Calm, not alarming. Even alert states (drift detected, high-risk transaction, latency degradation under load) should be clear and actionable without being visually panic-inducing — this is a tool an analyst or interviewer will look at closely, not a one-off warning screen.
