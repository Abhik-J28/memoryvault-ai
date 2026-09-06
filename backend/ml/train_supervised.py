"""
MemoryVault AI -- Supervised Location Classifier (Production Pipeline)
=======================================================================
Phase 2, Step 3 (revised)  |  SRS Section 7 / FR-05 / FR-06 / VR-01

Differences from train_classifier.py
--------------------------------------
- Reserves a strict 80/20 stratified train/test holdout split
- 5-fold CV is executed on the TRAINING split only (no test-set leakage)
- Final metrics are reported on the held-out TEST split
- Output artefact: location_classifier.joblib
- evaluation_metrics.json is overwritten with test-set metrics

Pipeline
--------
1.  Load synthetic_context_data.csv
2.  Engineer 4 interaction features (encode the 4 conditional placement rules)
3.  80/20 stratified train/test split (random_state=42)
4.  ColumnTransformer: OHE for categoricals, StandardScaler for numerics
5.  5-fold StratifiedKFold CV on the TRAINING set:
        - Top-1 Accuracy
        - Top-3 Categorical Accuracy  (SRS NFR-02 >= 0.80)
        - Macro OvR ROC-AUC           (SRS NFR-03 >= 0.85)
6.  Fit final XGBClassifier on the full training set
7.  Evaluate on the held-out test set
8.  Confusion Matrix + per-class One-vs-Rest ROC curves
9.  Serialize pipeline + label encoder -> artifacts/location_classifier.joblib
10. Export artifacts/evaluation_metrics.json

Usage (from backend/ root):
    python ml/train_supervised.py
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
    accuracy_score,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import StratifiedKFold, train_test_split
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
_JOBLIB_PATH  = _ARTIFACT_DIR / "location_classifier.joblib"
_JSON_PATH    = _ARTIFACT_DIR / "evaluation_metrics.json"

# ---------------------------------------------------------------------------
# Feature schema
# ---------------------------------------------------------------------------
CATEGORICAL_FEATURES = ["item_type", "weather_condition"]
NUMERIC_FEATURES = [
    "time_of_day", "day_of_week", "fatigue_level", "carrying_baggage",
    # Engineered interaction features (the 4 conditional placement rules)
    "feat_baggage_entry_item",  # R1: baggage & keys|backpack  -> foyer/kitchen
    "feat_tired_night",         # R2: fatigue>=4 & time>=21    -> bedroom/couch
    "feat_work_hours",          # R3: spectacles|earphones & weekday & 9-18 -> desk
    "feat_inclement_baggage",   # R4: rain|snow & baggage       -> foyer boost
]
ALL_CONTEXT_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET_COLUMN = "target_zone"

# ---------------------------------------------------------------------------
# Hyperparameters & thresholds (SRS NFR-02 / NFR-03)
# ---------------------------------------------------------------------------
RANDOM_STATE   = 42
TEST_SIZE      = 0.20
N_SPLITS       = 5
TOP_K          = 3
TOP3_THRESHOLD = 0.80   # NFR-02
ROC_THRESHOLD  = 0.85   # NFR-03
ROC_SAMPLE_PTS = 50     # points per class exported to JSON


# ===========================================================================
# Feature engineering
# ===========================================================================

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Materialise the four dataset conditional rules as binary (0/1) features.
    Called AFTER the carrying_baggage column has been cast to int.
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


# ===========================================================================
# Data loading
# ===========================================================================

def load_data(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    """Load CSV and return (X_df, y_series) with engineered features."""
    df = pd.read_csv(path)

    raw_required = [
        "item_type", "weather_condition", "time_of_day", "day_of_week",
        "fatigue_level", "carrying_baggage", TARGET_COLUMN,
    ]
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


# ===========================================================================
# Preprocessor
# ===========================================================================

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


# ===========================================================================
# XGBoost factory
# ===========================================================================

def build_xgb(n_classes: int) -> XGBClassifier:
    return XGBClassifier(
        objective        = "multi:softprob",
        eval_metric      = "mlogloss",
        num_class        = n_classes,
        n_estimators     = 400,
        max_depth        = 6,
        learning_rate    = 0.08,
        subsample        = 0.85,
        colsample_bytree = 0.85,
        min_child_weight = 3,
        use_label_encoder= False,
        random_state     = RANDOM_STATE,
        n_jobs           = -1,
        verbosity        = 0,
    )


# ===========================================================================
# Metric helpers
# ===========================================================================

def top_k_accuracy(y_true: np.ndarray, y_prob: np.ndarray, k: int = 3) -> float:
    top_k = np.argsort(y_prob, axis=1)[:, -k:]
    return float(np.mean([y_true[i] in top_k[i] for i in range(len(y_true))]))


def compute_roc_curves(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    classes: list[str],
    n_pts: int = ROC_SAMPLE_PTS,
) -> dict[str, dict]:
    """Per-class One-vs-Rest ROC curves, down-sampled to n_pts for compact JSON."""
    lb    = LabelBinarizer().fit(range(len(classes)))
    y_bin = lb.transform(y_true)
    result: dict[str, dict] = {}
    for i, name in enumerate(classes):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_prob[:, i])
        auc_val     = float(np.trapezoid(tpr, fpr))
        idx         = np.linspace(0, len(fpr) - 1, n_pts, dtype=int)
        result[name] = {
            "fpr": [round(float(v), 5) for v in fpr[idx]],
            "tpr": [round(float(v), 5) for v in tpr[idx]],
            "auc": round(auc_val, 5),
        }
    return result


# ===========================================================================
# 5-fold CV on training split
# ===========================================================================

def run_cv(
    X_train: pd.DataFrame,
    y_train: np.ndarray,
    n_classes: int,
) -> dict[str, list[float]]:
    """
    Run N_SPLITS-fold StratifiedKFold CV strictly on the training partition.
    Returns lists of fold scores for top1, top3, and roc_auc.
    """
    skf    = StratifiedKFold(n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE)
    top1s: list[float] = []
    top3s: list[float] = []
    rocs:  list[float] = []

    for fold, (tr_idx, val_idx) in enumerate(skf.split(X_train, y_train), 1):
        X_tr, X_val = X_train.iloc[tr_idx], X_train.iloc[val_idx]
        y_tr, y_val = y_train[tr_idx], y_train[val_idx]

        pre = build_preprocessor()
        X_tr_p  = pre.fit_transform(X_tr)
        X_val_p = pre.transform(X_val)

        mdl = build_xgb(n_classes)
        mdl.fit(X_tr_p, y_tr, eval_set=[(X_val_p, y_val)], verbose=False)

        y_prob = mdl.predict_proba(X_val_p)
        y_pred = np.argmax(y_prob, axis=1)

        top1 = float(accuracy_score(y_val, y_pred))
        top3 = top_k_accuracy(y_val, y_prob, k=TOP_K)
        roc  = roc_auc_score(y_val, y_prob, multi_class="ovr", average="macro")

        top1s.append(top1)
        top3s.append(top3)
        rocs.append(roc)

        print(
            f"  Fold {fold}/{N_SPLITS} -> "
            f"Top-1: {top1:.4f}  |  Top-3: {top3:.4f}  |  ROC-AUC: {roc:.4f}"
        )

    return {"top1": top1s, "top3": top3s, "roc_auc": rocs}


# ===========================================================================
# Serialisation helpers
# ===========================================================================

def save_joblib(
    preprocessor: ColumnTransformer,
    model: XGBClassifier,
    label_encoder: LabelEncoder,
    path: Path,
) -> None:
    joblib.dump(
        {"preprocessor": preprocessor, "model": model, "label_encoder": label_encoder},
        path,
    )
    print(f"[train_supervised] Saved joblib -> {path}")


def save_metrics_json(
    cv_scores: dict[str, list[float]],
    test_metrics: dict,
    classes: list[str],
    cm: np.ndarray,
    roc_data: dict[str, dict],
    path: Path,
) -> None:
    payload = {
        # CV averages (training split only)
        "cv_top1_mean":    round(float(np.mean(cv_scores["top1"])),  6),
        "cv_top3_mean":    round(float(np.mean(cv_scores["top3"])),  6),
        "cv_roc_auc_mean": round(float(np.mean(cv_scores["roc_auc"])), 6),
        "cv_top1_folds":    [round(v, 6) for v in cv_scores["top1"]],
        "cv_top3_folds":    [round(v, 6) for v in cv_scores["top3"]],
        "cv_roc_auc_folds": [round(v, 6) for v in cv_scores["roc_auc"]],
        # Holdout test-set metrics
        "test_top1_accuracy": round(test_metrics["top1"], 6),
        "top3_accuracy":      round(test_metrics["top3"], 6),   # NFR-02
        "roc_auc_macro":      round(test_metrics["roc"],  6),   # NFR-03
        # Acceptance criteria
        "nfr02_threshold":  TOP3_THRESHOLD,
        "nfr03_threshold":  ROC_THRESHOLD,
        "nfr02_passed":     test_metrics["top3"] >= TOP3_THRESHOLD,
        "nfr03_passed":     test_metrics["roc"]  >= ROC_THRESHOLD,
        # Class metadata
        "classes":          classes,
        "n_classes":        len(classes),
        "train_test_split": f"80/{int(TEST_SIZE*100)}",
        # Confusion matrix & ROC curves for Evaluator UI
        "confusion_matrix": cm.tolist(),
        "roc_curves":       roc_data,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"[train_supervised] Saved evaluation metrics JSON -> {path}")


# ===========================================================================
# Formatted report
# ===========================================================================

def print_report(
    cv_scores: dict[str, list[float]],
    test_metrics: dict,
    classes: list[str],
    cm: np.ndarray,
) -> None:
    sep = "=" * 72

    print()
    print(sep)
    print("  MemoryVault AI -- Supervised Pipeline Evaluation Report")
    print(sep)

    # ---- CV summary ----
    print(f"\n  5-Fold Stratified CV (on 80% training split):")
    print(f"  {'Fold':<6} {'Top-1 Acc':>10}  {'Top-3 Acc':>10}  {'ROC-AUC (macro)':>16}")
    print(f"  {'-'*6} {'-'*10}  {'-'*10}  {'-'*16}")
    for i, (t1, t3, roc) in enumerate(
        zip(cv_scores["top1"], cv_scores["top3"], cv_scores["roc_auc"]), 1
    ):
        print(f"  {i:<6} {t1:>10.4f}  {t3:>10.4f}  {roc:>16.4f}")
    cv_t1  = float(np.mean(cv_scores["top1"]))
    cv_t3  = float(np.mean(cv_scores["top3"]))
    cv_roc = float(np.mean(cv_scores["roc_auc"]))
    print(f"  {'MEAN':<6} {cv_t1:>10.4f}  {cv_t3:>10.4f}  {cv_roc:>16.4f}")

    # ---- Test-set results ----
    t1  = test_metrics["top1"]
    t3  = test_metrics["top3"]
    roc = test_metrics["roc"]
    print(f"\n  Held-out Test Set Results (20%):")
    print(f"    Top-1 Accuracy  : {t1:.4f}")
    print(
        f"    Top-3 Accuracy  : {t3:.4f}  "
        f"(NFR-02 threshold >= {TOP3_THRESHOLD})  "
        f"[{'PASS' if t3 >= TOP3_THRESHOLD else 'FAIL'}]"
    )
    print(
        f"    ROC-AUC (macro) : {roc:.4f}  "
        f"(NFR-03 threshold >= {ROC_THRESHOLD})  "
        f"[{'PASS' if roc >= ROC_THRESHOLD else 'FAIL'}]"
    )

    # ---- Confusion matrix ----
    print(f"\n  Confusion Matrix (rows=Actual, cols=Predicted):")
    short = [c[:8] for c in classes]
    hdr   = f"  {'':>28}" + "".join(f"{s:>10}" for s in short)
    print(hdr)
    for i, row_cls in enumerate(classes):
        row = f"  {row_cls:<28}" + "".join(f"{cm[i,j]:>10}" for j in range(len(classes)))
        print(row)

    # ---- Final verdict ----
    print()
    nfr02_ok = t3  >= TOP3_THRESHOLD
    nfr03_ok = roc >= ROC_THRESHOLD
    if nfr02_ok and nfr03_ok:
        print(f"  [PASS]  All SRS Section 7 acceptance criteria met.")
    else:
        if not nfr02_ok:
            print(f"  [FAIL]  NFR-02: Top-3 {t3:.4f} < {TOP3_THRESHOLD}")
        if not nfr03_ok:
            print(f"  [FAIL]  NFR-03: ROC-AUC {roc:.4f} < {ROC_THRESHOLD}")

    print(sep)
    print()


# ===========================================================================
# Main
# ===========================================================================

def main() -> None:
    print("[train_supervised] Phase 2, Step 3 -- Supervised Location Classifier")
    print(f"[train_supervised] Data     <- {_DATA_PATH}")
    print(f"[train_supervised] Joblib   -> {_JOBLIB_PATH}")
    print(f"[train_supervised] JSON     -> {_JSON_PATH}")
    print()

    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # 1. Load data                                                         #
    # ------------------------------------------------------------------ #
    print("[train_supervised] Loading dataset...")
    X, y_raw = load_data(_DATA_PATH)
    print(f"[train_supervised] {len(X):,} rows  |  {len(ALL_CONTEXT_FEATURES)} features")

    # ------------------------------------------------------------------ #
    # 2. Encode target labels                                              #
    # ------------------------------------------------------------------ #
    label_encoder = LabelEncoder()
    y_enc         = label_encoder.fit_transform(y_raw)
    classes       = list(label_encoder.classes_)
    n_classes     = len(classes)
    print(f"[train_supervised] {n_classes} classes: {classes}")

    # ------------------------------------------------------------------ #
    # 3. 80/20 stratified train / test split                               #
    # ------------------------------------------------------------------ #
    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc,
        test_size    = TEST_SIZE,
        stratify     = y_enc,
        random_state = RANDOM_STATE,
    )
    print(
        f"[train_supervised] Train: {len(X_train):,} rows  |  "
        f"Test: {len(X_test):,} rows  (80/20 stratified)"
    )

    # ------------------------------------------------------------------ #
    # 4. 5-fold CV on training split                                       #
    # ------------------------------------------------------------------ #
    print(f"\n[train_supervised] Running {N_SPLITS}-fold Stratified CV on training set...")
    cv_scores = run_cv(X_train, y_train, n_classes)

    cv_t3  = float(np.mean(cv_scores["top3"]))
    cv_roc = float(np.mean(cv_scores["roc_auc"]))
    print(f"\n[train_supervised] CV mean Top-3 : {cv_t3:.4f}")
    print(f"[train_supervised] CV mean ROC-AUC: {cv_roc:.4f}")

    if cv_t3 < TOP3_THRESHOLD:
        warnings.warn(
            f"NFR-02 WARNING: CV Top-3 mean {cv_t3:.4f} < {TOP3_THRESHOLD}",
            stacklevel=2,
        )
    if cv_roc < ROC_THRESHOLD:
        warnings.warn(
            f"NFR-03 WARNING: CV ROC-AUC mean {cv_roc:.4f} < {ROC_THRESHOLD}",
            stacklevel=2,
        )

    # ------------------------------------------------------------------ #
    # 5. Fit final model on full training set                              #
    # ------------------------------------------------------------------ #
    print("\n[train_supervised] Fitting final model on full training set...")
    preprocessor = build_preprocessor()
    X_train_proc = preprocessor.fit_transform(X_train)
    X_test_proc  = preprocessor.transform(X_test)

    final_model  = build_xgb(n_classes)
    final_model.fit(
        X_train_proc, y_train,
        eval_set = [(X_test_proc, y_test)],
        verbose  = False,
    )
    print("[train_supervised] Final model trained.")

    # ------------------------------------------------------------------ #
    # 6. Evaluate on held-out test set                                     #
    # ------------------------------------------------------------------ #
    y_prob_test = final_model.predict_proba(X_test_proc)
    y_pred_test = np.argmax(y_prob_test, axis=1)

    test_top1 = float(accuracy_score(y_test, y_pred_test))
    test_top3 = top_k_accuracy(y_test, y_prob_test, k=TOP_K)
    test_roc  = roc_auc_score(
        y_test, y_prob_test,
        multi_class = "ovr",
        average     = "macro",
    )
    test_metrics = {"top1": test_top1, "top3": test_top3, "roc": test_roc}

    print(f"[train_supervised] Test Top-1 Accuracy : {test_top1:.4f}")
    print(f"[train_supervised] Test Top-3 Accuracy : {test_top3:.4f}")
    print(f"[train_supervised] Test ROC-AUC (macro): {test_roc:.4f}")

    # ------------------------------------------------------------------ #
    # 7. Confusion matrix + per-class ROC curves                           #
    # ------------------------------------------------------------------ #
    cm       = confusion_matrix(y_test, y_pred_test)
    roc_data = compute_roc_curves(y_test, y_prob_test, classes)

    # ------------------------------------------------------------------ #
    # 8. Serialize                                                         #
    # ------------------------------------------------------------------ #
    save_joblib(preprocessor, final_model, label_encoder, _JOBLIB_PATH)
    save_metrics_json(cv_scores, test_metrics, classes, cm, roc_data, _JSON_PATH)

    # ------------------------------------------------------------------ #
    # 9. Print formatted report                                            #
    # ------------------------------------------------------------------ #
    print_report(cv_scores, test_metrics, classes, cm)

    # ------------------------------------------------------------------ #
    # 10. Final acceptance check                                            #
    # ------------------------------------------------------------------ #
    nfr02_ok = test_top3 >= TOP3_THRESHOLD
    nfr03_ok = test_roc  >= ROC_THRESHOLD

    if not nfr02_ok:
        warnings.warn(
            f"NFR-02 FAIL: Test Top-3 {test_top3:.4f} < {TOP3_THRESHOLD}", stacklevel=2
        )
    if not nfr03_ok:
        warnings.warn(
            f"NFR-03 FAIL: Test ROC-AUC {test_roc:.4f} < {ROC_THRESHOLD}", stacklevel=2
        )

    if nfr02_ok and nfr03_ok:
        print("[DONE]  Phase 2, Step 3 complete.")
        print(f"        location_classifier.joblib -> {_JOBLIB_PATH}")
        print(f"        evaluation_metrics.json    -> {_JSON_PATH}")
    else:
        print("ERROR: SRS Section 7 acceptance criteria not met.")
        sys.exit(1)


if __name__ == "__main__":
    main()
