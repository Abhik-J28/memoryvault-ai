"""
MemoryVault AI — Habit Profiler (Unsupervised ML)
==================================================
Phase 2, Step 2B

Uses PCA for dimensionality reduction and K-Means for clustering
to discover latent behavioural archetypes from user placement data.

Exports
-------
- ``train_profiler(df)`` — fit PCA + KMeans, save models, return metrics
- ``get_cluster(features)`` — predict cluster label for a feature vector
- ``get_pca_coords(features)`` — project a feature vector to 2D PCA space
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import LabelEncoder, StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_MODELS_DIR = Path(__file__).resolve().parent / "models"
_MODELS_DIR.mkdir(parents=True, exist_ok=True)

_SCALER_PATH = _MODELS_DIR / "habit_scaler.joblib"
_PCA_PATH = _MODELS_DIR / "habit_pca.joblib"
_KMEANS_PATH = _MODELS_DIR / "habit_kmeans.joblib"
_ENCODERS_PATH = _MODELS_DIR / "habit_encoders.joblib"
_METRICS_PATH = _MODELS_DIR / "habit_metrics.json"

# ---------------------------------------------------------------------------
# Feature preparation
# ---------------------------------------------------------------------------

_CATEGORICAL_COLS = ["item_type", "weather_condition"]
_NUMERIC_COLS = ["time_of_day", "day_of_week", "carrying_baggage", "fatigue_level"]


def _prepare_features(
    df: pd.DataFrame,
    encoders: dict[str, LabelEncoder] | None = None,
    scaler: StandardScaler | None = None,
    fit: bool = False,
) -> tuple[np.ndarray, dict[str, LabelEncoder], StandardScaler]:
    """Encode categoricals, scale numerics, return feature matrix."""

    if encoders is None:
        encoders = {}

    feature_df = df.copy()

    # Convert boolean carrying_baggage to int
    feature_df["carrying_baggage"] = feature_df["carrying_baggage"].astype(int)

    # Label-encode categoricals
    for col in _CATEGORICAL_COLS:
        if fit or col not in encoders:
            enc = LabelEncoder()
            feature_df[col] = enc.fit_transform(feature_df[col])
            encoders[col] = enc
        else:
            feature_df[col] = encoders[col].transform(feature_df[col])

    all_cols = _CATEGORICAL_COLS + _NUMERIC_COLS
    X = feature_df[all_cols].values.astype(float)

    if scaler is None:
        scaler = StandardScaler()

    if fit:
        X = scaler.fit_transform(X)
    else:
        X = scaler.transform(X)

    return X, encoders, scaler


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------


def train_profiler(df: pd.DataFrame) -> dict[str, Any]:
    """
    Fit PCA (→ 2 components) + K-Means on the dataset.

    Selects optimal *k* from [3, 4, 5, 6] via silhouette score.
    Persists all artifacts to ``backend/app/ml/models/``.
    Returns a metrics dict.
    """

    X, encoders, scaler = _prepare_features(df, fit=True)

    # --- PCA ---
    pca = PCA(n_components=2, random_state=42)
    X_pca = pca.fit_transform(X)

    # --- K-Means (auto-select k) ---
    best_k, best_score, best_model = 4, -1.0, None
    for k in [3, 4, 5, 6]:
        km = KMeans(n_clusters=k, random_state=42, n_init=10, max_iter=300)
        labels = km.fit_predict(X_pca)
        score = silhouette_score(X_pca, labels)
        if score > best_score:
            best_k, best_score, best_model = k, score, km

    assert best_model is not None
    labels = best_model.predict(X_pca)

    # --- Persist ---
    joblib.dump(scaler, _SCALER_PATH)
    joblib.dump(pca, _PCA_PATH)
    joblib.dump(best_model, _KMEANS_PATH)
    joblib.dump(encoders, _ENCODERS_PATH)

    metrics = {
        "n_clusters": best_k,
        "silhouette_score": round(best_score, 4),
        "explained_variance_ratio": [round(v, 4) for v in pca.explained_variance_ratio_.tolist()],
        "inertia": round(best_model.inertia_, 2),
    }

    with open(_METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    # Build cluster data for frontend visualization
    cluster_data = {
        "points": [
            {
                "x": round(float(X_pca[i, 0]), 4),
                "y": round(float(X_pca[i, 1]), 4),
                "cluster": int(labels[i]),
            }
            for i in range(len(X_pca))
        ],
        "centroids": [
            {
                "x": round(float(c[0]), 4),
                "y": round(float(c[1]), 4),
                "cluster": idx,
            }
            for idx, c in enumerate(best_model.cluster_centers_)
        ],
    }
    cluster_path = _MODELS_DIR / "cluster_data.json"
    with open(cluster_path, "w", encoding="utf-8") as f:
        json.dump(cluster_data, f)

    print(f"[HabitProfiler] k={best_k}, silhouette={best_score:.4f}")
    return metrics


# ---------------------------------------------------------------------------
# Inference helpers
# ---------------------------------------------------------------------------


def _load_models():
    scaler: StandardScaler = joblib.load(_SCALER_PATH)
    pca: PCA = joblib.load(_PCA_PATH)
    kmeans: KMeans = joblib.load(_KMEANS_PATH)
    encoders: dict[str, LabelEncoder] = joblib.load(_ENCODERS_PATH)
    return scaler, pca, kmeans, encoders


def get_cluster(features: dict) -> int:
    """Return the cluster id for a single feature dict."""
    scaler, pca, kmeans, encoders = _load_models()
    df = pd.DataFrame([features])
    X, _, _ = _prepare_features(df, encoders=encoders, scaler=scaler, fit=False)
    X_pca = pca.transform(X)
    return int(kmeans.predict(X_pca)[0])


def get_pca_coords(features: dict) -> list[float]:
    """Return [x, y] PCA coordinates for a single feature dict."""
    scaler, pca, _, encoders = _load_models()
    df = pd.DataFrame([features])
    X, _, _ = _prepare_features(df, encoders=encoders, scaler=scaler, fit=False)
    coords = pca.transform(X)[0]
    return [round(float(coords[0]), 4), round(float(coords[1]), 4)]
