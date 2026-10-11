"""
MemoryVault AI — Pydantic Schemas
==================================
Phase 4

Request / response models for the chat and analytics API endpoints.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    """Payload sent from the frontend on every user interaction."""

    session_id: str = Field(..., description="UUID identifying the current chat session")
    message: str = Field(..., description="User's text input or quick-reply value")
    state: str = Field(
        default="GREETING",
        description="Current dialogue state (managed by the frontend)",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Accumulated context collected so far (item, time, weather …)",
    )
    username: Optional[str] = Field(
        default=None,
        description="Logged-in username if authenticated",
    )


class RouteStep(BaseModel):
    """A single step in the generated search checklist."""

    room: str
    label: str
    probability: float
    distance_from_previous: float
    cumulative_distance: float
    x: int
    y: int
    path_from_previous: list[str]


class ChatResponse(BaseModel):
    """Payload returned to the frontend after processing a chat turn."""

    session_id: str
    bot_message: str
    quick_replies: list[str] = Field(default_factory=list)
    state: str
    context: dict[str, Any] = Field(default_factory=dict)
    route_data: Optional[list[RouteStep]] = None
    layout: Optional[dict[str, Any]] = None
    prediction: Optional[dict[str, Any]] = None
    custom_user_rooms: list[str] = Field(default_factory=list, description="User-pinned custom habit rooms for pink map highlights")
    repeated_finding_rooms: list[str] = Field(default_factory=list, description="Empirical repeated finding rooms for orange map highlights")
    finding_counts: dict[str, int] = Field(default_factory=dict, description="Finding frequency per room for badge counts")


# ---------------------------------------------------------------------------
# Auth Models
# ---------------------------------------------------------------------------


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    user: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Custom Location Models
# ---------------------------------------------------------------------------


class CustomLocationRequest(BaseModel):
    username: str
    item_type: str
    room: str
    notes: Optional[str] = ""


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------


class FeedbackRequest(BaseModel):
    """Sent when the user clicks "Found Here" on a route card."""

    session_id: str
    item_type: str
    found_location: str
    context: dict[str, Any] = Field(default_factory=dict)
    username: Optional[str] = Field(
        default=None,
        description="Logged-in username if authenticated; guests are excluded",
    )



# ---------------------------------------------------------------------------
# Analytics (response-only)
# ---------------------------------------------------------------------------


class AnalyticsMetrics(BaseModel):
    """Aggregated ML model performance metrics."""

    accuracy: float
    top3_accuracy: float
    roc_auc_macro: float
    classification_report: dict[str, Any]
    confusion_matrix: list[list[int]]
    class_labels: list[str]
    roc_curves: dict[str, Any]


class ClusterData(BaseModel):
    """PCA cluster visualisation data."""

    points: list[dict[str, Any]]
    centroids: list[dict[str, Any]]
