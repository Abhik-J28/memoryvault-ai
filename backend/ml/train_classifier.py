"""
MemoryVault AI -- Supervised Classifier Training Pipeline
==========================================================
Phase 2, Step 3  |  SRS FR-05 / FR-06 / VR-01 / NFR-02 / NFR-03

Pipeline
--------
1. Load backend/ml/data/synthetic_context_data.csv
2. Separate 6 context features (X) from target label target_zone (y)
3. Preprocess via ColumnTransformer (OHE + StandardScaler)
4. Encode labels with LabelEncoder
5. 5-fold StratifiedKFold cross-validation (FR-06 / VR-01):
     - Top-3 Categorical Accuracy  (NFR-02 threshold: >= 0.80)
     - Macro One-vs-Rest ROC-AUC   (NFR-03 threshold: >= 0.85)
6. Fit final XGBClassifier on the full training corpus
7. Compute Confusion Matrix and per-class ROC curves (FPR / TPR)
8. Serialize {preprocessor, model, label_encoder} -> artifacts/classifier_model.joblib
9. Export evaluation_metrics.json for the Evaluator Analytics UI drawer

Usage (from backend/ root):
    python ml/train_classifier.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import (
    LabelBinarizer,
    LabelEncoder,
    OneHotEncoder,
    StandardScaler,
)
from xgboost import XGBClassifier

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_ML_DIR       = Path(__file__).resolve().parent
_DATA_PATH    = _ML_DIR / "data" / "synthetic_context_data.csv"
_ARTIFACT_DIR = _ML_DIR / "artifacts"
_JOBLIB_PATH  = _ARTIFACT_DIR / "classifier_model.joblib"
_JSON_PATH    = _ARTIFACT_DIR / "evaluation_metrics.json"

# ---------------------------------------------------------------------------
# Feature schema  (SRS Section 5)
# ---------------------------------------------------------------------------
CATEGORICAL_FEATURES = ["item_type", "weather_condition"]
NUMERIC_FEATURES     = [
    "time_of_day", "day_of_week", "fatigue_level", "carrying_baggage",
    # Engineered interaction features (mirror the 4 conditional rules)
    "feat_baggage_entry_item",   # R1: baggage & (keys|backpack)
    "feat_tired_night",          # R2: fatigue>=4 & time>=21
    "feat_work_hours",           # R3: (spectacles|earphones) & weekday & midday
    "feat_inclement_baggage",    # R4: (rain|snow) & baggage
]
ALL_CONTEXT_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET_COLUMN        = "target_zone"

# ---------------------------------------------------------------------------
# CV & threshold constants  (SRS NFR-02 / NFR-03)
# ---------------------------------------------------------------------------
N_SPLITS       = 5
RANDOM_STATE   = 42
TOP_K          = 3
TOP3_THRESHOLD = 0.80   # NFR-02
ROC_THRESHOLD  = 0.85   # NFR-03

# Number of ROC curve sample points exported per class (keeps JSON small)
ROC_SAMPLE_PTS = 50


# ---------------------------------------------------------------------------
# Step 2: Load data
# ---------------------------------------------------------------------------

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Materialise the four conditional placement rules as explicit numeric
    boolean features (0 / 1) so the classifier can exploit them directly.

    R1: carrying_baggage=True AND item in {keys, backpack}
    R2: fatigue_level >= 4 AND time_of_day >= 21.0
    R3: item in {spectacles, earphones} AND weekday (0-4) AND 9<=time<=18
    R4: weather in {rain, snow} AND carrying_baggage=True
    """
    df = df.copy()
    df["feat_baggage_entry_item"] = (
        (df["carrying_baggage"] == 1) &
        (df["item_type"].isin(["keys", "backpack"]))
    ).astype(int)
    df["feat_tired_night"] = (
        (df["fatigue_level"] >= 4) &
        (df["time_of_day"] >= 21.0)
    ).astype(int)
    df["feat_work_hours"] = (
        (df["item_type"].isin(["spectacles", "earphones"])) &
        (df["day_of_week"] <= 4) &
        (df["time_of_day"] >= 9.0) &
        (df["time_of_day"] <= 18.0)
    ).astype(int)
    df["feat_inclement_baggage"] = (
        (df["weather_condition"].isin(["rain", "snow"])) &
        (df["carrying_baggage"] == 1)
    ).astype(int)
    return df


