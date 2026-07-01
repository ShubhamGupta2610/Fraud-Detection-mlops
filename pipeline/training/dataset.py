"""
Assembles a flat, model-ready DataFrame from Phase 1's generator and
Phase 2's feature pipeline.

WHY THIS IS ITS OWN MODULE rather than inlined in a training script:
every script in Phase 3 (baseline, XGBoost, Isolation Forest, SHAP,
calibration, error analysis) needs the EXACT same dataset, built the
EXACT same way, or results across them stop being comparable. One
function, called identically everywhere, prevents that drift.
"""

import pandas as pd
from datetime import datetime

from pipeline.generators.transaction_stream import generate_dataset
from pipeline.features.pipeline import run_feature_pipeline

FEATURE_COLUMNS = [
    "txn_count_1min", "txn_count_1h", "txn_count_24h",
    "total_amount_1h", "total_amount_24h", "distinct_merchants_24h",
    "geo_velocity", "amount_deviation_from_avg", "hour_of_day_deviation",
    "merchant_category_novelty", "is_new_device", "is_new_ip_or_location",
]


def build_training_dataframe(
    n_accounts: int = 6000,
    fraud_rate: float = 0.005,
    seed: int = 42,
    end_time: datetime = None,
) -> pd.DataFrame:
    """
    Returns a flat DataFrame: one row per transaction, FEATURE_COLUMNS
    plus account_id, timestamp, is_fraud, fraud_type.

    is_fraud and fraud_type are kept in the DataFrame for splitting,
    evaluation, and error analysis - but per docs/data_leakage.md
    Section 1, FEATURE_COLUMNS is the ONLY thing that should ever be
    passed to X (the model input). Any training code that does
    `X = df.drop(columns=["is_fraud"])` instead of
    `X = df[FEATURE_COLUMNS]` is one accidental column rename away from
    a leakage bug - so every script in this phase uses FEATURE_COLUMNS
    explicitly, never drop-everything-else.
    """
    if end_time is None:
        end_time = datetime(2026, 6, 1)

    transactions = generate_dataset(
        n_accounts=n_accounts, fraud_rate=fraud_rate, end_time=end_time, seed=seed,
    )
    rows = run_feature_pipeline(transactions)

    flat_rows = []
    for r in rows:
        flat = {
            "account_id": r["account_id"],
            "timestamp": r["timestamp"],
            "is_fraud": int(r["label"]["is_fraud"]),
            "fraud_type": r["label"]["fraud_type"],
        }
        flat.update(r["features"])
        flat_rows.append(flat)

    df = pd.DataFrame(flat_rows)
    df = df.sort_values("timestamp").reset_index(drop=True)
    return df


def time_based_split(df: pd.DataFrame, test_fraction: float = 0.2):
    """
    Splits chronologically - train on the earlier portion, test on the
    later portion - rather than a random shuffle split.

    WHY THIS MATTERS (docs/data_leakage.md Section 2, flagged in Phase 2
    as a Phase 3 reminder): a random split lets the model train on
    transactions that happened AFTER some of its test examples, which a
    real production model could never do - it would never have access
    to the future when scoring a transaction. A random split would make
    offline metrics look better than the model could actually achieve
    in production. Splitting by time is the honest version of this
    experiment, even though it usually produces a harder (less
    flattering) number than a random split would.
    """
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    split_idx = int(len(df_sorted) * (1 - test_fraction))
    train_df = df_sorted.iloc[:split_idx].copy()
    test_df = df_sorted.iloc[split_idx:].copy()
    return train_df, test_df
