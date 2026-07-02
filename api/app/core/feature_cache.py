"""
In-process feature cache: holds each account's recent transaction
history so real-time sliding-window features (velocity, geo-velocity,
behavioral deviation) can be computed without a database round-trip on
every /score call.

WHY NOT REDIS YET (TechSpec.md Section 6.3):
Redis is the v2 upgrade "once load testing shows it's actually needed."
An in-process dict is simpler, faster at small scale, and has zero
operational overhead for a v1 single-replica deployment. Phase 9's
load testing will tell us whether we actually hit a cache bottleneck
under concurrent load, and at that point the upgrade path is clear:
replace this class with one backed by Redis, keeping the same interface
so nothing else in the codebase changes.

THREAD SAFETY:
FastAPI runs request handlers as async coroutines in an event loop -
standard asyncio concurrency, not multi-threading. Python's GIL means
dict access here is effectively safe without explicit locking for our
v1 use case. If we moved to a multi-process deployment (e.g. uvicorn
with multiple workers), each process would have its own cache and
consistency across workers would be a real concern - at that point the
Redis upgrade becomes mandatory, not optional.
"""

from collections import defaultdict
from datetime import datetime
from typing import List

from pipeline.generators.legitimate import RawTransaction
from pipeline.features.history_store import AccountHistoryStore


class InProcessFeatureCache:
    """
    Wraps AccountHistoryStore (Phase 2's sliding-window engine) in a
    simple singleton that lives for the API process's lifetime.

    This is intentionally stateful within a single process - that's the
    whole point of a cache. The statelessness requirement (TechSpec.md
    Section 6.2) applies to HTTP request handling (any replica can serve
    any request), not to the in-process optimization layer that supports
    it.
    """

    def __init__(self):
        self._store = AccountHistoryStore()

    def add_transaction(self, txn: RawTransaction) -> None:
        """
        Add a transaction to the account's history after scoring it -
        so it becomes visible to the NEXT request for this account.
        Never call this BEFORE computing features for the same
        transaction (the same ordering rule as Phase 2's pipeline.py).
        """
        self._store.add(txn)

    def get_store(self) -> AccountHistoryStore:
        """
        Returns the underlying AccountHistoryStore for use by the
        feature engineering functions from Phase 2 - they accept a
        store directly, so no API changes needed there.
        """
        return self._store

    def known_account_count(self) -> int:
        return len(self._store._history)


# Module-level singleton - created once when this module is first
# imported, shared across all requests in this process.
feature_cache = InProcessFeatureCache()