def load_data(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    """Load CSV, cast boolean column, return (X_df, y_series)."""
    df = pd.read_csv(path)

    # Validate only the raw SRS schema columns (engineered features don't exist yet)
    raw_required = ["item_type", "weather_condition",
                    "time_of_day", "day_of_week", "fatigue_level",
                    "carrying_baggage", TARGET_COLUMN]
    missing = [c for c in raw_required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns: {missing}")

    df["carrying_baggage"] = df["carrying_baggage"].map(
        {True: 1, False: 0, "True": 1, "False": 0}
    ).astype(int)

    df = engineer_features(df)

    X = df[ALL_CONTEXT_FEATURES].copy()
    y = df[TARGET_COLUMN].copy()
    return X, y


# ---------------------------------------------------------------------------
# Step 3: Preprocessor
# ---------------------------------------------------------------------------

def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            (
                "num",
                StandardScaler(),
                NUMERIC_FEATURES,
            ),
        ],
        remainder="drop",
    )


# ---------------------------------------------------------------------------
# Step 4 + 5 helper: Top-K accuracy
# ---------------------------------------------------------------------------

def top_k_accuracy(y_true_enc: np.ndarray, y_prob: np.ndarray, k: int = 3) -> float:
    """
    Fraction of samples where the true class appears in the top-k predicted
    probability positions.
    """
    top_k_pred = np.argsort(y_prob, axis=1)[:, -k:]
    return float(np.mean([
        y_true_enc[i] in top_k_pred[i]
        for i in range(len(y_true_enc))
    ]))


# ---------------------------------------------------------------------------
# Step 5: 5-fold Stratified Cross-Validation
# ---------------------------------------------------------------------------

def run_cross_validation(
    X: pd.DataFrame,
    y_enc: np.ndarray,
    preprocessor: ColumnTransformer,
    n_classes: int,
) -> tuple[list[float], list[float]]:
    """
    Run 5-fold StratifiedKFold CV.

    Returns
    -------
    top3_scores : list of per-fold Top-3 accuracies
    roc_scores  : list of per-fold macro OvR ROC-AUC scores
    """
    skf        = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    top3_scores: list[float] = []
    roc_scores:  list[float] = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y_enc), start=1):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y_enc[train_idx], y_enc[val_idx]

        # Fit preprocessor only on training split to avoid leakage
        pre = build_preprocessor()
        X_tr_proc  = pre.fit_transform(X_tr)
        X_val_proc = pre.transform(X_val)

        model = _build_xgb(n_classes)
        model.fit(
            X_tr_proc, y_tr,
            eval_set=[(X_val_proc, y_val)],
            verbose=False,
        )

        y_prob = model.predict_proba(X_val_proc)

        t3  = top_k_accuracy(y_val, y_prob, k=TOP_K)
        roc = roc_auc_score(
            y_val, y_prob,
            multi_class="ovr",
            average="macro",
        )

        top3_scores.append(t3)
        roc_scores.append(roc)
        print(
            f"  Fold {fold}/{N_SPLITS} -> "
            f"Top-3 Acc: {t3:.4f}  |  ROC-AUC (macro OvR): {roc:.4f}"
        )

    return top3_scores, roc_scores


# ---------------------------------------------------------------------------
# XGBClassifier factory
# ---------------------------------------------------------------------------

def _build_xgb(n_classes: int) -> XGBClassifier:
    return XGBClassifier(
        objective       = "multi:softprob",
        eval_metric     = "mlogloss",
        num_class       = n_classes,
        n_estimators    = 300,
        max_depth       = 6,
        learning_rate   = 0.1,
        subsample       = 0.8,
        colsample_bytree= 0.8,
        use_label_encoder = False,
        random_state    = RANDOM_STATE,
        n_jobs          = -1,
        verbosity       = 0,
    )


# ---------------------------------------------------------------------------
# Step 7a: Confusion Matrix
# ---------------------------------------------------------------------------

def compute_confusion_matrix(
    y_true_enc: np.ndarray,
    y_pred_enc: np.ndarray,
) -> np.ndarray:
    return confusion_matrix(y_true_enc, y_pred_enc)


# ---------------------------------------------------------------------------
# Step 7b: Per-class ROC curves
# ---------------------------------------------------------------------------

def compute_roc_curves(
    y_true_enc: np.ndarray,
    y_prob: np.ndarray,
    classes: list[str],
    n_pts: int = ROC_SAMPLE_PTS,
) -> dict[str, dict]:
    """
    Compute One-vs-Rest ROC curve (FPR, TPR) for each class.
    Down-samples to n_pts evenly-spaced points to keep the JSON compact.
    """
    lb         = LabelBinarizer()
    y_bin      = lb.fit_transform(y_true_enc)      # (n_samples, n_classes)
    roc_data: dict[str, dict] = {}

    for i, class_name in enumerate(classes):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_prob[:, i])
        auc_val     = float(np.trapezoid(tpr, fpr))

        # Subsample to n_pts evenly-spaced indices for compact JSON
        idx     = np.linspace(0, len(fpr) - 1, n_pts, dtype=int)
        roc_data[class_name] = {
            "fpr":      [round(float(v), 5) for v in fpr[idx]],
            "tpr":      [round(float(v), 5) for v in tpr[idx]],
            "auc":      round(auc_val, 5),
        }

    return roc_data


