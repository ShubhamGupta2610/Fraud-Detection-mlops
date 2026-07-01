"""
Isolation Forest: the unsupervised companion to XGBoost.

WHY THIS MODEL EXISTS IN THIS PROJECT AT ALL (docs/model_comparison.md):
XGBoost learns from labeled fraud examples - it can only catch patterns
that resemble fraud it has SEEN. Isolation Forest needs no labels at
all; it flags transactions that are structurally unusual relative to
the overall population, which means it can catch a genuinely novel
fraud pattern that never appeared in training data. This script's real
job is to measure whether Isolation Forest actually catches anything
XGBoost's predictions miss - not just to report its own standalone
metrics, which (per its anomaly-detection nature) are expected to be
weaker than a supervised model trained directly on the labels.
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_curve, auc

from pipeline.training.dataset import build_training_dataframe, time_based_split, FEATURE_COLUMNS
from pipeline.training.xgboost_models import train_class_weighted_xgboost


def train_isolation_forest(X_train, contamination: float):
    """
    contamination = expected fraction of anomalies, the closest
    Isolation Forest analogue to "fraud rate" - set from the TRAINING
    set's actual observed fraud rate, since in a real deployment we
    wouldn't know the test set's rate in advance either.
    """
    model = IsolationForest(
        n_estimators=200, contamination=contamination, random_state=42, n_jobs=-1,
    )
    model.fit(X_train)
    return model


def isolation_forest_scores_to_risk(model, X) -> np.ndarray:
    """
    IsolationForest.score_samples() returns LOWER values for more
    anomalous points (the opposite direction of a fraud risk score,
    where higher = riskier) - negated and rescaled here so output is
    directly comparable to XGBoost's predict_proba risk direction.
    """
    raw_scores = model.score_samples(X)  # lower = more anomalous
    risk_scores = -raw_scores  # now higher = more anomalous
    # Min-max scale to [0, 1] for comparability with XGBoost's probability output
    risk_scores = (risk_scores - risk_scores.min()) / (risk_scores.max() - risk_scores.min() + 1e-9)
    return risk_scores


def find_xgboost_misses_caught_by_isolation_forest(
    xgb_model, iso_model, X_test, y_test, xgb_threshold=0.5, iso_top_pct=0.01,
):
    """
    The actual value-add check: among the fraud cases XGBoost's
    predictions MISSED (false negatives at xgb_threshold), how many
    does Isolation Forest's top iso_top_pct riskiest scores catch?
    This is the number that belongs in docs/error_analysis.md Section 4
    ("Where Isolation Forest added value beyond XGBoost") - a real
    measured count, not an assumed one.
    """
    xgb_proba = xgb_model.predict_proba(X_test)[:, 1]
    xgb_pred = (xgb_proba >= xgb_threshold).astype(int)

    false_negative_mask = (y_test == 1) & (xgb_pred == 0)
    n_false_negatives = false_negative_mask.sum()

    iso_risk = isolation_forest_scores_to_risk(iso_model, X_test)
    threshold_value = np.quantile(iso_risk, 1 - iso_top_pct)
    iso_flagged_mask = iso_risk >= threshold_value

    caught_by_iso = (false_negative_mask & iso_flagged_mask).sum()

    return {
        "xgb_false_negatives": int(n_false_negatives),
        "iso_top_pct_flagged_count": int(iso_flagged_mask.sum()),
        "xgb_misses_caught_by_isolation_forest": int(caught_by_iso),
        "xgb_misses_caught_pct": round(100 * caught_by_iso / n_false_negatives, 2) if n_false_negatives else None,
    }


if __name__ == "__main__":
    df = build_training_dataframe(n_accounts=6000, fraud_rate=0.005, seed=42)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df["is_fraud"].values
    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df["is_fraud"].values

    train_fraud_rate = y_train.mean()
    print(f"Training Isolation Forest with contamination={train_fraud_rate:.4f} (observed train fraud rate)")

    iso_model = train_isolation_forest(X_train, contamination=max(train_fraud_rate, 0.001))
    iso_risk_test = isolation_forest_scores_to_risk(iso_model, X_test)

    precision, recall, _ = precision_recall_curve(y_test, iso_risk_test)
    pr_auc = auc(recall, precision)
    print(f"Isolation Forest standalone PR-AUC: {round(pr_auc, 4)}")
    print("(Expected to be weaker than XGBoost's labeled-supervised PR-AUC - that's normal for an unsupervised model and not a failure.)")
    print()

    print("Training class-weighted XGBoost for comparison...")
    xgb_model, xgb_metrics = train_class_weighted_xgboost(X_train, y_train, X_test, y_test)
    print(f"XGBoost PR-AUC: {xgb_metrics['pr_auc']}")
    print()

    print("Checking: does Isolation Forest catch any fraud XGBoost's predictions missed?")
    overlap_result = find_xgboost_misses_caught_by_isolation_forest(
        xgb_model, iso_model, X_test, y_test, xgb_threshold=0.5, iso_top_pct=0.01,
    )
    for k, v in overlap_result.items():
        print(f"  {k}: {v}")
