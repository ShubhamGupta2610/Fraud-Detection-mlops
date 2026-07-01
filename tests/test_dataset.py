"""
Tests for pipeline/training/dataset.py.
"""

from pipeline.training.dataset import build_training_dataframe, time_based_split, FEATURE_COLUMNS


def test_time_based_split_contains_fraud_in_both_halves():
    """
    Regression test for the fraud-clustering bug found during Phase 3
    verification: the original generator placed every fraud event in
    the last 5 days of the whole dataset, so an 80/20 time-based split
    put 100% of fraud into the test set and left the model with nothing
    to learn from. Fixed in transaction_stream.py by spreading fraud
    events across each account's own history window instead.
    """
    df = build_training_dataframe(n_accounts=3000, fraud_rate=0.005, seed=42)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    assert train_df["is_fraud"].sum() > 0, "train set must contain at least some fraud examples"
    assert test_df["is_fraud"].sum() > 0, "test set must contain at least some fraud examples"


def test_time_based_split_does_not_overlap_in_time():
    """The split boundary must be real: every train timestamp before every test timestamp."""
    df = build_training_dataframe(n_accounts=1000, fraud_rate=0.01, seed=7)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    assert train_df["timestamp"].max() <= test_df["timestamp"].min()


def test_feature_columns_exclude_label_and_identifier_fields():
    """
    Direct check that FEATURE_COLUMNS - the list every training script
    in this phase is required to use - never accidentally includes
    is_fraud, fraud_type, account_id, or timestamp.
    """
    forbidden = {"is_fraud", "fraud_type", "account_id", "timestamp"}
    assert forbidden.isdisjoint(set(FEATURE_COLUMNS))


def test_dataframe_has_no_missing_values_in_feature_columns():
    """
    Every feature function in Phase 2 has an explicit, documented
    cold-start default - none of them should ever produce a null. If
    one did, it would mean a cold-start case was missed somewhere.
    """
    df = build_training_dataframe(n_accounts=1000, fraud_rate=0.01, seed=3)
    assert df[FEATURE_COLUMNS].isnull().sum().sum() == 0
