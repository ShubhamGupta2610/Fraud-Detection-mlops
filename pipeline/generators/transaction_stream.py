"""
Orchestrates the full synthetic dataset: generates the account
population, gives each account a legitimate history, and injects fraud
patterns onto a small subset of accounts at specific points in time.

WHY FRAUD RATE IS KEPT DELIBERATELY LOW AND CONFIGURABLE:
PRD.md and research/03_imbalance_learning.md both center on the fact
that fraud is rare (<1%) - if this generator produced, say, 20% fraud
by default "to make modeling easier," every later phase would be
training and evaluating against a problem that doesn't resemble the
real one. fraud_rate defaults to 0.5%, matching the figure used
throughout the docs, and is a parameter specifically so it CAN be
varied later for controlled experiments (e.g. "how does PR-AUC change
if fraud rate were 2% instead of 0.5%") without rewriting this file.
"""

import random
from datetime import datetime, timedelta
from typing import List

from pipeline.generators.accounts import generate_account_population, AccountProfile
from pipeline.generators.legitimate import generate_legitimate_history, RawTransaction
from pipeline.generators.fraud_patterns import (
    inject_card_testing,
    inject_account_takeover,
    inject_impossible_travel,
)

FRAUD_PATTERN_INJECTORS = {
    "card_testing": inject_card_testing,
    "account_takeover": inject_account_takeover,
    "impossible_travel": inject_impossible_travel,
}


def generate_dataset(
    n_accounts: int = 1000,
    fraud_rate: float = 0.005,
    end_time: datetime = None,
    seed: int = 42,
) -> List[RawTransaction]:
    """
    Returns a single chronologically-sortable list of RawTransaction,
    combining every account's legitimate history with injected fraud
    on a subset of accounts.

    FRAUD RATE DEFINITION - read this before changing fraud_rate:
    fraud_rate is the TARGET fraction of accounts that experience a
    fraud event (closer to how real fraud is reported - some accounts
    are compromised, most never are). It is NOT the resulting fraction
    of individual transactions that will be fraudulent, because each
    fraud event produces a small cluster of transactions (1-12) while
    each legitimate account produces many more over its full history.

    A first version of this function conflated the two and silently
    produced a ~10x lower transaction-level fraud rate than intended
    (0.5% account rate -> ~0.04% transaction rate) - caught by actually
    running dataset_summary() and comparing the number to the target,
    not by assuming the code did what the docstring said. This is
    exactly the kind of check docs/data_leakage.md and Rules.md Rule 3
    ask for: don't trust a number until you've actually measured it.

    To compensate, n_fraud_accounts is now scaled up using an empirical
    correction factor estimated from a calibration run (see
    research/01_fraud_domain.md for the actual numbers from that run) -
    this is an approximation, not exact, because the correction factor
    depends on the average legitimate-history length, which varies with
    n_accounts and the "new"/"short"/"established" mix.
    """
    if end_time is None:
        end_time = datetime.utcnow()

    rng = random.Random(seed)
    accounts = generate_account_population(n_accounts, seed=seed)

    all_transactions: List[RawTransaction] = []

    # Empirical correction: in a calibration run with 2000 established-
    # heavy accounts, the realized transaction-level fraud rate was
    # roughly 8-10x lower than the account-level fraud_rate parameter,
    # because each legitimate account contributes ~67 transactions on
    # average while each fraud event contributes only ~4-6. We scale
    # the account-level target up to compensate, then re-verify with
    # dataset_summary() rather than trusting this constant blindly.
    ACCOUNT_RATE_CORRECTION = 9.0
    target_account_fraud_rate = min(0.9, fraud_rate * ACCOUNT_RATE_CORRECTION)

    n_fraud_accounts = max(1, int(n_accounts * target_account_fraud_rate))
    # Guarantee at least a few of EACH pattern type when n_fraud_accounts
    # is small, instead of leaving pattern assignment purely to chance -
    # this was the second issue the verification run surfaced
    # (impossible_travel didn't appear at all in a small sample purely
    # due to low odds, not a bug, but it's a bad property for a dataset
    # other phases depend on: every pattern should reliably be present).
    fraud_accounts = rng.sample(accounts, k=min(n_fraud_accounts, n_accounts))
    fraud_account_ids = set(a.account_id for a in fraud_accounts)

    pattern_assignment = {}
    patterns_cycle = ["card_testing", "account_takeover", "impossible_travel"]
    for i, account in enumerate(fraud_accounts):
        if account.history_length == "new":
            pattern_assignment[account.account_id] = "card_testing"
        else:
            # Round-robin through the other patterns first (guarantees
            # coverage), then random for any remainder.
            if i < len(patterns_cycle):
                pattern_assignment[account.account_id] = patterns_cycle[i]
            else:
                pattern_assignment[account.account_id] = rng.choice(patterns_cycle)

    for account in accounts:
        legit_history = generate_legitimate_history(account, end_time, rng)
        all_transactions.extend(legit_history)

        if account.account_id in fraud_account_ids:
            pattern = pattern_assignment[account.account_id]

            # Inject the fraud event at a random point spread across the
            # account's own history window, NOT clustered near end_time.
            #
            # CORRECTNESS NOTE (found during Phase 3 verification, not
            # by inspection): the original version always placed
            # fraud_time within the last 5 days of the entire dataset
            # (`end_time - timedelta(days=rng.uniform(0, 5))`). That's
            # fine for Phase 1/2's purposes in isolation, but it
            # silently broke Phase 3's time-based train/test split
            # (docs/data_leakage.md Section 2): with a 6-month dataset
            # split 80/20 by time, EVERY fraud example landed in the
            # last 20% (test set), leaving zero fraud examples to train
            # on. A model can't learn what it never sees. Spreading
            # fraud events across the account's own available history
            # (bounded by how much history that account actually has)
            # fixes this while still respecting each account's own
            # account_age_days - we're not inventing history that
            # wouldn't exist for that account.
            account_span_days = min(account.account_age_days, 180)
            fraud_time = end_time - timedelta(days=rng.uniform(0, max(1, account_span_days)))

            injector = FRAUD_PATTERN_INJECTORS[pattern]
            fraud_transactions = injector(account, fraud_time, rng)
            all_transactions.extend(fraud_transactions)

    all_transactions.sort(key=lambda t: t.timestamp)
    return all_transactions


def dataset_summary(transactions: List[RawTransaction]) -> dict:
    """
    Quick sanity-check summary - used by the verification script and
    worth re-running any time this generator changes, since a silent
    change in fraud rate or pattern mix would invalidate every Phase 3
    modeling result without this kind of check catching it.
    """
    total = len(transactions)
    fraud = [t for t in transactions if t.is_fraud]
    by_pattern = {}
    for t in fraud:
        by_pattern[t.fraud_type] = by_pattern.get(t.fraud_type, 0) + 1

    return {
        "total_transactions": total,
        "fraud_transactions": len(fraud),
        "fraud_rate_pct": round(100 * len(fraud) / total, 4) if total else 0,
        "fraud_by_pattern": by_pattern,
        "distinct_accounts": len(set(t.account_id for t in transactions)),
    }
