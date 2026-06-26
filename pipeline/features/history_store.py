"""
Maintains per-account transaction history so sliding-window features can
be computed using ONLY transactions strictly before the one being scored.

WHY THIS EXISTS AS ITS OWN MODULE (research/02_feature_engineering.md):
The single most important correctness property in this entire phase is:
when computing features for transaction T, we must look only at this
account's transactions with timestamp < T.timestamp. Get this wrong and
every feature becomes a temporal leakage bug (docs/data_leakage.md
Section 2) - the model would be trained on information that wouldn't
exist yet in real production, and Phase 3's metrics would be dishonestly
inflated.

DATA STRUCTURE CHOICE:
A plain Python list per account, kept sorted by timestamp, is used here.
research/02_feature_engineering.md asks specifically about more
efficient structures (deque, time-bucketed counters) for a live system
handling real concurrent traffic - that's a legitimate optimization for
Phase 4/9, but Phase 2's job is CORRECTNESS first. A sorted list with
bisect for the lookback boundary is simple to verify correct, which
matters more right now than raw speed. This tradeoff should be written
into research/02_feature_engineering.md once read.
"""

import bisect
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List

from pipeline.generators.legitimate import RawTransaction


class AccountHistoryStore:
    """
    Holds every account's transactions, sorted by timestamp, and answers
    "what happened in this account's last N minutes/hours, strictly
    before time T" queries.
    """

    def __init__(self):
        self._history: dict[str, List[RawTransaction]] = defaultdict(list)
        self._timestamps: dict[str, List[datetime]] = defaultdict(list)

    def add(self, transaction: RawTransaction) -> None:
        """
        Adds a transaction to history. Transactions MUST be added in
        chronological order per account for the bisect-based lookback
        to remain valid - the feature pipeline (pipeline.py) is
        responsible for processing the full dataset in timestamp order
        for this reason.
        """
        acc = transaction.account_id
        self._history[acc].append(transaction)
        self._timestamps[acc].append(transaction.timestamp)

    def transactions_before(
        self,
        account_id: str,
        before_time: datetime,
        window: timedelta = None,
    ) -> List[RawTransaction]:
        """
        Returns all of this account's transactions with timestamp
        STRICTLY before before_time (never equal - the transaction being
        scored should never see itself in its own history), optionally
        restricted to the last `window` of time before before_time.

        This is the one function every feature in this phase ultimately
        calls - keeping the boundary logic in exactly one place means
        a future bug fix here automatically fixes every feature at once,
        rather than needing to hunt down the same off-by-one mistake in
        five different feature functions.
        """
        timestamps = self._timestamps[account_id]
        # bisect_left on before_time gives the index of the first
        # transaction with timestamp >= before_time - everything before
        # that index has timestamp < before_time, which is exactly the
        # "strictly before, never equal" boundary we need.
        idx = bisect.bisect_left(timestamps, before_time)

        candidates = self._history[account_id][:idx]

        if window is not None:
            window_start = before_time - window
            # candidates is already sorted ascending by timestamp;
            # filter to the window. A second bisect would be faster than
            # a linear filter, but correctness first per the module
            # docstring above - this can be optimized later without
            # changing behavior, which is exactly the kind of change
            # that needs a regression test before AND after.
            candidates = [t for t in candidates if t.timestamp >= window_start]

        return candidates

    def known_devices(self, account_id: str, before_time: datetime) -> set:
        """Distinct device_ids seen for this account before before_time."""
        return {t.device_id for t in self.transactions_before(account_id, before_time)}

    def last_transaction_before(self, account_id: str, before_time: datetime):
        """
        The single most recent transaction strictly before before_time,
        or None if this is the account's first-ever transaction. Used by
        geo_velocity, which only cares about the immediately PRECEDING
        transaction, not the whole window.
        """
        history = self.transactions_before(account_id, before_time)
        return history[-1] if history else None
