"""
MemoryVault AI - Supabase Database Client
==========================================
Phase 1, Step 2: Database Connection

Loads SUPABASE_URL and SUPABASE_KEY from the .env file located at the
backend root directory and exports a singleton Supabase client instance.

Usage:
    from app.db import supabase
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

# ---------------------------------------------------------------------------
# Locate and load the .env file
# ---------------------------------------------------------------------------
# The .env file should live at backend/.env (one level above this package).
# We resolve relative to this file's location so the path is correct
# regardless of the working directory the server is launched from.

_HERE = Path(__file__).resolve().parent          # backend/app/
_BACKEND_ROOT = _HERE.parent                     # backend/
_ENV_PATH = _BACKEND_ROOT / ".env"

if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    # Fallback: let python-dotenv search the standard locations
    load_dotenv()

# ---------------------------------------------------------------------------
# Validate required environment variables
# ---------------------------------------------------------------------------

SUPABASE_URL: str | None = os.getenv("SUPABASE_URL")
SUPABASE_KEY: str | None = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    raise RuntimeError(
        "Missing environment variable: SUPABASE_URL. "
        "Ensure it is set in backend/.env before starting the server."
    )

if not SUPABASE_KEY:
    raise RuntimeError(
        "Missing environment variable: SUPABASE_KEY. "
        "Ensure it is set in backend/.env before starting the server."
    )

# ---------------------------------------------------------------------------
# Singleton Supabase client
# ---------------------------------------------------------------------------

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
