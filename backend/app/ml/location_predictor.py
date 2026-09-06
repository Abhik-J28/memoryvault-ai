"""
MemoryVault AI — Location Predictor (Supervised ML)
====================================================
Phase 2, Step 2C

Trains a multiclass Random Forest Classifier to predict the most
probable room where an item was placed, given situational context.

Exports
-------
- ``train_predictor(df)`` — train, evaluate, persist, return metrics
- ``predict(features)``   — ranked probability dict for a single query
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelBinarizer, LabelEncoder, StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MODELS_DIR = Path(__file__).resolve().parent / "models"
_MODELS_DIR.mkdir(parents=True, exist_ok=True)

_MODEL_PATH = _MODELS_DIR / "rf_model.joblib"
_SCALER_PATH = _MODELS_DIR / "rf_scaler.joblib"
_ENCODERS_PATH = _MODELS_DIR / "rf_encoders.joblib"
_LABEL_CLASSES_PATH = _MODELS_DIR / "rf_label_classes.joblib"
_METRICS_PATH = _MODELS_DIR / "rf_metrics.json"

# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

_ITEM_TYPES = [
    "backpack", "charger", "earphones", "keys",
    "phone", "spectacles", "wallet", "water_bottle",
]
_WEATHER_TYPES = ["cold", "humid", "rainy", "sunny"]


def _prepare_features(
    df: pd.DataFrame,
    encoders: dict | None = None,
    scaler: StandardScaler | None = None,
    fit: bool = False,
) -> tuple[np.ndarray, dict, StandardScaler]:
    """One-hot encode categoricals, normalise time, return feature matrix."""

    if encoders is None:
        encoders = {}

    feature_df = df.copy()

    # Boolean → int
    feature_df["carrying_baggage"] = feature_df["carrying_baggage"].astype(int)

    # Normalise time_of_day to [0, 1]
    feature_df["time_of_day"] = feature_df["time_of_day"] / 24.0

    # One-hot encode item_type
    for it in _ITEM_TYPES:
        feature_df[f"item_{it}"] = (feature_df["item_type"] == it).astype(int)

    # One-hot encode weather_condition
    for wc in _WEATHER_TYPES:
        feature_df[f"weather_{wc}"] = (feature_df["weather_condition"] == wc).astype(int)

    # Build final feature column list
    numeric_cols = ["time_of_day", "day_of_week", "carrying_baggage", "fatigue_level"]
    item_cols = [f"item_{it}" for it in _ITEM_TYPES]
    weather_cols = [f"weather_{wc}" for wc in _WEATHER_TYPES]
    all_cols = numeric_cols + item_cols + weather_cols

    X = feature_df[all_cols].values.astype(float)

    if scaler is None:
        scaler = StandardScaler()

    if fit:
        X = scaler.fit_transform(X)
    else:
        X = scaler.transform(X)

    encoders["feature_columns"] = all_cols
    return X, encoders, scaler


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_predictor(df: pd.DataFrame) -> dict[str, Any]:
    """
    Train a Random Forest on the dataset.

    - 80 / 20 stratified split
    - ``n_estimators=200``, ``max_depth=15``
    - Persists model + evaluation artefacts
    """

    X, encoders, scaler = _prepare_features(df, fit=True)
    y = df["placed_location"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        random_state=42,
        n_jobs=-1,
        class_weight="balanced",
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    # --- Metrics ---
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    # Top-3 accuracy
    classes = clf.classes_
    top3_correct = 0
    for i, true_label in enumerate(y_test):
        top3_classes = [classes[j] for j in np.argsort(y_proba[i])[::-1][:3]]
        if true_label in top3_classes:
            top3_correct += 1
    top3_accuracy = top3_correct / len(y_test)

    # ROC-AUC (one-vs-rest, macro)
    lb = LabelBinarizer()
    y_test_bin = lb.fit_transform(y_test)
    try:
        roc_auc = roc_auc_score(y_test_bin, y_proba, average="macro", multi_class="ovr")
    except ValueError:
        roc_auc = 0.0

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred, labels=classes).tolist()

    # Per-class ROC data for frontend
    roc_curves = {}
    for idx, cls in enumerate(classes):
        y_cls = (y_test == cls).astype(int)
        scores = y_proba[:, idx]
        # Simple threshold-based points for visualization
        thresholds = np.linspace(0, 1, 50)
        tpr_list, fpr_list = [], []
        for t in thresholds:
            pred_pos = (scores >= t).astype(int)
            tp = np.sum((pred_pos == 1) & (y_cls == 1))
            fp = np.sum((pred_pos == 1) & (y_cls == 0))
            fn = np.sum((pred_pos == 0) & (y_cls == 1))
            tn = np.sum((pred_pos == 0) & (y_cls == 0))
            tpr_list.append(float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0)
            fpr_list.append(float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0)
        roc_curves[cls] = {"fpr": fpr_list, "tpr": tpr_list}

    # --- Persist ---
    joblib.dump(clf, _MODEL_PATH)
    joblib.dump(scaler, _SCALER_PATH)
    joblib.dump(encoders, _ENCODERS_PATH)
    joblib.dump(list(classes), _LABEL_CLASSES_PATH)

    metrics = {
        "accuracy": round(acc, 4),
        "top3_accuracy": round(top3_accuracy, 4),
        "roc_auc_macro": round(roc_auc, 4),
        "classification_report": report,
        "confusion_matrix": cm,
        "class_labels": list(classes),
        "roc_curves": roc_curves,
    }

    with open(_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"[LocationPredictor] accuracy={acc:.4f}, top3={top3_accuracy:.4f}, ROC-AUC={roc_auc:.4f}")
    return metrics


# ---------------------------------------------------------------------------
# Inference
# ---------------------------------------------------------------------------


def predict(features: dict) -> dict[str, Any]:
    """
    Predict placement probabilities for a single context vector.

    Parameters
    ----------
    features : dict
        Must contain: item_type, time_of_day, day_of_week,
        weather_condition, carrying_baggage, fatigue_level

    Returns
    -------
    dict with ``predicted_location``, ``probabilities`` (sorted desc),
    and ``top3`` list.
    """

    clf: RandomForestClassifier = joblib.load(_MODEL_PATH)
    scaler: StandardScaler = joblib.load(_SCALER_PATH)
    encoders: dict = joblib.load(_ENCODERS_PATH)
    classes: list[str] = joblib.load(_LABEL_CLASSES_PATH)

    df = pd.DataFrame([features])
    X, _, _ = _prepare_features(df, encoders=encoders, scaler=scaler, fit=False)

    proba = clf.predict_proba(X)[0]
    prob_dict = {cls: round(float(p), 4) for cls, p in zip(classes, proba)}

    # Sort descending by probability
    sorted_probs = dict(sorted(prob_dict.items(), key=lambda x: x[1], reverse=True))
    top3 = list(sorted_probs.keys())[:3]

    return {
        "predicted_location": top3[0],
        "probabilities": sorted_probs,
        "top3": top3,
    }
