"""
Decision engine: converts a calibrated risk probability into a
allow/challenge/block decision by applying a configurable threshold.

WHY THIS IS A SEPARATE MODULE, NOT INLINED IN THE ROUTE HANDLER:
Rules.md Rule 7: "Never hardcode a 0.5 classification threshold as the
final decision boundary. The threshold must come from the cost-curve
calculation (TechSpec.md 5.4)." Keeping this logic separate makes it
easy to:
  1. Change the threshold at runtime (the dashboard's "Apply Threshold"
     button in AppFlow.md will call an endpoint that updates this)
  2. Test the decision logic independently of the HTTP layer
  3. Audit exactly what threshold was in effect when any past decision
     was made (schema.md's scores.threshold_used column)
"""

from app.schemas.scoring import DecisionEnum


# The cost-optimal threshold from Phase 3's cost_curve.py:
# threshold=0.12, saving 5.2% vs the default 0.5 at the cost
# assumptions in cost_curve.py ($350 fraud loss / $25 false-positive
# cost). Stored as a module-level variable so it can be updated at
# runtime via the /threshold endpoint in Phase 5/6.
#
# This is still a default - Rules.md Rule 7 says the threshold must
# NOT stay as a hardcoded constant once the cost curve is built, and
# it isn't: it's now the measured cost-optimal value from Phase 3,
# exposed as a mutable variable the dashboard can change.
_current_threshold: float = 0.12


def get_current_threshold() -> float:
    return _current_threshold


def set_threshold(new_threshold: float) -> None:
    """
    Updates the active threshold. Called by the dashboard's
    "Apply Threshold" action (AppFlow.md Section 3.4).
    Validates the range before accepting the change.
    """
    global _current_threshold
    if not 0.0 < new_threshold < 1.0:
        raise ValueError(f"Threshold must be between 0 and 1, got {new_threshold}")
    _current_threshold = new_threshold


def make_decision(risk_probability: float, threshold: float = None) -> DecisionEnum:
    """
    Converts a calibrated risk probability (0-1, from the model) into
    a 3-way decision using a two-tier threshold:

    - >= challenge_threshold: challenge (flag for manual review)
    - >= block_threshold: block outright
    - below challenge_threshold: allow

    WHY TWO TIERS, NOT JUST ONE:
    A binary allow/block decision is too coarse for a real fraud system.
    "Challenge" (e.g. trigger a 2FA step or ask for additional
    verification) lets borderline transactions proceed with extra checks
    rather than flatly blocking a potentially-legitimate customer -
    reducing the false-positive cost in practice, which is exactly what
    the cost curve in Phase 3 was optimizing for.
    """
    if threshold is None:
        threshold = _current_threshold

    # Challenge threshold sits slightly below the block threshold -
    # the gap is the "uncertain zone" where a human or a 2FA check
    # is a better answer than an outright block.
    challenge_threshold = threshold
    block_threshold = threshold + 0.3  # transactions scoring > 0.42 get blocked outright

    if risk_probability >= block_threshold:
        return DecisionEnum.block
    elif risk_probability >= challenge_threshold:
        return DecisionEnum.challenge
    else:
        return DecisionEnum.allow


def probability_to_risk_score(probability: float) -> float:
    """
    Converts a calibrated probability (0-1) to a 0-100 risk score for
    the dashboard display - per ScoreResponse.risk_score in schemas.py.
    Simple linear scaling; the meaningful number is still the probability
    and threshold, but 0-100 reads more intuitively in a UI.
    """
    return round(probability * 100, 2)