# ---------------------------------------------------------------------------
# Step 8: Serialize joblib
# ---------------------------------------------------------------------------

def save_joblib(
    preprocessor: ColumnTransformer,
    model: XGBClassifier,
    label_encoder: LabelEncoder,
    path: Path,
) -> None:
    payload = {
        "preprocessor":   preprocessor,
        "model":          model,
        "label_encoder":  label_encoder,
    }
    joblib.dump(payload, path)
    print(f"[train_classifier] Saved joblib artifact -> {path}")


# ---------------------------------------------------------------------------
# Step 9: Export evaluation_metrics.json
# ---------------------------------------------------------------------------

def save_evaluation_json(
    top3_cv: list[float],
    roc_cv: list[float],
    top3_final: float,
    roc_final: float,
    classes: list[str],
    cm: np.ndarray,
    roc_curves_data: dict[str, dict],
    path: Path,
) -> None:
    payload = {
        "top3_accuracy":     round(top3_final, 6),
        "roc_auc_macro":     round(roc_final, 6),
        "top3_cv_folds":     [round(v, 6) for v in top3_cv],
        "roc_auc_cv_folds":  [round(v, 6) for v in roc_cv],
        "top3_cv_mean":      round(float(np.mean(top3_cv)), 6),
        "roc_auc_cv_mean":   round(float(np.mean(roc_cv)), 6),
        "nfr02_threshold":   TOP3_THRESHOLD,
        "nfr03_threshold":   ROC_THRESHOLD,
        "nfr02_passed":      top3_final >= TOP3_THRESHOLD,
        "nfr03_passed":      roc_final  >= ROC_THRESHOLD,
        "classes":           classes,
        "confusion_matrix":  cm.tolist(),
        "roc_curves":        roc_curves_data,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"[train_classifier] Saved evaluation metrics JSON -> {path}")


# ---------------------------------------------------------------------------
# Pretty-print final summary
# ---------------------------------------------------------------------------

