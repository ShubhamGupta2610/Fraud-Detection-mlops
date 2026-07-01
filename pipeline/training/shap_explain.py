"""
SHAP explainability for the chosen XGBoost model.
TreeExplainer specifically, per research/05_shap_notes.md - exploits
the tree structure directly rather than treating the model as a black
box, which is why it's dramatically faster than the general-purpose
KernelExplainer for tree-based models like XGBoost.
"""

import shap
import numpy as np

from pipeline.training.dataset import build_training_dataframe, time_based_split, FEATURE_COLUMNS
from pipeline.training.xgboost_models import train_class_weighted_xgboost


def build_shap_explainer(model):
    return shap.TreeExplainer(model)


def explain_transaction(explainer, X_row: np.ndarray, feature_names: list, top_n: int = 5) -> dict:
    """
    Per-transaction local explanation: top_n features ranked by
    |SHAP value|, exactly the shape AppFlow.md's per-transaction
    explanation panel needs.
    """
    shap_values = explainer.shap_values(X_row.reshape(1, -1))[0]

    pairs = list(zip(feature_names, shap_values))
    pairs.sort(key=lambda p: abs(p[1]), reverse=True)

    return {
        "top_features": [
            {"feature": name, "shap_value": round(float(val), 4)}
            for name, val in pairs[:top_n]
        ]
    }


def global_feature_importance(explainer, X: np.ndarray, feature_names: list) -> list:
    """Mean |SHAP value| per feature across the dataset - the global summary."""
    shap_values = explainer.shap_values(X)
    mean_abs = np.abs(shap_values).mean(axis=0)

    importance = sorted(
        zip(feature_names, mean_abs),
        key=lambda p: p[1], reverse=True,
    )
    return [{"feature": name, "mean_abs_shap": round(float(val), 4)} for name, val in importance]


if __name__ == "__main__":
    df = build_training_dataframe(n_accounts=6000, fraud_rate=0.005, seed=42)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df["is_fraud"].values
    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df["is_fraud"].values

    model, metrics = train_class_weighted_xgboost(X_train, y_train, X_test, y_test)
    explainer = build_shap_explainer(model)

    print("=== Global feature importance (mean |SHAP value| across test set) ===")
    importance = global_feature_importance(explainer, X_test, FEATURE_COLUMNS)
    for item in importance:
        print(f"  {item['feature']}: {item['mean_abs_shap']}")

    print()
    print("=== Local explanation: a real fraud transaction from the test set ===")
    fraud_indices = np.where(y_test == 1)[0]
    sample_idx = fraud_indices[0]
    explanation = explain_transaction(explainer, X_test[sample_idx], FEATURE_COLUMNS)
    print(f"Transaction (test row {sample_idx}), true label = fraud:")
    for f in explanation["top_features"]:
        direction = "pushes toward FRAUD" if f["shap_value"] > 0 else "pushes toward LEGITIMATE"
        print(f"  {f['feature']}: {f['shap_value']} ({direction})")

    print()
    print("=== Local explanation: a real legitimate transaction from the test set ===")
    legit_indices = np.where(y_test == 0)[0]
    sample_idx2 = legit_indices[0]
    explanation2 = explain_transaction(explainer, X_test[sample_idx2], FEATURE_COLUMNS)
    print(f"Transaction (test row {sample_idx2}), true label = legitimate:")
    for f in explanation2["top_features"]:
        direction = "pushes toward FRAUD" if f["shap_value"] > 0 else "pushes toward LEGITIMATE"
        print(f"  {f['feature']}: {f['shap_value']} ({direction})")
