"""
MemoryVault AI — Synthetic Dataset Generator
=============================================
Phase 2, Step 2A

Generates ~5,000 synthetic placement records with realistic conditional
distributions.  Each record captures the situational context at the
moment a user placed an everyday item somewhere in a typical Indian
residential flat.

Output
------
backend/app/data/dataset.csv

Run
---
    python -m app.data.generate_dataset
"""

from __future__ import annotations

import csv
import os
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ITEMS: list[str] = [
    "keys",
    "wallet",
    "phone",
    "spectacles",
    "earphones",
    "backpack",
    "water_bottle",
    "charger",
]

LOCATIONS: list[str] = [
    "entrance_hallway",
    "living_room",
    "kitchen",
    "bedroom",
    "study_room",
    "bathroom",
    "balcony",
    "dining_area",
]

WEATHER_CONDITIONS: list[str] = ["sunny", "rainy", "cold", "humid"]

NUM_RECORDS: int = 5_000

# ---------------------------------------------------------------------------
# Conditional probability tables
# ---------------------------------------------------------------------------
# Each item has a base distribution over locations.  Certain contextual
# conditions shift the probabilities to emulate realistic human habits.


def _base_distribution(item: str) -> dict[str, float]:
    """Return a baseline probability vector for *item* across all locations."""
    distributions: dict[str, dict[str, float]] = {
        "keys": {
            "entrance_hallway": 0.35,
            "living_room": 0.15,
            "kitchen": 0.10,
            "bedroom": 0.15,
            "study_room": 0.05,
            "bathroom": 0.02,
            "balcony": 0.03,
            "dining_area": 0.15,
        },
        "wallet": {
            "entrance_hallway": 0.20,
            "living_room": 0.20,
            "kitchen": 0.05,
            "bedroom": 0.30,
            "study_room": 0.10,
            "bathroom": 0.02,
            "balcony": 0.03,
            "dining_area": 0.10,
        },
        "phone": {
            "entrance_hallway": 0.05,
            "living_room": 0.25,
            "kitchen": 0.10,
            "bedroom": 0.25,
            "study_room": 0.15,
            "bathroom": 0.08,
            "balcony": 0.05,
            "dining_area": 0.07,
        },
        "spectacles": {
            "entrance_hallway": 0.05,
            "living_room": 0.15,
            "kitchen": 0.05,
            "bedroom": 0.30,
            "study_room": 0.25,
            "bathroom": 0.08,
            "balcony": 0.02,
            "dining_area": 0.10,
        },
        "earphones": {
            "entrance_hallway": 0.08,
            "living_room": 0.22,
            "kitchen": 0.05,
            "bedroom": 0.28,
            "study_room": 0.20,
            "bathroom": 0.05,
            "balcony": 0.07,
            "dining_area": 0.05,
        },
        "backpack": {
            "entrance_hallway": 0.40,
            "living_room": 0.20,
            "kitchen": 0.02,
            "bedroom": 0.25,
            "study_room": 0.08,
            "bathroom": 0.01,
            "balcony": 0.02,
            "dining_area": 0.02,
        },
        "water_bottle": {
            "entrance_hallway": 0.08,
            "living_room": 0.15,
            "kitchen": 0.30,
            "bedroom": 0.15,
            "study_room": 0.12,
            "bathroom": 0.05,
            "balcony": 0.05,
            "dining_area": 0.10,
        },
        "charger": {
            "entrance_hallway": 0.03,
            "living_room": 0.20,
            "kitchen": 0.05,
            "bedroom": 0.35,
            "study_room": 0.25,
            "bathroom": 0.02,
            "balcony": 0.02,
            "dining_area": 0.08,
        },
    }
    return distributions[item]


