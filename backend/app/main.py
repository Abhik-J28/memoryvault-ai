"""
MemoryVault AI - FastAPI Application Entry Point
=================================================
Phase 1, Step 2: Database Connection
Phase 2, Step 4: Analytics Router
Phase 3, Step 3: Search Router

This module initialises the FastAPI application instance, configures
CORS middleware, and registers:
  - /api/health            -> basic API liveness check
  - /api/health/db         -> Supabase connectivity probe against session_logs
  - /api/v1/analytics/*   -> ML evaluation metrics for the Evaluator drawer
  - /api/v1/router/search -> Item location prediction and spatial routing
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.db import supabase
from app.routers import analytics, search

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
# Routers
# ---------------------------------------------------------------------------

app.include_router(analytics.router)
app.include_router(search.router)

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
