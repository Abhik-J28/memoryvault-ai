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

        # 2. Custom Item Locations table (Manual User Overrides — Pink Highlights)
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

        # 3. User Item Findings table (Empirical Repeated Findings — Orange Highlights)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_item_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                item_type TEXT NOT NULL,
                room TEXT NOT NULL,
                found_count INTEGER DEFAULT 1,
                last_found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
# Custom Item Locations Functions (Manual Overrides — Pink Highlights)
# ---------------------------------------------------------------------------

def save_custom_location(username: str, item_type: str, room: str, notes: str = "") -> dict:
    """Save or update a user's custom saved location for an item (Manual Override — Pink)."""
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
    """Fetch custom saved locations for a user (Manual Overrides — Pink)."""
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


# ---------------------------------------------------------------------------
# Empirical Item Findings Functions (Repeated Findings — Orange Highlights)
# ---------------------------------------------------------------------------

def normalize_item_type(item_type: str) -> str:
    """Normalize item aliases into canonical keys."""
    if not item_type:
        return ""
    item = item_type.strip().lower()
    item_aliases = {
        "key": "keys",
        "keys": "keys",
        "car keys": "keys",
        "car_keys": "keys",
        "house keys": "keys",
        "house_keys": "keys",
        "wallet": "wallet",
        "purse": "wallet",
        "phone": "phone",
        "mobile": "phone",
        "cell": "phone",
        "spectacles": "spectacles",
        "glasses": "spectacles",
        "specs": "spectacles",
        "earphones": "earphones",
        "headphones": "earphones",
        "earbuds": "earphones",
        "airpods": "earphones",
        "backpack": "backpack",
        "bag": "backpack",
        "water bottle": "water_bottle",
        "water_bottle": "water_bottle",
        "bottle": "water_bottle",
        "charger": "charger",
        "charging cable": "charger",
        "cable": "charger",
    }
    return item_aliases.get(item, item)


def record_item_finding(username: str, item_type: str, room: str) -> dict:
    """Record a 'Found Here' event into user_item_findings.
    Empirical habits are only recorded for authenticated users (never for guests).
    Increments count on repeated finding."""
    username = (username or "").strip().lower()
    if not username or username == "guest":
        return {"success": False, "message": "Guest findings are not recorded."}

    item_type = normalize_item_type(item_type)
    room = (room or "").strip().lower()
    if not item_type or not room:
        return {"success": False, "message": "Valid item and room are required."}

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_item_findings (username, item_type, room, found_count)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(username, item_type, room)
            DO UPDATE SET found_count = user_item_findings.found_count + 1, last_found_at=CURRENT_TIMESTAMP
        """, (username, item_type, room))
        conn.commit()
        return {"success": True, "message": f"Recorded finding for {item_type} in {room}."}


def get_item_findings(username: str, item_type: str | None = None) -> list[dict]:
    """Fetch repeated findings for a specific authenticated user and item, ordered by found_count DESC.
    Guests return an empty list."""
    username = (username or "").strip().lower()
    if not username or username == "guest":
        return []

    with get_db_connection() as conn:
        cursor = conn.cursor()
        if item_type:
            norm_item = normalize_item_type(item_type)
            cursor.execute(
                "SELECT id, username, item_type, room, found_count, last_found_at FROM user_item_findings WHERE username = ? AND item_type = ? ORDER BY found_count DESC, id DESC",
                (username, norm_item)
            )
        else:
            cursor.execute(
                "SELECT id, username, item_type, room, found_count, last_found_at FROM user_item_findings WHERE username = ? ORDER BY found_count DESC, id DESC",
                (username,)
            )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

