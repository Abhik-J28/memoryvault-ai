# MemoryVault AI — System Startup, Setup & Shutdown Guide

This guide contains all commands required to set up, run, test, and stop the **MemoryVault AI** application (Backend + Frontend).

---

## Prerequisites
- **Python**: 3.10 or higher
- **Node.js**: v18.0.0 or higher (`npm` included)
- **Git**: Installed and configured

---

## 1. Backend Setup & Startup

### Step 1.1: Install Backend Dependencies
Open a terminal in the project root directory:
```bash
cd backend
pip install -r requirements.txt
```

### Step 1.2: Generate Dataset & Train ML Models
Train the Habit Profiler models and compute evaluator metrics:
```bash
python -m app.ml.train
```
*(This generates 5,000 synthetic records, trains RandomForest/GradientBoosting models, and saves evaluation metrics).*

### Step 1.3: Start FastAPI Backend Server
Launch the backend server on `http://127.0.0.1:8000`:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
> **Backend API Docs**: Swagger UI is available at `http://127.0.0.1:8000/docs`

---

## 2. Frontend Setup & Startup

### Step 2.1: Install Frontend Dependencies
Open a new terminal window in the project root directory:
```bash
cd frontend
npm install
```

### Step 2.2: Start Next.js Development Server
Launch the frontend application:
```bash
npm run dev
```
*(or using Next.js directly: `npx next dev`)*

---

## 3. Accessing the Application

Open your browser and navigate to:
👉 **`http://localhost:3000`**

### Features Available:
- **Conversational Triage**: Chat with MemoryVault AI to pinpoint lost items (`car keys`, `wallet`, `passport`, `glasses`, etc.).
- **Search Route Inspector**: High-visibility blueprint floor plan displaying step-by-step search paths with distance indicators.
- **HD Fullscreen View**: Click **"Expand Map"** to view the floor plan in full resolution.
- **Evaluator Analytics Drawer**: Click **"Evaluator Analytics"** in the top bar to inspect Accuracy, Confusion Matrix, ROC curves, and PCA clusters.
- **Search Another Item**: Click **"Search Another Item"** or **"New Search"** to clear session and predict another misplaced item.

---

## 4. Stopping / Shutting Down the Application

### Option A: Terminal Graceful Shutdown
In each terminal window running the backend or frontend:
- Press `Ctrl + C` (or `Cmd + C` on macOS) to stop the process.

### Option B: PowerShell Process Termination (Windows)
If background processes are running on ports `8000` or `3000`:

```powershell
# Stop Backend process (Port 8000)
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force

# Stop Frontend process (Port 3000)
Get-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess | Stop-Process -Force
```

### Option C: Bash Process Termination (Linux / macOS)
```bash
# Kill process on port 8000
fuser -k 8000/tcp

# Kill process on port 3000
fuser -k 3000/tcp
```
