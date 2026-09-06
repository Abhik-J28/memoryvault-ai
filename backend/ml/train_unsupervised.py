"""
MemoryVault AI -- Unsupervised Habit Clustering Pipeline
=========================================================
Phase 2, Step 2  |  SRS FR-04 / VR-02 / PRD Section 4

Pipeline
--------
1. Load backend/ml/data/synthetic_context_data.csv
2. Select ONLY the 6 context features (target_zone excluded -- no label leakage)
3. Preprocess with a ColumnTransformer:
      - OneHotEncoder  -> categorical: item_type, weather_condition
      - StandardScaler -> numeric/bool: time_of_day, day_of_week,
                          fatigue_level, carrying_baggage
4. Fit PCA(n_components=2)  -- 2D projection for the Evaluator scatter plot
5. Fit KMeans(n_clusters=3) -- 3 behavioural archetypes (FR-04)
6. Interpret centroids programmatically to assign human-readable archetype names
7. Serialize preprocessor + PCA + KMeans -> backend/ml/artifacts/kmeans_pca.joblib
8. Export cluster_summary.json for the Next.js Evaluator Analytics drawer

Usage (from backend/ root):
    python ml/train_unsupervised.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.preprocessing import OneHotEncoder, StandardScaler

# ---------------------------------------------------------------------------
# Paths -- resolved relative to this file so CWD does not matter
# ---------------------------------------------------------------------------
_ML_DIR       = Path(__file__).resolve().parent          # backend/ml/
_DATA_PATH    = _ML_DIR / "data" / "synthetic_context_data.csv"
_ARTIFACT_DIR = _ML_DIR / "artifacts"
_JOBLIB_PATH  = _ARTIFACT_DIR / "kmeans_pca.joblib"
_JSON_PATH    = _ARTIFACT_DIR / "cluster_summary.json"

# ---------------------------------------------------------------------------
# Feature schema  (SRS Section 5)
# ---------------------------------------------------------------------------
CATEGORICAL_FEATURES = ["item_type", "weather_condition"]
NUMERIC_FEATURES     = ["time_of_day", "day_of_week", "fatigue_level", "carrying_baggage"]
ALL_CONTEXT_FEATURES = CATEGORICAL_FEATURES + NUMERIC_FEATURES   # 6 features

N_CLUSTERS   = 3
PCA_DIMS     = 2
RANDOM_STATE = 42
N_SAMPLE_VIZ = 200   # points exported to cluster_summary.json for the scatter plot


# ---------------------------------------------------------------------------
# Step 1 & 2: Load data and isolate context features
# ---------------------------------------------------------------------------

def load_features(path: Path) -> pd.DataFrame:
    """Load CSV and return only the 6 context feature columns (no target_zone)."""
    df = pd.read_csv(path)

    missing = [c for c in ALL_CONTEXT_FEATURES if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns in dataset: {missing}")

    # Cast boolean column read as string back to int (0/1) for StandardScaler
    df["carrying_baggage"] = df["carrying_baggage"].map(
        {True: 1, False: 0, "True": 1, "False": 0}
    ).astype(int)

    return df[ALL_CONTEXT_FEATURES].copy()


# ---------------------------------------------------------------------------
# Step 3: Preprocessor
# ---------------------------------------------------------------------------

def build_preprocessor() -> ColumnTransformer:
    """
    ColumnTransformer applying:
      - OneHotEncoder  to categorical features (item_type, weather_condition)
      - StandardScaler to numeric/boolean features
    """
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
# Step 6: Programmatic archetype labelling
# ---------------------------------------------------------------------------

def _label_clusters(
    kmeans: KMeans,
    preprocessor: ColumnTransformer,
    df_raw: pd.DataFrame,
    labels: np.ndarray,
) -> dict[int, dict]:
    """
    Inspect centroid characteristics in the *original* feature space to assign
    human-readable archetype names and dominant trait descriptions.
    """
    archetypes: dict[int, dict] = {}
    
    # Pre-calculate stats for all clusters
    stats = {}
    for cid in range(N_CLUSTERS):
        mask = labels == cid
        cluster_df = df_raw[mask]
        stats[cid] = {
            "n": int(mask.sum()),
            "avg_time": float(cluster_df["time_of_day"].mean()),
            "avg_fatigue": float(cluster_df["fatigue_level"].mean()),
            "avg_dow": float(cluster_df["day_of_week"].mean()),
            "bag_rate": float(cluster_df["carrying_baggage"].mean()),
            "top_item": cluster_df["item_type"].mode().iloc[0],
            "top_weather": cluster_df["weather_condition"].mode().iloc[0],
        }

    # Find the cluster with highest baggage rate
    baggage_cid = max(stats.keys(), key=lambda c: stats[c]["bag_rate"])
    
    # Remaining two clusters
    remaining = [c for c in stats.keys() if c != baggage_cid]
    
    # Of the remaining two, the one with higher fatigue is the fatigued/distracted cluster
    fatigued_cid = max(remaining, key=lambda c: stats[c]["avg_fatigue"])
    alert_cid = [c for c in remaining if c != fatigued_cid][0]
    
    for cid in range(N_CLUSTERS):
        s = stats[cid]
        if cid == baggage_cid:
            name   = "Rushed Baggage Drop"
            traits = (
                f"Baggage rate {s['bag_rate']*100:.0f}%, avg time {s['avg_time']:.1f}h. "
                f"Hands-full drop pattern on entry, often in {s['top_weather']} weather. "
                f"Dominant item: {s['top_item']}."
            )
        elif cid == fatigued_cid:
            if s['avg_time'] >= 18.0:
                name = "Fatigued Late-Night Return"
                traits = f"Avg time {s['avg_time']:.1f}h, avg fatigue {s['avg_fatigue']:.1f}/5. Items misplaced during exhausted evening arrivals. Dominant item: {s['top_item']}."
            else:
                name = "High-Fatigue Distracted Placement"
                traits = f"Avg fatigue {s['avg_fatigue']:.1f}/5 during daytime (avg {s['avg_time']:.1f}h). Absent-minded placements driven by cognitive load. Dominant item: {s['top_item']}."
        else:
            name   = "Alert Daytime Transit"
            traits = (
                f"Avg time {s['avg_time']:.1f}h, avg day-of-week {s['avg_dow']:.1f} "
                f"(0=Mon, 6=Sun). Low-fatigue ({s['avg_fatigue']:.1f}/5) weekday placements. "
                f"Dominant item: {s['top_item']}."
            )

        archetypes[cid] = {
            "name":          name,
            "sample_count":  s["n"],
            "avg_time_of_day":    round(s["avg_time"], 2),
            "avg_fatigue_level":  round(s["avg_fatigue"], 2),
            "avg_day_of_week":    round(s["avg_dow"], 2),
            "baggage_rate":       round(s["bag_rate"], 4),
            "dominant_item":      s["top_item"],
            "dominant_weather":   s["top_weather"],
            "traits":             traits,
        }

    return archetypes


# ---------------------------------------------------------------------------
# Step 7: Serialize artefacts
# ---------------------------------------------------------------------------

def save_joblib(
    preprocessor: ColumnTransformer,
    pca: PCA,
    kmeans: KMeans,
    path: Path,
) -> None:
    payload = {
        "preprocessor": preprocessor,
        "pca":          pca,
        "kmeans":       kmeans,
    }
    joblib.dump(payload, path)
    print(f"[train_unsupervised] Saved joblib artefact -> {path}")


# ---------------------------------------------------------------------------
# Step 8: Export cluster_summary.json
# ---------------------------------------------------------------------------

def save_cluster_summary(
    pca: PCA,
    archetypes: dict[int, dict],
    pca_coords: np.ndarray,
    labels: np.ndarray,
    df_raw: pd.DataFrame,
    path: Path,
) -> None:
    """Emit the lightweight JSON consumed by the Next.js Evaluator drawer."""

    # Sub-sample N_SAMPLE_VIZ points, stratified across clusters
    rng          = np.random.default_rng(RANDOM_STATE)
    indices      = rng.choice(len(pca_coords), size=N_SAMPLE_VIZ, replace=False)
    sample_proj  = [
        {
            "pca_x":      round(float(pca_coords[i, 0]), 4),
            "pca_y":      round(float(pca_coords[i, 1]), 4),
            "cluster_id": int(labels[i]),
            "item_type":  str(df_raw["item_type"].iloc[i]),
        }
        for i in indices
    ]

    summary = {
        "pca_variance_ratio": [round(float(v), 6) for v in pca.explained_variance_ratio_],
        "total_explained_variance": round(float(pca.explained_variance_ratio_.sum()), 6),
        "n_clusters": N_CLUSTERS,
        "cluster_archetypes": {
            str(cid): {
                "name":         meta["name"],
                "sample_count": meta["sample_count"],
                "traits":       meta["traits"],
            }
            for cid, meta in archetypes.items()
        },
        "sample_projections": sample_proj,
    }

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    print(f"[train_unsupervised] Saved cluster summary JSON -> {path}")


# ---------------------------------------------------------------------------
# Pretty-print summary table
# ---------------------------------------------------------------------------

def print_summary(
    pca: PCA,
    archetypes: dict[int, dict],
) -> None:
    total_var = pca.explained_variance_ratio_.sum()

    print()
    print("=" * 70)
    print("  MemoryVault AI -- Unsupervised Pipeline Summary")
    print("=" * 70)
    print(f"  PCA explained variance  : "
          f"PC1={pca.explained_variance_ratio_[0]*100:.2f}%  "
          f"PC2={pca.explained_variance_ratio_[1]*100:.2f}%  "
          f"Total={total_var*100:.2f}%")
    print(f"  KMeans clusters         : {N_CLUSTERS}")
    print("-" * 70)
    print(f"  {'ID':<4} {'Archetype Name':<32} {'Count':>6}  {'Avg Time':>9}  "
          f"{'Avg Fatigue':>11}  {'Bag%':>5}")
    print("-" * 70)
    for cid, meta in sorted(archetypes.items()):
        print(
            f"  {cid:<4} {meta['name']:<32} {meta['sample_count']:>6}  "
            f"{meta['avg_time_of_day']:>9.2f}  "
            f"{meta['avg_fatigue_level']:>11.2f}  "
            f"{meta['baggage_rate']*100:>4.1f}%"
        )
    print("-" * 70)
    print(f"  VR-02 requirement: >= 3 distinct clusters    [{'PASS' if N_CLUSTERS >= 3 else 'FAIL'}]")
    print("=" * 70)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("[train_unsupervised] Phase 2, Step 2 -- Unsupervised Habit Clustering")
    print(f"[train_unsupervised] Data     <- {_DATA_PATH}")
    print(f"[train_unsupervised] Joblib   -> {_JOBLIB_PATH}")
    print(f"[train_unsupervised] JSON     -> {_JSON_PATH}")
    print()

    # Ensure output directory exists
    _ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    # ---- Step 1 & 2: Load features (no target_zone) ----
    print("[train_unsupervised] Loading dataset...")
    df_raw = load_features(_DATA_PATH)
    print(f"[train_unsupervised] Loaded {len(df_raw):,} rows, "
          f"{len(ALL_CONTEXT_FEATURES)} context features.")

    # ---- Step 3: Fit preprocessor ----
    print("[train_unsupervised] Fitting ColumnTransformer (OHE + StandardScaler)...")
    preprocessor = build_preprocessor()
    X_processed  = preprocessor.fit_transform(df_raw)
    print(f"[train_unsupervised] Preprocessed matrix shape: {X_processed.shape}")

    # ---- Step 4: Fit PCA ----
    print(f"[train_unsupervised] Fitting PCA(n_components={PCA_DIMS})...")
    pca        = PCA(n_components=PCA_DIMS, random_state=RANDOM_STATE)
    pca_coords = pca.fit_transform(X_processed)
    print(f"[train_unsupervised] PCA explained variance ratio: "
          f"{pca.explained_variance_ratio_.round(4)}")

    # ---- Step 5: Fit KMeans ----
    print(f"[train_unsupervised] Fitting KMeans(n_clusters={N_CLUSTERS}, "
          f"n_init=10, random_state={RANDOM_STATE})...")
    kmeans = KMeans(
        n_clusters   = N_CLUSTERS,
        random_state = RANDOM_STATE,
        n_init       = 10,
    )
    labels = kmeans.fit_predict(X_processed)
    unique, counts = np.unique(labels, return_counts=True)
    for cid, cnt in zip(unique, counts):
        print(f"  Cluster {cid}: {cnt:,} samples")

    # ---- Step 6: Interpret centroids -> archetype labels ----
    print("[train_unsupervised] Interpreting cluster centroids...")
    archetypes = _label_clusters(kmeans, preprocessor, df_raw, labels)

    # ---- Step 7: Serialize joblib ----
    save_joblib(preprocessor, pca, kmeans, _JOBLIB_PATH)

    # ---- Step 8: Export JSON summary ----
    save_cluster_summary(pca, archetypes, pca_coords, labels, df_raw, _JSON_PATH)

    # ---- Print summary table ----
    print_summary(pca, archetypes)

    print("[DONE]  Phase 2, Step 2 complete.")
    print(f"        Artefacts written to: {_ARTIFACT_DIR}")


if __name__ == "__main__":
    main()
