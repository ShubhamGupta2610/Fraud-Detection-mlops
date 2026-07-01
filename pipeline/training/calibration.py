"""
Calibration analysis: is XGBoost's raw predict_proba output actually a
calibrated probability, or just a useful ranking? Per
research/04_xgboost_notes.md and docs/calibration_analysis.md - this
matters specifically because the cost curve (cost_curve.py) multiplies
the risk score's implied probability by dollar figures, which is only
honest if the score really does behave like a probability.
"""

import numpy as np
from sklearn.calibration import calibration_curve, CalibratedClassifierCV
from sklearn.metrics import brier_score_loss

from pipeline.training.dataset import build_training_dataframe, time_based_split, FEATURE_COLUMNS
from pipeline.training.xgboost_models import train_class_weighted_xgboost


def compute_calibration_curve(y_true, y_proba, n_bins=5):
    """
    Buckets predictions by predicted probability, compares each
    bucket's average predicted probability to its actual observed
    fraud rate - a well-calibrated model has these two numbers close
    together in every bin.

    n_bins=5, not the more common 10: found by actually running this
    with 10 quantile bins first (see calibration.py's __main__ output
    history / Tracker.md) and seeing 9 of 10 bins collapse to
    predicted=0.0000, actual=0.0000 - an honest consequence of how
    extreme the class imbalance is (most transactions get a
    near-certain "legitimate" score), but not informative. Fewer,
    coarser bins still respect that imbalance while giving each bin
    enough data to say something real.
    """
    fraction_of_positives, mean_predicted_value = calibration_curve(
        y_true, y_proba, n_bins=n_bins, strategy="quantile",
    )
    return list(zip(mean_predicted_value, fraction_of_positives))


def calibrate_with_isotonic(model, X_train, y_train):
    """
    Isotonic regression chosen over Platt scaling per
    research/04_xgboost_notes.md's reasoning: more flexible
    (non-parametric, doesn't assume a sigmoid-shaped miscalibration),
    and our training set (n=326k, ~625 fraud) is large enough that
    isotonic's higher data requirement isn't a practical concern here.

    API NOTE (found by actually running this, not by reading docs in
    isolation): scikit-learn >=1.6 removed CalibratedClassifierCV's
    cv="prefit" option in favor of wrapping an already-fitted estimator
    in sklearn.frozen.FrozenEstimator first. We're on sklearn 1.8.0 here
    (research/04_xgboost_notes.md - worth noting library versions
    matter even for well-established APIs). FrozenEstimator marks the
    model as "do not refit me," which is exactly the semantic
    cv="prefit" used to express.
    """
    from sklearn.frozen import FrozenEstimator

    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="isotonic")
    calibrated.fit(X_train, y_train)
    return calibrated


if __name__ == "__main__":
    df = build_training_dataframe(n_accounts=6000, fraud_rate=0.005, seed=42)
    train_df, test_df = time_based_split(df, test_fraction=0.2)

    X_train = train_df[FEATURE_COLUMNS].values
    y_train = train_df["is_fraud"].values
    X_test = test_df[FEATURE_COLUMNS].values
    y_test = test_df["is_fraud"].values

    model, metrics = train_class_weighted_xgboost(X_train, y_train, X_test, y_test)
    y_proba_raw = model.predict_proba(X_test)[:, 1]

    print("=== Raw XGBoost output calibration ===")
    raw_brier = brier_score_loss(y_test, y_proba_raw)
    print(f"Brier score (raw): {round(raw_brier, 6)}")
    print("Calibration curve (mean_predicted, actual_fraction):")
    for mean_pred, actual_frac in compute_calibration_curve(y_test, y_proba_raw):
        gap = abs(mean_pred - actual_frac)
        print(f"  predicted={mean_pred:.4f}  actual={actual_frac:.4f}  gap={gap:.4f}")

    print()
    print("=== Calibrating with isotonic regression (held-out calibration split) ===")
    # Use a portion of the TRAINING set, held out from model fitting,
    # to fit the calibration map - using the test set here would leak
    # test information into the calibration step itself, the same
    # leakage principle from docs/data_leakage.md applied to this
    # specific technique.
    split = int(len(X_train) * 0.8)
    X_fit, X_calib = X_train[:split], X_train[split:]
    y_fit, y_calib = y_train[:split], y_train[split:]

    import xgboost as xgb
    refit_model = xgb.XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        scale_pos_weight=(y_fit == 0).sum() / max((y_fit == 1).sum(), 1),
        eval_metric="logloss", random_state=42,
    )
    refit_model.fit(X_fit, y_fit)

    calibrated_model = calibrate_with_isotonic(refit_model, X_calib, y_calib)
    y_proba_calibrated = calibrated_model.predict_proba(X_test)[:, 1]

    calibrated_brier = brier_score_loss(y_test, y_proba_calibrated)
    print(f"Brier score (calibrated): {round(calibrated_brier, 6)}")
    print("Calibration curve (mean_predicted, actual_fraction):")
    for mean_pred, actual_frac in compute_calibration_curve(y_test, y_proba_calibrated):
        gap = abs(mean_pred - actual_frac)
        print(f"  predicted={mean_pred:.4f}  actual={actual_frac:.4f}  gap={gap:.4f}")

    print()
    improvement = raw_brier - calibrated_brier
    print(f"Brier score change: {round(improvement, 6)} "
          f"({'improved' if improvement > 0 else 'did not improve'} by calibration)")
