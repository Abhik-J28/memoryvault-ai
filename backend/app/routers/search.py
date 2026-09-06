"""
MemoryVault AI — Search Router
================================
Phase 3, Step 3  |  SRS FR-04 / FR-08

Exposes the POST /api/v1/router/search endpoint to predict the likely
locations of a lost item based on user context, and computes the optimal
A*-inspired search route through the household.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.spatial.router import calculate_optimal_route

# ---------------------------------------------------------------------------
# Load ML artifacts
# ---------------------------------------------------------------------------
_ROUTER_DIR   = Path(__file__).resolve().parent
_BACKEND_DIR  = _ROUTER_DIR.parent.parent
_ARTIFACT_DIR = _BACKEND_DIR / "ml" / "artifacts"
_JOBLIB_PATH  = _ARTIFACT_DIR / "location_classifier.joblib"

# Load the model artifact at startup
_model_artifact: dict[str, Any] | None = None

def _get_model_artifact() -> dict[str, Any]:
    global _model_artifact
    if _model_artifact is None:
        if not _JOBLIB_PATH.exists():
            raise HTTPException(
                status_code=503,
                detail="Model artifact not found. Please run training scripts first."
            )
        # We suppress warnings from joblib if xgboost versions mismatch slightly
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            _model_artifact = joblib.load(_JOBLIB_PATH)
    return _model_artifact


# ===========================================================================
# Pydantic models
# ===========================================================================

class SearchRequest(BaseModel):
    """Contextual features provided by the user for an item search."""
    item_type:         str   = Field(..., description="E.g. keys, wallet, backpack")
    time_of_day:       float = Field(..., description="0.00 to 23.99")
    day_of_week:       int   = Field(..., description="0 (Monday) to 6 (Sunday)")
    weather_condition: str   = Field(..., description="clear, rain, snow, extreme_heat")
    carrying_baggage:  bool  = Field(..., description="True if carrying groceries/packages")
    fatigue_level:     int   = Field(..., description="1 (Energetic) to 5 (Exhausted)")
    start_zone:        str   = Field(
        default="foyer_credenza",
        description="The user's current starting location."
    )


class SearchResponse(BaseModel):
    """Result of the ML prediction and spatial routing."""
    probabilities:         dict[str, float]
    route:                 list[str]
    total_distance_meters: float
    pruned_zones:          list[str]
    route_steps:           list[dict]


# ===========================================================================
# Router
# ===========================================================================

router = APIRouter(
    prefix="/api/v1/router",
    tags=["search"],
)


def _engineer_features(req: SearchRequest) -> pd.DataFrame:
    """
    Convert the incoming request to a DataFrame and engineer the 4
    interaction features exactly as done in train_supervised.py.
    """
    baggage_int = 1 if req.carrying_baggage else 0
    
    # Base features
    data = {
        "item_type":         [req.item_type],
        "weather_condition": [req.weather_condition],
        "time_of_day":       [req.time_of_day],
        "day_of_week":       [req.day_of_week],
        "fatigue_level":     [req.fatigue_level],
        "carrying_baggage":  [baggage_int],
    }
    df = pd.DataFrame(data)
    
    # R1: baggage & keys|backpack -> foyer/kitchen
    df["feat_baggage_entry_item"] = (
        (df["carrying_baggage"] == 1) & 
        (df["item_type"].isin(["keys", "backpack"]))
    ).astype(int)
    
    # R2: fatigue>=4 & time>=21 -> bedroom/couch
    df["feat_tired_night"] = (
        (df["fatigue_level"] >= 4) & 
        (df["time_of_day"] >= 21.0)
    ).astype(int)
    
    # R3: spectacles|earphones & weekday & 9-18 -> desk
    df["feat_work_hours"] = (
        (df["item_type"].isin(["spectacles", "earphones"])) & 
        (df["day_of_week"] <= 4) & 
        (df["time_of_day"] >= 9.0) & 
        (df["time_of_day"] <= 18.0)
    ).astype(int)
    
    # R4: rain|snow & baggage -> foyer boost
    df["feat_inclement_baggage"] = (
        (df["weather_condition"].isin(["rain", "snow"])) & 
        (df["carrying_baggage"] == 1)
    ).astype(int)
    
    return df


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """
    Predict item location probabilities and calculate the optimal search route.
    """
    artifact      = _get_model_artifact()
    preprocessor  = artifact["preprocessor"]
    model         = artifact["model"]
    label_encoder = artifact["label_encoder"]
    
    # 1. Feature Engineering
    df = _engineer_features(request)
    
    # 2. Preprocess
    # The ColumnTransformer expects the exact column order from training.
    X_proc = preprocessor.transform(df)
    
    # 3. Predict Probabilities
    probs_array = model.predict_proba(X_proc)[0]  # first (and only) row
    
    # 4. Map probabilities to class names
    classes = label_encoder.classes_
    probabilities: dict[str, float] = {
        cls_name: float(prob) for cls_name, prob in zip(classes, probs_array)
    }
    
    # 5. Route calculation
    try:
        route_result = calculate_optimal_route(
            start_zone=request.start_zone,
            probabilities=probabilities
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return SearchResponse(
        probabilities=probabilities,
        route=route_result["route"],
        total_distance_meters=route_result["total_distance_meters"],
        pruned_zones=route_result["pruned_zones"],
        route_steps=route_result.get("route_steps", [])
    )
