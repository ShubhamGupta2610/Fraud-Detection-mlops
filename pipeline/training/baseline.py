"""
Logistic regression baseline.

WHY THIS RUNS FIRST, BEFORE XGBOOST:
docs/model_comparison.md treats this as a floor, not a contender - its
job is to give us an honest number to beat, and to force us to look the
accuracy-under-imbalance trap in the eye before any more sophisticated
model could quietly hide it behind a good-looking metric.

Logistic regression is also naturally closer to producing calibrated
probabilities than XGBoost (research/04_xgboost_notes.md /
docs/calibration_analysis.md), so its calibration curve is a useful
point of comparison once we get there.
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    precision_recall_curve, auc, confusion_matrix,
    precision_score, recall_score, brier_score_loss,
)
from sklearn.preprocessing import StandardScaler

from pipeline.training.dataset import build_training_dataframe, time_based_split, FEATURE_COLUMNS


def compute_naive_baseline_accuracy(test_df) -> float:
    """
    The "always predict legitimate" accuracy trap, computed for real on
    whatever test set is passed in - per research/01_fraud_domain.md,
    this number should be looked at and internalized, not just known
    abstractly. On this project's actual test set (6000 accounts,
    seed=42, 0.5% target fraud rate): 99.22% accuracy, 0% recall.
    """
    n_test = len(test_df)
    n_fraud = test_df["is_fraud"].sum()
    return (n_test - n_fraud) / n_test


def train_logistic_regression_baseline(train_df, test_df):
    """
    Returns (model, scaler, metrics_dict). Logistic regression DOES
    need feature scaling (unlike the tree-based models coming next) -
    research/04_xgboost_notes.md asks specifically why tree-based models
    don't need this: trees split on thresholds per feature independently,
    so the scale of one feature doesn't affect how splits on another
    feature are chosen. Logistic regression's gradient descent, by
    contrast, is sensitive to feature scale - a feature ranging in the
    thousands (total_amount_24h) would dominate the loss gradient over
    one ranging in single digits (is_new_device) purely due to scale,
    not actual predictive value.
    """
    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df["is_fraud"].values
    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df["is_fraud"].values

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)  # transform only, never fit, on test - docs/data_leakage.md Section 4

    # class_weight="balanced" is logistic regression's equivalent of
    # XGBoost's scale_pos_weight - both reweight the loss function to
    # penalize missing the minority class more heavily, per
    # research/03_imbalance_learning.md.
    model = LogisticRegression(class_weight="balanced", max_iter=1000, random_state=42)
    model.fit(X_train_scaled, y_train)

    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    y_pred_default_threshold = (y_proba >= 0.5).astype(int)

    precision, recall, _ = precision_recall_curve(y_test, y_proba)
    pr_auc = auc(recall, precision)

    metrics = {
        "pr_auc": round(pr_auc, 4),
        "precision_at_0.5": round(precision_score(y_test, y_pred_default_threshold, zero_division=0), 4),
        "recall_at_0.5": round(recall_score(y_test, y_pred_default_threshold, zero_division=0), 4),
        "brier_score": round(brier_score_loss(y_test, y_proba), 4),
        "naive_baseline_accuracy": round(compute_naive_baseline_accuracy(test_df), 4),
        "confusion_matrix_at_0.5": confusion_matrix(y_test, y_pred_default_threshold).tolist(),
    }

    return model, scaler, metrics


if __name__ == "__main__":
    df = build_training_dataframe(n_accounts=6000, fraud_rate=0.005, seed=42)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    print(f"Train: {len(train_df)} rows, {train_df['is_fraud'].sum()} fraud")
    print(f"Test:  {len(test_df)} rows, {test_df['is_fraud'].sum()} fraud")
    print()

    model, scaler, metrics = train_logistic_regression_baseline(train_df, test_df)

    print("=== Logistic Regression Baseline ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    print()
    print(f"INTERPRETATION: naive 'always legitimate' accuracy is "
          f"{metrics['naive_baseline_accuracy']*100:.2f}% with 0% recall.")
    print(f"This model gets PR-AUC={metrics['pr_auc']} with "
          f"{metrics['recall_at_0.5']*100:.1f}% recall at the default 0.5 threshold - "
          f"a real, if imperfect, improvement over the naive trap.")
