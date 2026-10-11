"""
MemoryVault AI — Search History & Placement Logging Router
===========================================================
Faculty Architecture Enhancement: Guest Mode vs. Authenticated Mode
Endpoints:
  - POST /api/v1/history/log           -> Record item search outcome (with optional user_id)
  - GET  /api/v1/history/user/{user_id} -> Retrieve search history & recovered item logs for user
  - GET  /api/v1/history               -> General query for history logs
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db import supabase
from app.db_local import get_db_connection, record_item_finding

router = APIRouter(prefix="/api/v1/history", tags=["history"])

# ---------------------------------------------------------------------------
# Ensure local search_history table exists in SQLite for fault-tolerant cache
# ---------------------------------------------------------------------------

def _ensure_history_table():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                session_id TEXT,
                item_type TEXT NOT NULL,
                predicted_zone TEXT,
                actual_found_zone TEXT NOT NULL,
                time_of_day REAL,
                day_of_week INTEGER,
                weather_condition TEXT,
                carrying_baggage INTEGER,
                fatigue_level INTEGER,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

_ensure_history_table()


# ===========================================================================
# Pydantic Schemas
# ===========================================================================

class SearchHistoryLogRequest(BaseModel):
    user_id: str | None = Field(
        default=None,
        description="Optional user ID or username. None / omitted indicates Guest Quick-Search.",
    )
    session_id: str | None = Field(
        default=None,
        description="Active dialogue session ID.",
    )
    item_type: str = Field(
        ...,
        description="Type of the lost item (e.g. keys, phone, wallet).",
    )
    predicted_zone: str | None = Field(
        default=None,
        description="Initial ML predicted zone (e.g. foyer_credenza).",
    )
    actual_found_zone: str = Field(
        ...,
        description="Confirmed domestic zone where item was recovered (e.g. kitchen_counter).",
    )
    time_of_day: float | None = Field(
        default=None,
        description="Time of day as float (0.0 to 24.0).",
    )
    day_of_week: int | None = Field(
        default=None,
        description="Day of week integer (0 = Monday, 6 = Sunday).",
    )
    weather_condition: str | None = Field(
        default=None,
        description="Atmospheric condition (sunny, rainy, cloudy, snowy).",
    )
    carrying_baggage: bool | None = Field(
        default=None,
        description="Whether user was carrying luggage / bag.",
    )
    fatigue_level: int | None = Field(
        default=None,
        description="Fatigue level on 1-5 scale.",
    )
    notes: str | None = Field(
        default="",
        description="Optional recovery remarks or habit context.",
    )


class HistoryLogEntry(BaseModel):
    id: int | str | None = None
    user_id: str | None = None
    session_id: str | None = None
    item_type: str
    predicted_zone: str | None = None
    actual_found_zone: str
    time_of_day: float | None = None
    day_of_week: int | None = None
    weather_condition: str | None = None
    carrying_baggage: bool | None = None
    fatigue_level: int | None = None
    notes: str | None = None
    created_at: str | None = None


class UserHistoryResponse(BaseModel):
    user_id: str
    total_records: int
    history: list[HistoryLogEntry]


# ===========================================================================
# Endpoints
# ===========================================================================

@router.post(
    "/log",
    summary="Log search outcome and confirmed item location",
    response_model=dict,
)
async def log_search_outcome(payload: SearchHistoryLogRequest) -> dict:
    """
    Record an item search outcome.
    
    - In Authenticated Mode (user_id provided): saves to user history,
      updates empirical habit counters, and mirrors to Supabase.
    - In Guest Mode (user_id omitted/null): logs the session outcome
      anonymously without linking to a user profile.
    """
    user_id_clean = payload.user_id.strip() if payload.user_id else None
    if user_id_clean and user_id_clean.lower() == "guest":
        user_id_clean = None

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Store in local fault-tolerant SQLite database
    local_id = None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_search_history (
                    user_id, session_id, item_type, predicted_zone,
                    actual_found_zone, time_of_day, day_of_week,
                    weather_condition, carrying_baggage, fatigue_level,
                    notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id_clean,
                    payload.session_id,
                    payload.item_type.strip().lower(),
                    payload.predicted_zone,
                    payload.actual_found_zone.strip().lower(),
                    payload.time_of_day,
                    payload.day_of_week,
                    payload.weather_condition,
                    1 if payload.carrying_baggage else 0 if payload.carrying_baggage is not None else None,
                    payload.fatigue_level,
                    payload.notes or "",
                    now_iso,
                ),
            )
            conn.commit()
            local_id = cursor.lastrowid
    except Exception as exc:
        # Continue to attempt Supabase if local fails
        pass

    # 2. Update empirical repeated finding count if authenticated
    if user_id_clean:
        try:
            record_item_finding(
                username=user_id_clean.lower(),
                item_type=payload.item_type.strip().lower(),
                room=payload.actual_found_zone.strip().lower(),
            )
        except Exception:
            pass

    # 3. Synchronise with Supabase search_history and session_logs tables
    supabase_synced = False
    try:
        sess_uuid = str(uuid.uuid4())
        sh_payload: dict[str, Any] = {
            "session_id": sess_uuid,
            "item_type": payload.item_type.strip().lower(),
            "predicted_top_zone": payload.predicted_zone or "foyer_credenza",
            "actual_found_zone": payload.actual_found_zone.strip().lower(),
            "context_features": {
                "user_id": user_id_clean,
                "original_session_id": payload.session_id,
                "time_of_day": payload.time_of_day,
                "day_of_week": payload.day_of_week,
                "weather_condition": payload.weather_condition,
                "carrying_baggage": payload.carrying_baggage,
                "fatigue_level": payload.fatigue_level,
                "notes": payload.notes,
            },
        }
        supabase.table("search_history").insert(sh_payload).execute()

        sl_payload: dict[str, Any] = {
            "session_token": sess_uuid,
            "context_state": sh_payload,
        }
        supabase.table("session_logs").insert(sl_payload).execute()
        supabase_synced = True
    except Exception as exc:
        print(f"[Supabase history sync error]: {exc}")
        supabase_synced = False

    return {
        "status": "success",
        "message": "Search outcome logged successfully.",
        "mode": "authenticated" if user_id_clean else "guest",
        "entry_id": local_id,
        "supabase_synced": supabase_synced,
        "item_type": payload.item_type,
        "actual_found_zone": payload.actual_found_zone,
    }


@router.get(
    "/user/{user_id}",
    summary="Fetch past search history for an authenticated user",
    response_model=UserHistoryResponse,
)
async def get_user_search_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=100),
) -> UserHistoryResponse:
    """
    Retrieve history of previous misplaced item searches and confirmed
    found locations for an authenticated profile.
    """
    user_clean = user_id.strip()
    if not user_clean:
        raise HTTPException(status_code=400, detail="User ID is required.")

    entries: list[HistoryLogEntry] = []

    # 1. Fetch from local SQLite storage
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, session_id, item_type, predicted_zone,
                       actual_found_zone, time_of_day, day_of_week,
                       weather_condition, carrying_baggage, fatigue_level,
                       notes, created_at
                FROM user_search_history
                WHERE LOWER(user_id) = LOWER(?)
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_clean, limit),
            )
            rows = cursor.fetchall()
            for r in rows:
                entries.append(
                    HistoryLogEntry(
                        id=r["id"],
                        user_id=r["user_id"],
                        session_id=r["session_id"],
                        item_type=r["item_type"],
                        predicted_zone=r["predicted_zone"],
                        actual_found_zone=r["actual_found_zone"],
                        time_of_day=r["time_of_day"],
                        day_of_week=r["day_of_week"],
                        weather_condition=r["weather_condition"],
                        carrying_baggage=bool(r["carrying_baggage"]) if r["carrying_baggage"] is not None else None,
                        fatigue_level=r["fatigue_level"],
                        notes=r["notes"],
                        created_at=str(r["created_at"]),
                    )
                )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}")

    return UserHistoryResponse(
        user_id=user_clean,
        total_records=len(entries),
        history=entries,
    )


@router.get(
    "",
    summary="List general search history records",
    response_model=dict,
)
async def list_history(
    user_id: str | None = Query(default=None, description="Optional user filter"),
    limit: int = Query(default=50, ge=1, le=100),
) -> dict:
    """
    General history query endpoint supporting both authenticated and global audits.
    """
    if user_id:
        res = await get_user_search_history(user_id=user_id, limit=limit)
        return res.model_dump()

    # If no user_id, return recent global logs (anonymized for guests)
    entries: list[dict] = []
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, session_id, item_type, predicted_zone,
                       actual_found_zone, created_at
                FROM user_search_history
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            for r in rows:
                entries.append({
                    "id": r["id"],
                    "is_guest": r["user_id"] is None,
                    "user_id": r["user_id"] if r["user_id"] else "guest",
                    "session_id": r["session_id"],
                    "item_type": r["item_type"],
                    "predicted_zone": r["predicted_zone"],
                    "actual_found_zone": r["actual_found_zone"],
                    "created_at": str(r["created_at"]),
                })
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database query failed: {exc}")

    return {
        "total_records": len(entries),
        "history": entries,
    }
