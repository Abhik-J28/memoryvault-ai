"""
MemoryVault AI - FastAPI Application Entry Point
=================================================
Phase 1–4 combined

This module initialises the FastAPI application instance, configures
CORS middleware, and registers:
  - /api/health           → basic API liveness check
  - /api/health/db        → Supabase connectivity probe against session_logs
  - /api/v1/chat          → main conversational endpoint
  - /api/v1/feedback      → "Found Here" session feedback
  - /api/v1/analytics/metrics  → ML model performance metrics
  - /api/v1/analytics/clusters → PCA cluster visualisation data
  - /api/v1/layout        → home graph topology for frontend SVG
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.chat.dialogue_manager import process_turn
from app.chat.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    AuthRequest,
    AuthResponse,
    CustomLocationRequest,
)
from app.db import supabase
from app.db_local import (
    register_user,
    login_user,
    save_custom_location,
    get_custom_locations,
    delete_custom_location,
)

# ---------------------------------------------------------------------------
# Application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="MemoryVault AI API",
    description=(
        "Context-Aware Misplaced Item Prediction & Search Route Optimisation System. "
        "Provides a conversational interface backed by a Random Forest classifier "
        "and an A* spatial search router."
    ),
    version="1.0.0",
    # docs_url defaults to /docs  (Swagger UI)
    # redoc_url defaults to /redoc
    # openapi_url defaults to /openapi.json
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
# Allow requests originating from the Next.js / Vanilla JS frontend dev server
# running on http://localhost:3000.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Health Check Endpoint
# ---------------------------------------------------------------------------


@app.get(
    "/api/health",
    summary="API Health Check",
    tags=["Health"],
    response_description="Returns the operational status of the API.",
)
async def health_check() -> dict:
    """
    Health Check endpoint.

    Returns a 200 OK status with a JSON payload confirming that the
    MemoryVault AI API is active and reachable.

    **Phase 1 – Step 1 scope only.** ML inference and routing logic
    will be added in later phases.
    """
    return {
        "status": "ok",
        "message": "MemoryVault AI API is active.",
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Database Health Check Endpoint
# ---------------------------------------------------------------------------


@app.get(
    "/api/health/db",
    summary="Database Health Check",
    tags=["Health"],
    response_description="Confirms Supabase connectivity and session_logs table access.",
)
async def health_check_db() -> dict:
    """
    Database Health Check endpoint.

    Executes a lightweight probe query (``SELECT id FROM session_logs LIMIT 1``)
    against Supabase. Returns 200 on success or raises a 500 HTTPException
    with the underlying error detail on failure.

    **Phase 1 – Step 2 scope only.**
    """
    try:
        supabase.table("session_logs").select("id").limit(1).execute()
        return {"database": "connected", "table": "session_logs"}
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection error: {exc}",
        )


# ---------------------------------------------------------------------------
# Chat Endpoint
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/chat",
    summary="Process a chat turn",
    tags=["Chat"],
    response_model=ChatResponse,
)
async def chat(request: ChatRequest) -> dict:
    """
    Main conversational endpoint.

    Accepts the user's message, the current dialogue state, and
    accumulated context.  Returns the bot's response, quick-reply
    options, and (when context is complete) the ML prediction and
    A* search route.
    """
    try:
        result = process_turn(
            session_id=request.session_id,
            message=request.message,
            state=request.state,
            context=request.context,
            username=request.username,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing error: {exc}",
        )


# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/auth/register",
    summary="Register a new unique user",
    tags=["Auth"],
    response_model=AuthResponse,
)
async def auth_register(request: AuthRequest) -> dict:
    """Registers a new user account with unique username enforcement."""
    res = register_user(request.username, request.password)
    if not res["success"]:
        return {"success": False, "error": res["error"]}
    return {"success": True, "user": res["user"]}


@app.post(
    "/api/v1/auth/login",
    summary="User login authentication",
    tags=["Auth"],
    response_model=AuthResponse,
)
async def auth_login(request: AuthRequest) -> dict:
    """Authenticates username & password credentials."""
    res = login_user(request.username, request.password)
    if not res["success"]:
        return {"success": False, "error": res["error"]}
    return {"success": True, "user": res["user"]}


# ---------------------------------------------------------------------------
# User Custom Saved Locations Endpoints
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/user/custom-locations",
    summary="Save a custom item location habit override",
    tags=["User Adaptive"],
)
async def add_custom_location(request: CustomLocationRequest) -> dict:
    """Saves a user's custom habit location for an item (e.g., keys -> study_room)."""
    res = save_custom_location(
        username=request.username,
        item_type=request.item_type,
        room=request.room,
        notes=request.notes or "",
    )
    return res


