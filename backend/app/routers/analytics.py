"""
MemoryVault AI — Analytics Router
===================================
Phase 2, Step 4  |  SRS FR-07 / UI/UX Evaluator Analytics Drawer

Exposes pre-computed ML evaluation artefacts over a versioned REST API so
the Next.js Evaluator Analytics Drawer can fetch and render them without
any runtime ML inference.

Endpoints
---------
GET /api/v1/analytics/metrics
    Returns MetricsResponse combining:
      - Confusion matrix (classes + 2-D integer matrix)
      - ROC-AUC data   (macro AUC + per-class FPR / TPR arrays)
      - Cluster data   (PCA variance, archetype labels, 200 scatter points)
      - Validation status (boolean — NFR-02 Top-3 >= 0.80 & NFR-03 AUC >= 0.85)

Artefact sources (resolved relative to this file to work from any CWD)
-----------------------------------------------------------------------
  backend/ml/artifacts/evaluation_metrics.json   <- train_supervised.py output
  backend/ml/artifacts/cluster_summary.json      <- train_unsupervised.py output

Error handling
--------------
If either JSON file is absent (training has not been run), a 503 Service
Unavailable is raised with a clear instructional message.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Artefact paths — two levels up from this file: backend/ml/artifacts/
# ---------------------------------------------------------------------------
_ROUTER_DIR    = Path(__file__).resolve().parent          # backend/app/routers/
_APP_DIR       = _ROUTER_DIR.parent                       # backend/app/
_BACKEND_DIR   = _APP_DIR.parent                          # backend/
_ARTIFACT_DIR  = _BACKEND_DIR / "ml" / "artifacts"

_EVAL_JSON_PATH    = _ARTIFACT_DIR / "evaluation_metrics.json"
_CLUSTER_JSON_PATH = _ARTIFACT_DIR / "cluster_summary.json"


# ===========================================================================
# Pydantic response models
# ===========================================================================

class ConfusionMatrixData(BaseModel):
    """Validated confusion matrix payload for the Evaluator Heatmap."""

    classes: list[str] = Field(
        description="Ordered list of zone class names matching matrix rows/cols."
    )
    matrix: list[list[int]] = Field(
        description="2-D array of actual-vs-predicted counts (rows=actual, cols=predicted)."
    )


class ROCClassCurve(BaseModel):
    """FPR / TPR arrays and AUC for a single One-vs-Rest class."""

    fpr: list[float] = Field(description="False positive rate array (sampled).")
    tpr: list[float] = Field(description="True positive rate array (sampled).")
    auc: float       = Field(description="Area under the ROC curve for this class.")


class ROCData(BaseModel):
    """Full ROC payload: macro AUC + per-class curves."""

    macro_auc:    float                      = Field(
        description="Macro-averaged One-vs-Rest AUC across all classes."
    )
    class_curves: dict[str, ROCClassCurve]   = Field(
        description="Per-class ROC curve data keyed by zone name."
    )


class ClusterArchetype(BaseModel):
    """Human-readable label and traits for a single KMeans cluster."""

    name:         str = Field(description="Archetype name (e.g. 'Rushed Baggage Drop').")
    sample_count: int = Field(description="Number of training samples in this cluster.")
    traits:       str = Field(description="Dominant feature traits description.")


class ScatterPoint(BaseModel):
    """Single data point for the 2-D PCA scatter plot."""

    pca_x:      float = Field(description="PCA component 1 coordinate.")
    pca_y:      float = Field(description="PCA component 2 coordinate.")
    cluster_id: int   = Field(description="KMeans cluster assignment (0, 1, or 2).")
    item_type:  str   = Field(description="Item type string for colour coding.")


class ClusterData(BaseModel):
    """Unsupervised clustering payload for the Evaluator scatter visualisation."""

    pca_variance_ratio:  list[float]                     = Field(
        description="Explained variance ratios for PCA components 1 and 2."
    )
    cluster_archetypes:  dict[str, ClusterArchetype]     = Field(
        description="Mapping of cluster ID string to archetype metadata."
    )
    sample_projections:  list[ScatterPoint]              = Field(
        description="200 subsampled PCA-projected points for the scatter plot."
    )


class ValidationStatus(BaseModel):
    """SRS Section 7 acceptance criteria pass/fail flags."""

    nfr02_top3_passed:     bool  = Field(
        description="True if test-set Top-3 accuracy >= 0.80 (NFR-02)."
    )
    nfr03_roc_auc_passed:  bool  = Field(
        description="True if test-set macro ROC-AUC >= 0.85 (NFR-03)."
    )
    top3_accuracy:         float = Field(description="Actual test-set Top-3 accuracy.")
    roc_auc_macro:         float = Field(description="Actual test-set macro ROC-AUC.")
    nfr02_threshold:       float = Field(description="NFR-02 acceptance threshold (0.80).")
    nfr03_threshold:       float = Field(description="NFR-03 acceptance threshold (0.85).")
    all_criteria_met:      bool  = Field(
        description="True only when both NFR-02 and NFR-03 are satisfied."
    )


class MetricsResponse(BaseModel):
    """
    Combined analytics payload returned by GET /api/v1/analytics/metrics.

    Feeds the Next.js Evaluator Analytics Drawer with all data required to
    render the Confusion Matrix heatmap, ROC-AUC curve cards, PCA scatter
    plot, and acceptance criteria status badge.
    """

    confusion_matrix:  ConfusionMatrixData = Field(
        description="Confusion matrix data for the Evaluator Heatmap."
    )
    roc_auc:           ROCData             = Field(
        description="ROC curve data for per-class AUC cards."
    )
    cluster_data:      ClusterData         = Field(
        description="KMeans/PCA clustering payload for the scatter plot."
    )
    validation_status: ValidationStatus    = Field(
        description="SRS NFR-02 / NFR-03 acceptance criteria outcomes."
    )


# ===========================================================================
# Router
# ===========================================================================

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["analytics"],
)


# ---------------------------------------------------------------------------
# Helper: load and validate artefact files
# ---------------------------------------------------------------------------

def _load_artifacts() -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Load evaluation_metrics.json and cluster_summary.json from disk.

    Raises
    ------
    HTTPException(503) if either file is missing (training not yet run).
    """
    missing = [
        name
        for name, path in [
            ("evaluation_metrics.json", _EVAL_JSON_PATH),
            ("cluster_summary.json",    _CLUSTER_JSON_PATH),
        ]
        if not path.exists()
    ]

    if missing:
        raise HTTPException(
            status_code=503,
            detail=(
                "Model evaluation artifacts not found. "
                "Please run training scripts first. "
                f"Missing: {', '.join(missing)}"
            ),
        )

    eval_data    = json.loads(_EVAL_JSON_PATH.read_text(encoding="utf-8"))
    cluster_data = json.loads(_CLUSTER_JSON_PATH.read_text(encoding="utf-8"))
    return eval_data, cluster_data


