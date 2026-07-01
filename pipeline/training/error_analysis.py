"""
Error analysis: digs into WHICH transactions the model gets wrong, not
just the aggregate PR-AUC number. Per docs/error_analysis.md and
Rules.md Rule 13 - this is a required deliverable for Phase 3, not
optional polish.
"""

import numpy as np
import pandas as pd

from pipeline.training.dataset import build_training_dataframe, time_based_split, FEATURE_COLUMNS
from pipeline.training.xgboost_models import train_class_weighted_xgboost
from pipeline.training.shap_explain import build_shap_explainer, explain_transaction


def recall_by_fraud_type(test_df: pd.DataFrame, y_pred: np.ndarray) -> dict:
    """
    Breaks recall down by fraud SUBTYPE, not just overall - per
    docs/error_analysis.md, a model can have decent overall recall while
    completely missing one entire fraud category, and only this
    breakdown reveals that.
    """
    result = {}
    fraud_rows = test_df[test_df["is_fraud"] == 1].copy()
    fraud_rows["predicted"] = y_pred[test_df["is_fraud"].values == 1]

    for fraud_type in fraud_rows["fraud_type"].unique():
        subset = fraud_rows[fraud_rows["fraud_type"] == fraud_type]
        caught = (subset["predicted"] == 1).sum()
        total = len(subset)
        result[fraud_type] = {
            "total": int(total),
            "caught": int(caught),
            "recall": round(caught / total, 4) if total else None,
        }
    return result


def top_false_positives(test_df: pd.DataFrame, y_proba: np.ndarray, explainer, n=10):
    """
    Highest-confidence false positives: legitimate transactions the
    model was MOST sure were fraud. Per docs/error_analysis.md Section 1.
    """
    df = test_df.copy()
    df["proba"] = y_proba
    df["predicted"] = (y_proba >= 0.5).astype(int)

    fp = df[(df["is_fraud"] == 0) & (df["predicted"] == 1)].sort_values("proba", ascending=False).head(n)

    results = []
    for idx, row in fp.iterrows():
        X_row = row[FEATURE_COLUMNS].values.astype(float)
        explanation = explain_transaction(explainer, X_row, FEATURE_COLUMNS, top_n=3)
        results.append({
            "account_id": row["account_id"][:8],
            "proba": round(float(row["proba"]), 4),
            "top_features": explanation["top_features"],
        })
    return results


def top_false_negatives(test_df: pd.DataFrame, y_proba: np.ndarray, explainer, n=10):
    """
    Lowest-confidence false negatives: real fraud the model was MOST
    confident was legitimate. Per docs/error_analysis.md Section 2.
    """
    df = test_df.copy()
    df["proba"] = y_proba
    df["predicted"] = (y_proba >= 0.5).astype(int)

    fn = df[(df["is_fraud"] == 1) & (df["predicted"] == 0)].sort_values("proba", ascending=True).head(n)

    results = []
    for idx, row in fn.iterrows():
        X_row = row[FEATURE_COLUMNS].values.astype(float)
        explanation = explain_transaction(explainer, X_row, FEATURE_COLUMNS, top_n=3)
        results.append({
            "account_id": row["account_id"][:8],
            "fraud_type": row["fraud_type"],
            "proba": round(float(row["proba"]), 4),
            "top_features": explanation["top_features"],
        })
    return results


if __name__ == "__main__":
    df = build_training_dataframe(n_accounts=6000, fraud_rate=0.005, seed=42)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df["is_fraud"].values
    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df["is_fraud"].values

    model, metrics = train_class_weighted_xgboost(X_train, y_train, X_test, y_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)
    explainer = build_shap_explainer(model)

    print("=== Recall by fraud type ===")
    by_type = recall_by_fraud_type(test_df, y_pred)
    for fraud_type, stats in by_type.items():
        print(f"  {fraud_type}: {stats['caught']}/{stats['total']} caught (recall={stats['recall']})")

    print()
    print("=== Top false positives (legitimate flagged as fraud, highest confidence) ===")
    fps = top_false_positives(test_df, y_proba, explainer, n=5)
    for fp in fps:
        print(f"  account={fp['account_id']} proba={fp['proba']}")
        for f in fp["top_features"]:
            print(f"      {f['feature']}: {f['shap_value']}")

    print()
    print("=== Top false negatives (fraud missed, lowest confidence it was fraud) ===")
    fns = top_false_negatives(test_df, y_proba, explainer, n=5)
    for fn in fns:
        print(f"  account={fn['account_id']} fraud_type={fn['fraud_type']} proba={fn['proba']}")
        for f in fn["top_features"]:
            print(f"      {f['feature']}: {f['shap_value']}")
