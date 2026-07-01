"""
Cost curve: turns the XGBoost risk score into an actual threshold
decision, per TechSpec.md Section 5.4 and PRD.md's whole premise that a
threshold is a business decision, not a default.

Total Cost = (Missed Fraud Count x Average Fraud Loss)
           + (False Positives Count x Cost of Blocking a Legitimate Customer)
"""

import numpy as np

from pipeline.training.dataset import build_training_dataframe, time_based_split, FEATURE_COLUMNS
from pipeline.training.xgboost_models import train_class_weighted_xgboost

# These two cost figures are assumptions, not measured facts - made up
# but realistic, per TechSpec.md Section 5.4's instruction. Documented
# explicitly here, not buried, since the entire optimal threshold
# depends on this ratio: real fraud teams negotiate these numbers with
# finance/risk stakeholders, they don't derive from ML alone.
AVG_FRAUD_LOSS = 350.0          # dollars lost per fraud transaction that gets through
COST_OF_BLOCKING_LEGIT_CUSTOMER = 25.0  # estimated cost of a false decline (lost sale + support cost + trust damage, amortized)


def compute_cost_curve(y_true, y_proba, thresholds=None):
    """
    Computes total cost at every threshold in `thresholds`, returns a
    list of dicts (threshold, false_negatives, false_positives,
    total_cost, precision, recall) - the data the System Health /
    Threshold & Cost dashboard panel will eventually plot.
    """
    if thresholds is None:
        thresholds = np.arange(0.01, 1.0, 0.01)

    results = []
    for t in thresholds:
        y_pred = (y_proba >= t).astype(int)

        false_negatives = ((y_true == 1) & (y_pred == 0)).sum()
        false_positives = ((y_true == 0) & (y_pred == 1)).sum()
        true_positives = ((y_true == 1) & (y_pred == 1)).sum()

        total_cost = (false_negatives * AVG_FRAUD_LOSS) + (false_positives * COST_OF_BLOCKING_LEGIT_CUSTOMER)

        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0.0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0.0

        results.append({
            "threshold": round(float(t), 2),
            "false_negatives": int(false_negatives),
            "false_positives": int(false_positives),
            "total_cost": round(float(total_cost), 2),
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
        })

    return results


def find_optimal_threshold(cost_curve_results: list) -> dict:
    """Returns the single row with minimum total_cost - the actual answer to 'what threshold should we use.'"""
    return min(cost_curve_results, key=lambda r: r["total_cost"])


if __name__ == "__main__":
    df = build_training_dataframe(n_accounts=6000, fraud_rate=0.005, seed=42)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df["is_fraud"].values
    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df["is_fraud"].values

    model, metrics = train_class_weighted_xgboost(X_train, y_train, X_test, y_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    print(f"AVG_FRAUD_LOSS = ${AVG_FRAUD_LOSS}, COST_OF_BLOCKING_LEGIT_CUSTOMER = ${COST_OF_BLOCKING_LEGIT_CUSTOMER}")
    print(f"Cost ratio (fraud loss / false-positive cost) = {AVG_FRAUD_LOSS/COST_OF_BLOCKING_LEGIT_CUSTOMER:.1f}x")
    print()

    curve = compute_cost_curve(y_test, y_proba)
    optimal = find_optimal_threshold(curve)

    default_threshold_row = next(r for r in curve if r["threshold"] == 0.5)

    print("=== Cost at default threshold (0.5) ===")
    print(f"  FN={default_threshold_row['false_negatives']}, FP={default_threshold_row['false_positives']}, "
          f"total_cost=${default_threshold_row['total_cost']}, "
          f"precision={default_threshold_row['precision']}, recall={default_threshold_row['recall']}")
    print()

    print("=== Optimal threshold (minimum total cost) ===")
    print(f"  threshold={optimal['threshold']}, FN={optimal['false_negatives']}, FP={optimal['false_positives']}, "
          f"total_cost=${optimal['total_cost']}, precision={optimal['precision']}, recall={optimal['recall']}")
    print()

    savings = default_threshold_row["total_cost"] - optimal["total_cost"]
    print(f"Choosing the cost-optimal threshold instead of the default 0.5 saves "
          f"${savings:.2f} on this test set ({100*savings/default_threshold_row['total_cost']:.1f}% reduction).")