@app.get(
    "/api/v1/user/custom-locations",
    summary="Get user's custom saved locations",
    tags=["User Adaptive"],
)
async def fetch_custom_locations(username: str, item_type: str | None = None) -> list:
    """Fetches custom saved location overrides for a user."""
    return get_custom_locations(username=username, item_type=item_type)


@app.delete(
    "/api/v1/user/custom-locations/{location_id}",
    summary="Delete a custom saved location override",
    tags=["User Adaptive"],
)
async def remove_custom_location(location_id: int, username: str) -> dict:
    """Deletes a custom saved item location."""
    return delete_custom_location(username=username, location_id=location_id)


# ---------------------------------------------------------------------------
# Feedback Endpoint
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/feedback",
    summary="Log item-found feedback",
    tags=["Chat"],
)
async def feedback(request: FeedbackRequest) -> dict:
    """
    Records a "Found Here" event from the user.

    Attempts to insert the feedback into the Supabase ``session_logs``
    table.  Returns success even if the DB write fails (graceful
    degradation).
    """
    log_entry = {
        "session_id": request.session_id,
        "item_type": request.item_type,
        "found_location": request.found_location,
        **request.context,
    }

    try:
        supabase.table("session_logs").insert(log_entry).execute()
    except Exception:
        # Graceful degradation — don't fail the user experience
        pass

    return {"status": "ok", "message": "Feedback recorded."}


# ---------------------------------------------------------------------------
# Analytics Endpoints
# ---------------------------------------------------------------------------

_ML_MODELS_DIR = Path(__file__).resolve().parent / "ml" / "models"


@app.get(
    "/api/v1/analytics/metrics",
    summary="ML model performance metrics",
    tags=["Analytics"],
)
async def analytics_metrics() -> dict:
    """Return Random Forest evaluation metrics (accuracy, ROC-AUC, confusion matrix, etc.)."""
    metrics_path = _ML_MODELS_DIR / "rf_metrics.json"
    if not metrics_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Model metrics not found. Run `python -m app.ml.train` first.",
        )
    with open(metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get(
    "/api/v1/analytics/clusters",
    summary="PCA cluster visualisation data",
    tags=["Analytics"],
)
async def analytics_clusters() -> dict:
    """Return PCA-reduced cluster coordinates + centroids for scatter plot."""
    cluster_path = _ML_MODELS_DIR / "cluster_data.json"
    if not cluster_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Cluster data not found. Run `python -m app.ml.train` first.",
        )
    with open(cluster_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get(
    "/api/v1/analytics/habit-metrics",
    summary="Habit profiler metrics",
    tags=["Analytics"],
)
async def analytics_habit_metrics() -> dict:
    """Return K-Means + PCA evaluation metrics."""
    metrics_path = _ML_MODELS_DIR / "habit_metrics.json"
    if not metrics_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Habit metrics not found. Run `python -m app.ml.train` first.",
        )
    with open(metrics_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Layout Endpoint
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/layout",
    summary="Home floor plan graph topology",
    tags=["Layout"],
)
async def layout() -> dict:
    """Return the home layout graph (rooms + edges) for the Route Inspector SVG."""
    from app.search.astar_router import get_layout

    return get_layout()
