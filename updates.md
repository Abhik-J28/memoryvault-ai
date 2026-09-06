# MemoryVault AI — Update Changelog & Engineering Report

## Overview
**MemoryVault AI** is an intelligent, context-aware assistant for predicting misplaced everyday items (e.g. keys, wallet, passport, glasses, headphones) and plotting optimal room-by-room search routes within a home environment.

---

## Complete List of Updates Made

### Phase 1: Problem Definition & SRS Architecture Alignment
- Defined 6-class target item predictions (`car_keys`, `wallet`, `passport`, `reading_glasses`, `wireless_earbuds`, `house_keys`).
- Created 8-node residential floor plan graph (`entrance_hallway`, `living_room`, `dining_area`, `kitchen`, `bedroom`, `study_room`, `bathroom`, `balcony`).

### Phase 2: Data Synthesis & ML Pipeline
- Developed synthetic dataset generator (`backend/app/data/generate_dataset.py`) producing 5,000 realistic context-habit records with temporal, emotional, and social factors (e.g., `time_of_day`, `day_type`, `stress_level`, `has_guests`, `routine_disrupted`, `last_activity`).
- Implemented **Habit Profiler** (`backend/app/ml/habit_profiler.py`):
  - RandomForestClassifier + GradientBoosting ensemble predicting top misplaced locations.
  - Probability vector output over all 8 home rooms.
- Implemented **Evaluator Engine** (`backend/app/ml/evaluator.py`):
  - Evaluator analytics calculating Accuracy, Top-3 Accuracy, Macro ROC-AUC, per-class metrics.
  - Confusion Matrix heatmap generation.
  - One-vs-Rest ROC curve coordinates for all 6 target classes.
  - PCA (Principal Component Analysis) 2D cluster projections for habit feature space analysis.

### Phase 3: Spatial Graph Router (A* Pathfitting)
- Built graph topology and edge distance definitions in `home_layout.json`.
- Implemented **A* Search Router** (`backend/app/search/astar_router.py`):
  - Expected Search Time minimization heuristic based on probability distribution and spatial movement cost.
  - Step-by-step ordered room checklist generation with cumulative distance tracking.

### Phase 4: Conversational Triage Dialogue Manager
- Built state-machine dialogue engine (`backend/app/chat/dialogue_manager.py`):
  - Progressive slot filling (`GREETING` -> `ITEM_SELECTION` -> `CONTEXT_QUESTIONS` -> `RESULT`).
  - Contextual quick-reply chip generation.
  - Dynamic user message parsing and habit inference.

### Phase 5: Frontend UI & Route Inspector Overhaul
- Created high-clarity Next.js split-pane workspace (`frontend/src/app/page.tsx`):
  - 55/45 split pane with Chat Pane on left and Route Inspector on right.
- Overhauled **Route Inspector** (`frontend/src/components/RouteInspector.tsx`):
  - Scalable architectural blueprint SVG floor plan with room zone boundaries (`BEDROOM ZONE`, `STUDY/OFFICE`, `LIVING AREA`, `MAIN ENTRANCE`).
  - Illuminated neon A* search paths (`#38bdf8`) with animated flow dots and distance callouts (`2.0m`, `3.5m`).
  - Step sequence rank badges (`#1`, `#2`, `#3`) directly on room nodes.
  - High-visibility room label cards and probability percentage badges (`95%`, `15%`).
  - **HD Fullscreen Expand Modal** allowing users to inspect the floor plan map in maximum resolution.

### Phase 6: Evaluator Analytics Slide-Over Drawer
- Developed **Evaluator Analytics Drawer** (`frontend/src/components/AnalyticsDrawer.tsx`):
  - KPI summary metrics (Overall Accuracy, Top-3 Accuracy, ROC-AUC score).
  - Canvas-based Confusion Matrix heatmap visualization.
  - Canvas-based multi-class ROC curves.
  - Canvas-based PCA Cluster scatter plot visualization.

### Phase 7: "Search Another Lost Item" & Session Reset
- Added **"Search Another Item"** functionality across all UI touchpoints:
  - Top Utility Header bar (`RotateCcw` primary action button).
  - Chat Pane header bar shortcut button.
  - Route Inspector header bar shortcut button.
  - Primary button inside the item-found success banner.
- Clean session reset handler generating a fresh `sessionId`, clearing old predictions/routes, and resetting conversational triage.
