"""
MemoryVault AI - Local SQLite Database Module
=============================================
Provides persistent local storage for:
  - User Authentication (Unique username & hashed passwords)
  - User-Adaptive Custom Saved Item Locations

Zero external dependency requirement (uses standard library sqlite3 & hashlib).
"""

import sqlite3
import hashlib
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_DB_PATH = _HERE / "data" / "memoryvault.db"

# Ensure data directory exists
os.makedirs(_DB_PATH.parent, exist_ok=True)


def get_db_connection():
    """Return an SQLite database connection with row factory enabled."""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialise SQLite database schema for users and custom item locations."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 2. Custom Item Locations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_custom_locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                item_type TEXT NOT NULL,
                room TEXT NOT NULL,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(username, item_type, room)
            );
        """)
        conn.commit()


# Initialise on import
init_db()


def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = "memoryvault_salt_2026"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Auth Functions
# ---------------------------------------------------------------------------

def register_user(username: str, password: str) -> dict:
    """Register a new user with unique username check."""
    username = username.strip().lower()
    if not username or not password:
        return {"success": False, "error": "Username and password are required."}
    
    if len(username) < 3:
        return {"success": False, "error": "Username must be at least 3 characters long."}

    password_h = hash_password(password)

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_h)
            )
            conn.commit()
            user_id = cursor.lastrowid
            return {
                "success": True,
                "user": {"id": user_id, "username": username}
            }
    except sqlite3.IntegrityError:
        return {"success": False, "error": f"Username '{username}' is already taken. Please choose another."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def login_user(username: str, password: str) -> dict:
    """Authenticate user credentials."""
    username = username.strip().lower()
    password_h = hash_password(password)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username FROM users WHERE username = ? AND password_hash = ?",
            (username, password_h)
        )
        row = cursor.fetchone()
        if row:
            return {
                "success": True,
                "user": {"id": row["id"], "username": row["username"]}
            }
        return {"success": False, "error": "Invalid username or password."}


# ---------------------------------------------------------------------------
# Custom Item Locations Functions
# ---------------------------------------------------------------------------

def save_custom_location(username: str, item_type: str, room: str, notes: str = "") -> dict:
    """Save or update a user's custom saved location for an item."""
    username = username.strip().lower()
    item_type = item_type.strip().lower()
    room = room.strip().lower()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_custom_locations (username, item_type, room, notes)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username, item_type, room) 
            DO UPDATE SET notes=excluded.notes, created_at=CURRENT_TIMESTAMP
        """, (username, item_type, room, notes))
        conn.commit()
        return {"success": True, "message": f"Saved {room} for {item_type}."}


def get_custom_locations(username: str, item_type: str | None = None) -> list[dict]:
    """Fetch custom saved locations for a user, optionally filtered by item_type."""
    username = username.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if item_type:
            cursor.execute(
                "SELECT id, username, item_type, room, notes, created_at FROM user_custom_locations WHERE username = ? AND item_type = ? ORDER BY id DESC",
                (username, item_type.strip().lower())
            )
        else:
            cursor.execute(
                "SELECT id, username, item_type, room, notes, created_at FROM user_custom_locations WHERE username = ? ORDER BY id DESC",
                (username,)
            )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def delete_custom_location(username: str, location_id: int) -> dict:
    """Delete a custom saved location."""
    username = username.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM user_custom_locations WHERE id = ? AND username = ?",
            (location_id, username)
        )
        conn.commit()
        return {"success": True}
