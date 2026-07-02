"""
Model loading: loads the trained artifact and SHAP explainer once at
API startup, stores them in app.state, and provides a clean dependency
for route handlers to retrieve them.

WHY LOAD ONCE AT STARTUP, NOT PER REQUEST:
Loading a pickle file per /score call would take 100-500ms just for
deserialization - before a single feature is even computed. The 100ms
p99 latency target (PRD.md Section 6) would be instantly broken. By
loading at startup and storing in app.state, every request pays ~0ms
for model access (a Python attribute lookup) instead of the full
deserialization cost every time.

WHY APP.STATE, NOT A GLOBAL MODULE-LEVEL VARIABLE:
A module-level global would work for a single-process server, but
FastAPI's recommended pattern is app.state, which:
1. Is explicitly scoped to one app instance
2. Is immediately testable (tests can set app.state.model directly
   without monkeypatching module globals)
3. Clearly communicates "this is loaded once and shared" vs "this is
   computed per-request"
"""

import pickle
import json
import os
import shap
from pathlib import Path
from fastapi import FastAPI

# Resolve the project root relative to THIS file's location
# (api/app/core/model_loader.py -> up 3 levels = project root)
# so artifact discovery works correctly regardless of which
# directory the server is launched from.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARTIFACTS_DIR = PROJECT_ROOT / "pipeline" / "training" / "artifacts"


def find_latest_promoted_model() -> tuple[Path, dict]:
    """
    Finds the most recently saved model artifact that was marked
    promoted=True in its metadata. Returns (pkl_path, metadata_dict).

    In Phase 6, this same logic is reused by the retraining pipeline
    to find which model is "currently live" before deciding whether a
    newly trained model should replace it - so this function is the
    single source of truth for "what is the live model," not scattered
    path lookups across multiple files.
    """
    metadata_files = sorted(ARTIFACTS_DIR.glob("*_metadata.json"), reverse=True)

    for meta_file in metadata_files:
        with open(meta_file) as f:
            metadata = json.load(f)
        if metadata.get("promoted", False):
            # The artifact_path stored in metadata is a relative path
            # (written by train_final_model.py from the project root).
            # We resolve it against the project root rather than trusting
            # it as-is, so it works regardless of launch directory.
            artifact_path = PROJECT_ROOT / metadata["artifact_path"]
            if artifact_path.exists():
                return artifact_path, metadata

    raise FileNotFoundError(
        f"No promoted model artifact found in {ARTIFACTS_DIR}. "
        "Run pipeline/training/train_final_model.py first."
    )


def load_model_and_explainer(app: FastAPI) -> None:
    """
    Called once during app startup (see main.py's lifespan handler).
    Stores the model, SHAP explainer, and metadata on app.state so
    every route handler can access them without reloading.
    """
    artifact_path, metadata = find_latest_promoted_model()

    with open(artifact_path, "rb") as f:
        model = pickle.load(f)

    # SHAP TreeExplainer on the base estimator, not the calibration
    # wrapper - CalibratedClassifierCV wraps the base model, so we
    # reach through to the underlying XGBoost for SHAP computation,
    # which is what TreeExplainer is optimized for.
    base_estimator = model.estimator  # the FrozenEstimator / XGBClassifier inside the calibrated wrapper
    if hasattr(base_estimator, 'estimator'):
        base_estimator = base_estimator.estimator

    explainer = shap.TreeExplainer(base_estimator)

    app.state.model = model
    app.state.explainer = explainer
    app.state.model_version = metadata["version"]
    app.state.model_metadata = metadata
    app.state.score_count = 0
    app.state.fraud_flagged_count = 0
    app.state.total_latency_ms = 0.0

    print(f"[startup] Model loaded: version={metadata['version']}, PR-AUC={metadata['pr_auc']}")
