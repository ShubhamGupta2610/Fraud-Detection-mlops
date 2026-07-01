"""
XGBoost: class weighting vs. SMOTE vs. plain (no imbalance handling),
compared side by side - per research/03_imbalance_learning.md, this
project commits to actually comparing these rather than picking one
and asserting it was best.
"""

import xgboost as xgb
import numpy as np
from sklearn.metrics import (
    precision_recall_curve, auc, confusion_matrix,
    precision_score, recall_score, brier_score_loss,
)

from pipeline.training.dataset import build_training_dataframe, time_based_split, FEATURE_COLUMNS


def _evaluate(model, X_test, y_test, label: str) -> dict:
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)

    precision, recall, _ = precision_recall_curve(y_test, y_proba)
    pr_auc = auc(recall, precision)

    return {
        "approach": label,
        "pr_auc": round(pr_auc, 4),
        "precision_at_0.5": round(precision_score(y_test, y_pred, zero_division=0), 4),
        "recall_at_0.5": round(recall_score(y_test, y_pred, zero_division=0), 4),
        "brier_score": round(brier_score_loss(y_test, y_proba), 4),
        "confusion_matrix_at_0.5": confusion_matrix(y_test, y_pred).tolist(),
    }


def train_plain_xgboost(X_train, y_train, X_test, y_test) -> dict:
    """No imbalance handling at all - the naive XGBoost approach, included specifically so the other two have something honest to beat."""
    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        eval_metric="logloss", random_state=42,
    )
    model.fit(X_train, y_train)
    return model, _evaluate(model, X_test, y_test, "plain (no imbalance handling)")


def train_class_weighted_xgboost(X_train, y_train, X_test, y_test) -> dict:
    """
    scale_pos_weight, per research/03_imbalance_learning.md - set to the
    ratio of negative to positive class counts in the TRAINING set
    only (never test, to avoid any test-set information leaking into
    a training-time hyperparameter).
    """
    n_neg = (y_train == 0).sum()
    n_pos = (y_train == 1).sum()
    scale_pos_weight = n_neg / n_pos

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss", random_state=42,
    )
    model.fit(X_train, y_train)
    metrics = _evaluate(model, X_test, y_test, "class_weighting")
    metrics["scale_pos_weight_used"] = round(scale_pos_weight, 2)
    return model, metrics


def train_smote_xgboost(X_train, y_train, X_test, y_test) -> dict:
    """
    SMOTE applied to TRAINING data only, AFTER the train/test split -
    per docs/data_leakage.md Section 3, applying SMOTE before splitting
    would let synthetic points derived from what should be unseen test
    examples leak into training, inflating test performance dishonestly.
    The split happens once, upstream, in dataset.time_based_split() -
    this function only ever receives the already-split training data.
    """
    from imblearn.over_sampling import SMOTE

    smote = SMOTE(random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

    model = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        eval_metric="logloss", random_state=42,
    )
    model.fit(X_train_resampled, y_train_resampled)
    metrics = _evaluate(model, X_test, y_test, "SMOTE")
    metrics["train_size_after_smote"] = len(y_train_resampled)
    return model, metrics


if __name__ == "__main__":
    df = build_training_dataframe(n_accounts=6000, fraud_rate=0.005, seed=42)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df["is_fraud"].values
    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df["is_fraud"].values

    print(f"Train: {len(y_train)} rows, {y_train.sum()} fraud ({100*y_train.mean():.4f}%)")
    print(f"Test:  {len(y_test)} rows, {y_test.sum()} fraud ({100*y_test.mean():.4f}%)")
    print()

    results = []

    _, m1 = train_plain_xgboost(X_train, y_train, X_test, y_test)
    results.append(m1)
    print(f"[1/3] plain: PR-AUC={m1['pr_auc']}, precision={m1['precision_at_0.5']}, recall={m1['recall_at_0.5']}")

    _, m2 = train_class_weighted_xgboost(X_train, y_train, X_test, y_test)
    results.append(m2)
    print(f"[2/3] class_weighting (scale_pos_weight={m2['scale_pos_weight_used']}): "
          f"PR-AUC={m2['pr_auc']}, precision={m2['precision_at_0.5']}, recall={m2['recall_at_0.5']}")

    _, m3 = train_smote_xgboost(X_train, y_train, X_test, y_test)
    results.append(m3)
    print(f"[3/3] SMOTE (train size {m3['train_size_after_smote']} after resampling): "
          f"PR-AUC={m3['pr_auc']}, precision={m3['precision_at_0.5']}, recall={m3['recall_at_0.5']}")

    print()
    print("=== Full comparison ===")
    for r in results:
        print(r)