# ---------------------------------------------------------------------------
# GET /api/v1/analytics/metrics
# ---------------------------------------------------------------------------

@router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Fetch ML Evaluation Metrics",
    response_description=(
        "Combined confusion matrix, ROC-AUC curves, PCA cluster scatter data, "
        "and SRS acceptance criteria validation status."
    ),
)
async def get_metrics() -> MetricsResponse:
    """
    Return pre-computed ML evaluation artefacts for the Evaluator Analytics Drawer.

    Reads **evaluation_metrics.json** (from ``train_supervised.py``) and
    **cluster_summary.json** (from ``train_unsupervised.py``) from
    ``backend/ml/artifacts/``.

    **Raises 503** if either artefact file is absent — this means the
    training scripts have not been executed yet.
    """
    eval_data, cluster_raw = _load_artifacts()

    # ------------------------------------------------------------------ #
    # Build ConfusionMatrixData                                            #
    # ------------------------------------------------------------------ #
    confusion_matrix = ConfusionMatrixData(
        classes=eval_data["classes"],
        matrix=eval_data["confusion_matrix"],
    )

    # ------------------------------------------------------------------ #
    # Build ROCData                                                        #
    # ------------------------------------------------------------------ #
    class_curves: dict[str, ROCClassCurve] = {
        class_name: ROCClassCurve(
            fpr=curve["fpr"],
            tpr=curve["tpr"],
            auc=curve["auc"],
        )
        for class_name, curve in eval_data["roc_curves"].items()
    }
    roc_auc = ROCData(
        macro_auc=eval_data["roc_auc_macro"],
        class_curves=class_curves,
    )

    # ------------------------------------------------------------------ #
    # Build ClusterData                                                    #
    # ------------------------------------------------------------------ #
    archetypes: dict[str, ClusterArchetype] = {
        cid: ClusterArchetype(
            name=archetype["name"],
            sample_count=archetype["sample_count"],
            traits=archetype["traits"],
        )
        for cid, archetype in cluster_raw["cluster_archetypes"].items()
    }
    scatter_points: list[ScatterPoint] = [
        ScatterPoint(
            pca_x=pt["pca_x"],
            pca_y=pt["pca_y"],
            cluster_id=pt["cluster_id"],
            item_type=pt["item_type"],
        )
        for pt in cluster_raw["sample_projections"]
    ]
    cluster_data = ClusterData(
        pca_variance_ratio=cluster_raw["pca_variance_ratio"],
        cluster_archetypes=archetypes,
        sample_projections=scatter_points,
    )

    # ------------------------------------------------------------------ #
    # Build ValidationStatus                                               #
    # ------------------------------------------------------------------ #
    nfr02_ok = bool(eval_data["nfr02_passed"])
    nfr03_ok = bool(eval_data["nfr03_passed"])
    validation_status = ValidationStatus(
        nfr02_top3_passed=nfr02_ok,
        nfr03_roc_auc_passed=nfr03_ok,
        top3_accuracy=eval_data["top3_accuracy"],
        roc_auc_macro=eval_data["roc_auc_macro"],
        nfr02_threshold=eval_data["nfr02_threshold"],
        nfr03_threshold=eval_data["nfr03_threshold"],
        all_criteria_met=nfr02_ok and nfr03_ok,
    )

    return MetricsResponse(
        confusion_matrix=confusion_matrix,
        roc_auc=roc_auc,
        cluster_data=cluster_data,
        validation_status=validation_status,
    )
