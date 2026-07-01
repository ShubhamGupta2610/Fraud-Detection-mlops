"""
Produces Phase 3's actual saved deliverable: a versioned model artifact
on disk, plus a row of metadata matching schema.md's model_runs table
exactly (version, trained_at, trigger_type, pr_auc, promoted,
artifact_path, feedback_rows_used) - so when Phase 6 wires this up to
the real database, this output slots in directly.

CHOSEN APPROACH, per docs/model_comparison.md: class-weighted XGBoost.
Not SMOTE - the two were close (PR-AUC 0.9617 vs 0.9625, a 0.0008
difference), and class weighting is simpler (no synthetic data, no
inflated training set, lower risk of the SMOTE-specific failure mode
described in research/03_imbalance_learning.md) for a difference this
small. Isotonic calibration is layered on top per
docs/calibration_analysis.md's measured Brier score improvement.
"""

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

from pipeline.training.dataset import build_training_dataframe, time_based_split, FEATURE_COLUMNS
from pipeline.training.xgboost_models import train_class_weighted_xgboost
from pipeline.training.calibration import calibrate_with_isotonic

ARTIFACT_DIR = Path("pipeline/training/artifacts")


def train_and_save_final_model(n_accounts=6000, fraud_rate=0.005, seed=42):
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    df = build_training_dataframe(n_accounts=n_accounts, fraud_rate=fraud_rate, seed=seed)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df["is_fraud"].values
    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df["is_fraud"].values

    # Held-out calibration split from training data only - never test,
    # per docs/data_leakage.md's reasoning applied to calibration.
    split = int(len(X_train) * 0.8)
    X_fit, X_calib = X_train[:split], X_train[split:]
    y_fit, y_calib = y_train[:split], y_train[split:]

    import xgboost as xgb
    base_model = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        scale_pos_weight=(y_fit == 0).sum() / max((y_fit == 1).sum(), 1),
        eval_metric="logloss", random_state=42,
    )
    base_model.fit(X_fit, y_fit)

    calibrated_model = calibrate_with_isotonic(base_model, X_calib, y_calib)

    from sklearn.metrics import precision_recall_curve, auc
    y_proba = calibrated_model.predict_proba(X_test)[:, 1]
    precision, recall, _ = precision_recall_curve(y_test, y_proba)
    pr_auc = auc(recall, precision)

    version = f"v_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    artifact_path = ARTIFACT_DIR / f"{version}.pkl"

    with open(artifact_path, "wb") as f:
        pickle.dump(calibrated_model, f)

    # Matches schema.md model_runs table exactly, field for field.
    model_run_record = {
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "trigger_type": "manual",
        "pr_auc": round(float(pr_auc), 4),
        "promoted": True,  # first model - nothing to compare against yet, so it's promoted by default
        "artifact_path": str(artifact_path),
        "feedback_rows_used": int(len(y_train)),
    }

    metadata_path = ARTIFACT_DIR / f"{version}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(model_run_record, f, indent=2)

    return model_run_record, calibrated_model, (X_test, y_test, test_df)


if __name__ == "__main__":
    record, model, _ = train_and_save_final_model()
    print("Saved model run record (matches schema.md model_runs table):")
    print(json.dumps(record, indent=2))