def _apply_contextual_shifts(
    dist: dict[str, float],
    item: str,
    time_of_day: float,
    day_of_week: int,
    weather: str,
    carrying_baggage: bool,
    fatigue_level: int,
) -> dict[str, float]:
    """Mutate *dist* in-place based on contextual conditions."""

    # Rule 1: Evening return with baggage → keys/wallet more likely at entrance
    if carrying_baggage and 17.0 <= time_of_day <= 22.0:
        if item in ("keys", "wallet", "backpack"):
            dist["entrance_hallway"] += 0.20
            dist["bedroom"] -= 0.10
            dist["living_room"] -= 0.10

    # Rule 2: Late night + high fatigue → items left in bedroom
    if time_of_day >= 22.0 or time_of_day < 5.0:
        if fatigue_level >= 4:
            dist["bedroom"] += 0.20
            dist["entrance_hallway"] -= 0.10
            dist["kitchen"] -= 0.05
            dist["living_room"] -= 0.05

    # Rule 3: Study hours + spectacles/earphones/charger → study room boost
    if 9.0 <= time_of_day <= 17.0 and item in ("spectacles", "earphones", "charger"):
        dist["study_room"] += 0.15
        dist["bedroom"] -= 0.08
        dist["living_room"] -= 0.07

    # Rule 4: Rainy weather → entrance hallway boost (drying area near door)
    if weather == "rainy":
        if item in ("keys", "wallet", "backpack"):
            dist["entrance_hallway"] += 0.10
            dist["balcony"] -= 0.05
            dist["dining_area"] -= 0.05

    # Rule 5: Morning rush (6-9 AM) → kitchen for water_bottle/phone
    if 6.0 <= time_of_day <= 9.0:
        if item in ("water_bottle", "phone"):
            dist["kitchen"] += 0.15
            dist["bedroom"] -= 0.10
            dist["study_room"] -= 0.05

    # Rule 6: Weekend + low fatigue → living_room boost (leisure time)
    if day_of_week >= 5 and fatigue_level <= 2:
        dist["living_room"] += 0.10
        dist["study_room"] -= 0.05
        dist["entrance_hallway"] -= 0.05

    # Rule 7: High fatigue + bathroom items
    if fatigue_level >= 4 and item in ("spectacles", "phone"):
        dist["bathroom"] += 0.10
        dist["living_room"] -= 0.05
        dist["study_room"] -= 0.05

    # Clamp negatives and re-normalise
    for loc in dist:
        if dist[loc] < 0.01:
            dist[loc] = 0.01
    total = sum(dist.values())
    for loc in dist:
        dist[loc] /= total

    return dist


# ---------------------------------------------------------------------------
# Record generation
# ---------------------------------------------------------------------------


def _generate_time_of_day() -> float:
    """Sample a time with realistic multi-modal peaks."""
    mode = random.choices(
        ["morning_rush", "midday", "evening_return", "late_night", "uniform"],
        weights=[0.20, 0.15, 0.30, 0.15, 0.20],
    )[0]

    if mode == "morning_rush":
        t = random.gauss(7.5, 1.0)
    elif mode == "midday":
        t = random.gauss(13.0, 1.5)
    elif mode == "evening_return":
        t = random.gauss(19.0, 1.5)
    elif mode == "late_night":
        t = random.gauss(23.0, 1.0)
    else:
        t = random.uniform(0.0, 23.99)

    return round(max(0.0, min(23.99, t)), 2)


def _generate_record() -> dict:
    item = random.choice(ITEMS)
    time_of_day = _generate_time_of_day()
    day_of_week = random.choices(range(7), weights=[1.2, 1.2, 1.2, 1.2, 1.2, 0.9, 0.9])[0]
    weather = random.choices(
        WEATHER_CONDITIONS, weights=[0.40, 0.25, 0.20, 0.15]
    )[0]
    carrying_baggage = random.choices([True, False], weights=[0.45, 0.55])[0]
    fatigue_level = random.choices(
        [1, 2, 3, 4, 5], weights=[0.15, 0.25, 0.30, 0.20, 0.10]
    )[0]

    # Build conditional probability distribution
    dist = _base_distribution(item)
    dist = _apply_contextual_shifts(
        dist, item, time_of_day, day_of_week, weather, carrying_baggage, fatigue_level
    )

    placed_location = random.choices(LOCATIONS, weights=[dist[l] for l in LOCATIONS])[0]

    return {
        "item_type": item,
        "time_of_day": time_of_day,
        "day_of_week": day_of_week,
        "weather_condition": weather,
        "carrying_baggage": carrying_baggage,
        "fatigue_level": fatigue_level,
        "placed_location": placed_location,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def generate(n: int = NUM_RECORDS, seed: int = 42) -> Path:
    """Generate *n* records and write to ``dataset.csv``. Returns the path."""
    random.seed(seed)

    output_dir = Path(__file__).resolve().parent
    output_path = output_dir / "dataset.csv"

    fieldnames = [
        "item_type",
        "time_of_day",
        "day_of_week",
        "weather_condition",
        "carrying_baggage",
        "fatigue_level",
        "placed_location",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for _ in range(n):
            writer.writerow(_generate_record())

    print(f"[DataGen] Wrote {n} records -> {output_path}")
    return output_path


if __name__ == "__main__":
    generate()
