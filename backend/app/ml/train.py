"""
MemoryVault AI — ML Training Orchestrator
==========================================
Phase 2, Step 2D

Runs the full training pipeline:
  1. Generate synthetic dataset (5,000 records)
  2. Train habit profiler  (PCA + K-Means)
  3. Train location predictor (Random Forest)
  4. Save all model artefacts + metrics

Run
---
    python -m app.ml.train
"""

from __future__ import annotations

import pandas as pd

from app.data.generate_dataset import generate as generate_dataset
from app.ml.habit_profiler import train_profiler
from app.ml.location_predictor import train_predictor


def main() -> None:
    print("=" * 60)
    print("MemoryVault AI — ML Training Pipeline")
    print("=" * 60)

    # Step 1: Generate dataset
    print("\n[1/3] Generating synthetic dataset ...")
    csv_path = generate_dataset(n=5_000, seed=42)

    # Step 2: Load data
    df = pd.read_csv(csv_path)
    print(f"       Loaded {len(df)} records with columns: {list(df.columns)}")

    # Step 3: Habit profiler (unsupervised)
    print("\n[2/3] Training Habit Profiler (PCA + K-Means) ...")
    habit_metrics = train_profiler(df)
    print(f"       Metrics: {habit_metrics}")

    # Step 4: Location predictor (supervised)
    print("\n[3/3] Training Location Predictor (Random Forest) ...")
    loc_metrics = train_predictor(df)
    print(f"       Accuracy       : {loc_metrics['accuracy']}")
    print(f"       Top-3 Accuracy : {loc_metrics['top3_accuracy']}")
    print(f"       ROC-AUC (macro): {loc_metrics['roc_auc_macro']}")

    print("\n" + "=" * 60)
    print("Training complete. All models saved to backend/app/ml/models/")
    print("=" * 60)


if __name__ == "__main__":
    main()
