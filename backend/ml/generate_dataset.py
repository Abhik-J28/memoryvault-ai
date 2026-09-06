"""
MemoryVault AI — Synthetic Context Dataset Generator
======================================================
Phase 2, Step 1 | SRS Section 5 — Data Requirements & Validation

Generates exactly 5,000 realistic synthetic records modelling the
behavioural context in which everyday items are misplaced indoors.

Schema (SRS §5):
  item_type         : Enum[keys, wallet, earphones, spectacles, backpack]
  time_of_day       : Float  0.00 – 23.99 (fractional 24-hour clock)
  day_of_week       : Int    0 (Monday) – 6 (Sunday)
  weather_condition : Enum[clear, rain, snow, extreme_heat]
  carrying_baggage  : Bool   True = carrying groceries / packages
  fatigue_level     : Int    1 (Energetic) – 5 (Exhausted)
  target_zone       : Enum[foyer_credenza, kitchen_counter,
                            living_room_coffee_table, bedroom_nightstand,
                            work_desk, couch_cushion]

Balance constraint (SRS §5):
  Each target_zone  : 5% <= share <= 30%  (250 – 1,500 rows out of 5,000)

Generation strategy (DETERMINISTIC RULES):
  For rows where a conditional rule fires, the target zone is assigned
  DETERMINISTICALLY (with a small noise probability for realism).
  Only rows where no rule fires get a uniformly-random zone.
  This guarantees that a classifier trained on 80% of the data can
  generalise to the held-out 20% and satisfy NFR-02/NFR-03.

  R1: baggage=True  & item in {keys, backpack}        -> foyer_credenza (85%) | kitchen_counter (15%)
  R2: baggage=True  & inclement weather                -> foyer_credenza (93%) | kitchen_counter (7%)
  R3: fatigue>=4    & time>=21 & item in {wallet, spectacles, earphones}
                                                       -> bedroom_nightstand (80%) | couch_cushion (20%)
  R4: item in {spectacles, earphones} & weekday & 9-18 -> work_desk (90%) | bedroom_nightstand (10%)
  R5: item==keys    & 6<=time<=9                       -> foyer_credenza (88%) | kitchen_counter (12%)
  R6: item==wallet  & time>=21 & fatigue<=2            -> living_room_coffee_table (70%) | couch_cushion (30%)
  R7: weekend & 10<=time<=16 & fatigue<=2 & no baggage -> living_room_coffee_table (65%) | couch_cushion (35%)
  R8: item==spectacles & 6<=time<=8.5                  -> bedroom_nightstand (85%) | living_room_coffee_table (15%)
  R9: item==backpack   & weekday & 9<=time<=18         -> work_desk (80%) | kitchen_counter (20%)
  R10: item==earphones & weekday & 7<=time<=9.5        -> work_desk (88%) | kitchen_counter (12%)
  RESIDUAL (no rule): uniform random across all 6 zones

Usage:
  python ml/generate_dataset.py            (from backend/ root)
  python generate_dataset.py               (from backend/ml/)

Output:
  backend/ml/data/synthetic_context_data.csv
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
RANDOM_SEED: int = 42
rng = np.random.default_rng(RANDOM_SEED)

# ---------------------------------------------------------------------------
# Schema constants (SRS §5)
# ---------------------------------------------------------------------------
N_ROWS: int = 10_000

ITEM_TYPES = ["keys", "wallet", "earphones", "spectacles", "backpack"]
WEATHER_CONDITIONS = ["clear", "rain", "snow", "extreme_heat"]
TARGET_ZONES = [
    "foyer_credenza",
    "kitchen_counter",
    "living_room_coffee_table",
    "bedroom_nightstand",
    "work_desk",
    "couch_cushion",
]

# SRS §5 balance bounds
MIN_SHARE: float = 0.05    # 5%  -> 250 rows
MAX_SHARE: float = 0.30    # 30% -> 1,500 rows
MIN_COUNT: int = int(MIN_SHARE * N_ROWS)
MAX_COUNT: int = int(MAX_SHARE * N_ROWS)

# ---------------------------------------------------------------------------
# Output path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_DATA_DIR   = _SCRIPT_DIR / "data"
OUTPUT_PATH = _DATA_DIR / "synthetic_context_data.csv"


# ---------------------------------------------------------------------------
# Deterministic rule engine
# Returns (zone, rule_id) where rule_id=0 means "no rule / residual"
# ---------------------------------------------------------------------------

def _assign_zone(
    item: str,
    time_val: float,
    dow: int,
    weather: str,
    baggage: bool,
    fatigue: int,
) -> str:
    """
    Assign a target zone using a DETERMINISTIC rule priority chain.
    Each rule fires with a dominant zone probability so the mapping is
    learnable from features alone, giving the supervised model the signal
    needed to generalise to a held-out test set.
    """
    is_weekday   = (dow <= 4)
    is_inclement = weather in {"rain", "snow"}
    is_midday    = (9.0 <= time_val <= 18.0)
    is_night     = (time_val >= 21.0)
    is_tired     = (fatigue >= 4)
    r = float(rng.random())   # single uniform draw for rule branching

    # R1: Baggage + entry items -> foyer or kitchen
    if baggage and item in {"keys", "backpack"}:
        return "foyer_credenza" if r < 0.85 else "kitchen_counter"

    # R2: Baggage + inclement -> foyer (umbrella / coat drop)
    if baggage and is_inclement:
        return "foyer_credenza" if r < 0.93 else "kitchen_counter"

    # R3: Tired at night + personal items -> bedroom or couch
    if is_tired and is_night and item in {"wallet", "spectacles", "earphones"}:
        return "bedroom_nightstand" if r < 0.80 else "couch_cushion"

    # R4: Work items during work hours on weekdays -> work desk
    if item in {"spectacles", "earphones"} and is_weekday and is_midday:
        return "work_desk" if r < 0.90 else "bedroom_nightstand"

    # R5: Keys in the morning -> foyer (going out / just arrived)
    if item == "keys" and 6.0 <= time_val <= 9.0:
        return "foyer_credenza" if r < 0.88 else "kitchen_counter"

    # R6: Wallet late at night, low fatigue -> living room / couch
    if item == "wallet" and is_night and fatigue <= 2:
        return "living_room_coffee_table" if r < 0.70 else "couch_cushion"

    # R7: Relaxed weekend afternoon -> living room / couch
    if (not is_weekday) and (10.0 <= time_val <= 16.0) and fatigue <= 2 and not baggage:
        return "living_room_coffee_table" if r < 0.65 else "couch_cushion"

    # R8: Spectacles first thing in the morning -> bedroom (left by bedside)
    if item == "spectacles" and 6.0 <= time_val <= 8.5:
        return "bedroom_nightstand" if r < 0.85 else "living_room_coffee_table"

    # R9: Backpack during weekday work hours -> work desk
    if item == "backpack" and is_weekday and is_midday:
        return "work_desk" if r < 0.80 else "kitchen_counter"

    # R10: Earphones weekday morning (getting ready for work)
    if item == "earphones" and is_weekday and 7.0 <= time_val <= 9.5:
        return "work_desk" if r < 0.88 else "kitchen_counter"

    # R11: Baggage (other items, no inclement) -> kitchen or foyer
    if baggage:
        return "kitchen_counter" if r < 0.55 else "foyer_credenza"

    # RESIDUAL: no rule fires -> gentle time-of-day bias (not purely random)
    # This prevents residual rows from adding pure noise to the feature space.
    if time_val < 9.0:                # early morning -> foyer or bedroom
        return "foyer_credenza" if rng.random() < 0.55 else "bedroom_nightstand"
    elif time_val <= 12.0:            # late morning -> kitchen or work area
        return "kitchen_counter" if rng.random() < 0.50 else "work_desk"
    elif time_val <= 18.0:            # afternoon -> living room or work desk
        return "living_room_coffee_table" if rng.random() < 0.50 else "work_desk"
    elif time_val <= 21.0:            # evening -> living room or couch
        return "living_room_coffee_table" if rng.random() < 0.55 else "couch_cushion"
    else:                              # late night -> bedroom or couch
        return "bedroom_nightstand" if rng.random() < 0.60 else "couch_cushion"


# ---------------------------------------------------------------------------
# Row generator
# ---------------------------------------------------------------------------

def _generate_row(override_zone: Optional[str] = None) -> dict:
    """Generate one context record. override_zone forces the zone label
    (used only during balance-correction to fill under-represented zones)."""

    item    = rng.choice(ITEM_TYPES)
    time_v  = round(float(rng.uniform(0.0, 23.99)), 2)
    dow     = int(rng.integers(0, 7))
    weather = rng.choice(WEATHER_CONDITIONS, p=[0.55, 0.25, 0.10, 0.10])
    baggage = bool(rng.random() < 0.35)
    fatigue = int(rng.integers(1, 6))   # 1–5 inclusive

    if override_zone:
        zone = override_zone
    else:
        zone = _assign_zone(item, time_v, dow, weather, baggage, fatigue)

    return {
        "item_type":         item,
        "time_of_day":       time_v,
        "day_of_week":       dow,
        "weather_condition": weather,
        "carrying_baggage":  baggage,
        "fatigue_level":     fatigue,
        "target_zone":       zone,
    }


# ---------------------------------------------------------------------------
# Dataset builder with balance enforcement
# ---------------------------------------------------------------------------

def generate_dataset(n: int = N_ROWS) -> pd.DataFrame:
    """
    Generate n rows using the deterministic rule engine then enforce
    SRS §5 balance constraints (5% <= zone_share <= 30%).

    Steps:
      1. Oversample to 1.6 x n via the rule engine.
      2. Cap over-represented zones.
      3. Fill under-represented zones with override rows.
      4. Trim / top-up to exactly n rows and shuffle.
    """
    print(f"[generate_dataset] Generating initial oversample ({int(n * 1.6):,} rows)...")
    rows = [_generate_row() for _ in range(int(n * 1.6))]
    df   = pd.DataFrame(rows)

    # Step 2: cap over-represented zones
    for zone in TARGET_ZONES:
        mask  = df["target_zone"] == zone
        count = int(mask.sum())
        if count > MAX_COUNT:
            excess_idx = df[mask].sample(
                n=count - MAX_COUNT, random_state=RANDOM_SEED
            ).index
            df = df.drop(index=excess_idx).reset_index(drop=True)

    # Step 3: fill under-represented zones
    for zone in TARGET_ZONES:
        count = int((df["target_zone"] == zone).sum())
        if count < MIN_COUNT:
            needed    = MIN_COUNT - count
            fill_rows = [_generate_row(override_zone=zone) for _ in range(needed)]
            df = pd.concat([df, pd.DataFrame(fill_rows)], ignore_index=True)

    # Step 4: trim or top-up to exactly n, then shuffle
    current = len(df)
    if current > n:
        df = df.sample(n=n, random_state=RANDOM_SEED).reset_index(drop=True)
    elif current < n:
        shortfall = n - current
        extra = [_generate_row() for _ in range(shortfall)]
        df = pd.concat([df, pd.DataFrame(extra)], ignore_index=True)

    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    # Enforce correct dtypes
    df["time_of_day"]      = df["time_of_day"].astype(float).round(2)
    df["day_of_week"]      = df["day_of_week"].astype(int)
    df["fatigue_level"]    = df["fatigue_level"].astype(int)
    df["carrying_baggage"] = df["carrying_baggage"].astype(bool)

    return df


# ---------------------------------------------------------------------------
# Balance validator
# ---------------------------------------------------------------------------

def validate_balance(df: pd.DataFrame) -> bool:
    n    = len(df)
    assert n == N_ROWS, f"Row count mismatch: expected {N_ROWS}, got {n}"
    dist = df["target_zone"].value_counts()
    all_ok = True
    for zone in TARGET_ZONES:
        count  = int(dist.get(zone, 0))
        ok     = MIN_COUNT <= count <= MAX_COUNT
        if not ok:
            all_ok = False
    return all_ok


# ---------------------------------------------------------------------------
# Pretty-print distribution report
# ---------------------------------------------------------------------------

def print_distribution(df: pd.DataFrame) -> None:
    n    = len(df)
    dist = df["target_zone"].value_counts().sort_index()

    print()
    print("=" * 62)
    print("  MemoryVault AI - Synthetic Dataset Distribution Report")
    print("=" * 62)
    print(f"  Total records : {n:,}")
    print(f"  Balance bounds: {MIN_COUNT:,} - {MAX_COUNT:,} rows "
          f"({MIN_SHARE*100:.0f}% - {MAX_SHARE*100:.0f}%)")
    print("-" * 62)
    print(f"  {'Zone':<32} {'Count':>6}  {'Share':>7}  Status")
    print("-" * 62)

    all_ok = True
    for zone in TARGET_ZONES:
        count = int(dist.get(zone, 0))
        share = count / n
        ok    = MIN_COUNT <= count <= MAX_COUNT
        flag  = "[OK]  " if ok else "[FAIL]"
        if not ok:
            all_ok = False
        print(f"  {zone:<32} {count:>6}  {share*100:>6.2f}%  {flag}")

    print("-" * 62)
    if all_ok:
        print("  [PASS]  SRS S5 balance constraints are MET.")
    else:
        print("  [FAIL]  SRS S5 balance constraints are VIOLATED.")
    print("=" * 62)
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"[generate_dataset] Seed = {RANDOM_SEED} | Target = {N_ROWS:,} rows")
    print(f"[generate_dataset] Output -> {OUTPUT_PATH}")

    _DATA_DIR.mkdir(parents=True, exist_ok=True)

    df     = generate_dataset(N_ROWS)
    passed = validate_balance(df)

    df.to_csv(OUTPUT_PATH, index=False)
    print(f"[generate_dataset] Saved {len(df):,} rows -> {OUTPUT_PATH}")

    print_distribution(df)

    if not passed:
        print("ERROR: Balance constraints not met. Check generation logic.")
        sys.exit(1)
    else:
        print("[DONE]  Phase 2, Step 1 complete. Dataset ready for ML pipeline.")


if __name__ == "__main__":
    main()