def print_summary(
    top3_cv: list[float],
    roc_cv: list[float],
    top3_final: float,
    roc_final: float,
    classes: list[str],
    cm: np.ndarray,
) -> None:
    print()
    print("=" * 68)
    print("  MemoryVault AI -- Supervised Classifier Evaluation Summary")
    print("=" * 68)

    # CV summary
    print(f"\n  5-Fold Stratified Cross-Validation Results:")
    print(f"  {'Fold':<6} {'Top-3 Acc':>10}  {'ROC-AUC (macro OvR)':>20}")
    print(f"  {'-'*6} {'-'*10}  {'-'*20}")
    for i, (t3, roc) in enumerate(zip(top3_cv, roc_cv), 1):
        print(f"  {i:<6} {t3:>10.4f}  {roc:>20.4f}")
    print(f"  {'MEAN':<6} {float(np.mean(top3_cv)):>10.4f}  {float(np.mean(roc_cv)):>20.4f}")

    # Final model on full corpus
    print(f"\n  Final model (trained on full corpus):")
    print(f"    Top-3 Accuracy  : {top3_final:.4f}  "
          f"(NFR-02 threshold >= {TOP3_THRESHOLD:.2f})  "
          f"[{'PASS' if top3_final >= TOP3_THRESHOLD else 'FAIL'}]")
    print(f"    ROC-AUC (macro) : {roc_final:.4f}  "
          f"(NFR-03 threshold >= {ROC_THRESHOLD:.2f})  "
          f"[{'PASS' if roc_final >= ROC_THRESHOLD else 'FAIL'}]")

    # Confusion matrix
    print(f"\n  Confusion Matrix (rows=Actual, cols=Predicted):")
    header = f"  {'':>28}" + "".join(f"{c[:8]:>10}" for c in classes)
    print(header)
    for i, row_cls in enumerate(classes):
        row_str = f"  {row_cls:<28}" + "".join(f"{cm[i, j]:>10}" for j in range(len(classes)))
        print(row_str)

    print()
    print("=" * 68)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("[train_classifier] Phase 2, Step 3 -- Supervised Classification")
    print(f"[train_classifier] Data     <- {_DATA_PATH}")
    print(f"[train_classifier] Joblib   -> {_JOBLIB_PATH}")
    print(f"[train_classifier] JSON     -> {_JSON_PATH}")
    print()

    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Step 2: Load ----
    print("[train_classifier] Loading dataset...")
    X, y_raw = load_data(_DATA_PATH)
    print(f"[train_classifier] Loaded {len(X):,} rows | "
          f"Classes: {sorted(y_raw.unique())}")

    # ---- Step 4: Encode labels ----
    label_encoder = LabelEncoder()
    y_enc         = label_encoder.fit_transform(y_raw)
    classes       = list(label_encoder.classes_)
    n_classes     = len(classes)
    print(f"[train_classifier] {n_classes} target zones: {classes}")

    # ---- Step 5: 5-fold StratifiedKFold CV ----
    print(f"\n[train_classifier] Running {N_SPLITS}-fold Stratified CV...")
    preprocessor   = build_preprocessor()
    top3_cv, roc_cv = run_cross_validation(X, y_enc, preprocessor, n_classes)

    mean_top3 = float(np.mean(top3_cv))
    mean_roc  = float(np.mean(roc_cv))
    print(f"\n[train_classifier] CV Mean Top-3 Acc : {mean_top3:.4f}")
    print(f"[train_classifier] CV Mean ROC-AUC   : {mean_roc:.4f}")

    # Threshold warnings
    if mean_top3 < TOP3_THRESHOLD:
        warnings.warn(
            f"NFR-02 WARNING: CV mean Top-3 accuracy {mean_top3:.4f} "
            f"< threshold {TOP3_THRESHOLD:.2f}",
            stacklevel=2,
        )
    if mean_roc < ROC_THRESHOLD:
        warnings.warn(
            f"NFR-03 WARNING: CV mean ROC-AUC {mean_roc:.4f} "
            f"< threshold {ROC_THRESHOLD:.2f}",
            stacklevel=2,
        )

    # ---- Step 6: Fit final model on full corpus ----
    print("\n[train_classifier] Fitting final model on full corpus...")
    final_preprocessor = build_preprocessor()
    X_all_proc         = final_preprocessor.fit_transform(X)

    final_model = _build_xgb(n_classes)
    final_model.fit(X_all_proc, y_enc, verbose=False)
    print("[train_classifier] Final model trained.")

    # Final evaluation metrics on full corpus (in-sample, for JSON export)
    y_prob_final = final_model.predict_proba(X_all_proc)
    y_pred_final = np.argmax(y_prob_final, axis=1)

    top3_final = top_k_accuracy(y_enc, y_prob_final, k=TOP_K)
    roc_final  = roc_auc_score(
        y_enc, y_prob_final,
        multi_class="ovr",
        average="macro",
    )

    print(f"[train_classifier] Final Top-3 Accuracy : {top3_final:.4f}")
    print(f"[train_classifier] Final ROC-AUC (macro): {roc_final:.4f}")

    # ---- Step 7a: Confusion Matrix ----
    cm = compute_confusion_matrix(y_enc, y_pred_final)

    # ---- Step 7b: ROC curves ----
    roc_curves_data = compute_roc_curves(y_enc, y_prob_final, classes)

    # ---- Step 8: Serialize ----
    save_joblib(final_preprocessor, final_model, label_encoder, _JOBLIB_PATH)

    # ---- Step 9: Export JSON ----
    save_evaluation_json(
        top3_cv, roc_cv,
        top3_final, roc_final,
        classes, cm, roc_curves_data,
        _JSON_PATH,
    )

    # ---- Print summary ----
    print_summary(top3_cv, roc_cv, top3_final, roc_final, classes, cm)

    # Final threshold assertions
    nfr02_ok = top3_final >= TOP3_THRESHOLD
    nfr03_ok = roc_final  >= ROC_THRESHOLD

    if not nfr02_ok:
        warnings.warn(
            f"NFR-02 FAIL: Final Top-3 accuracy {top3_final:.4f} "
            f"< {TOP3_THRESHOLD:.2f}", stacklevel=2,
        )
    if not nfr03_ok:
        warnings.warn(
            f"NFR-03 FAIL: Final ROC-AUC {roc_final:.4f} "
            f"< {ROC_THRESHOLD:.2f}", stacklevel=2,
        )

    if nfr02_ok and nfr03_ok:
        print("[DONE]  Phase 2, Step 3 complete.")
        print("        NFR-02 (Top-3 >= 0.80): PASS")
        print("        NFR-03 (ROC-AUC >= 0.85): PASS")
        print(f"        Artifacts written to: {_ARTIFACT_DIR}")
    else:
        print("ERROR: One or more NFR thresholds not met. "
              "Review model hyperparameters or dataset quality.")
        sys.exit(1)


if __name__ == "__main__":
    main()
