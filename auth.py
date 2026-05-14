import hashlib
import os
import sqlite3
import uuid
import datetime
from pathlib import Path
from typing import Any, Dict, Optional

DB_PATH = Path(__file__).parent / "database" / "support.db"


def _hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + key.hex()


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, key_hex = stored.split(":", 1)
        key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 100_000
        )
        return key.hex() == key_hex
    except Exception:
        return False


def register_user(username: str, email: str, full_name: str, password: str) -> Dict[str, Any]:
    username = username.strip().lower()
    email = email.strip().lower()
    full_name = full_name.strip()

    if len(username) < 3:
        return {"success": False, "message": "Username must be at least 3 characters."}
    if not all(c.isalnum() or c == "_" for c in username):
        return {"success": False, "message": "Username can only contain letters, numbers, and underscores."}
    if len(password) < 6:
        return {"success": False, "message": "Password must be at least 6 characters."}
    if "@" not in email or "." not in email.split("@")[-1]:
        return {"success": False, "message": "Please enter a valid email address."}

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            conn.close()
            return {"success": False, "message": "Username already taken. Please choose another."}

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return {"success": False, "message": "An account with this email already exists."}

        pw_hash = _hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, email, full_name, password_hash) VALUES (?, ?, ?, ?)",
            (username, email, full_name, pw_hash),
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": "Account created successfully!",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "full_name": full_name or username,
            },
        }
    except Exception as e:
        return {"success": False, "message": f"Registration failed: {e}"}


def login_user(username_or_email: str, password: str) -> Dict[str, Any]:
    key = username_or_email.strip().lower()
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, email, full_name, password_hash, created_at
            FROM users
            WHERE username = ? OR email = ?
            """,
            (key, key),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"success": False, "message": "No account found with that username or email."}

        user_id, uname, email, full_name, pw_hash, created_at = row

        if not _verify_password(password, pw_hash):
            conn.close()
            return {"success": False, "message": "Incorrect password. Please try again."}

        cursor.execute(
            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?", (user_id,)
        )
        conn.commit()
        conn.close()

        return {
            "success": True,
            "user": {
                "id": user_id,
                "username": uname,
                "email": email,
                "full_name": full_name or uname,
                "created_at": created_at,
            },
        }
    except Exception as e:
        return {"success": False, "message": f"Login failed: {e}"}


def get_user_stats(user_id: int) -> Dict[str, Any]:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chat_logs WHERE user_id = ?", (user_id,))
        total_chats = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM support_tickets WHERE user_id = ?", (user_id,))
        total_tickets = cursor.fetchone()[0]
        conn.close()
        return {"total_chats": total_chats, "total_tickets": total_tickets}
    except Exception:
        return {"total_chats": 0, "total_tickets": 0}


# ── Session management (persistent login via cookie) ──────────────────────────

SESSION_DAYS = 30


def create_session(user_id: int) -> str:
    """Creates a DB-backed session token valid for SESSION_DAYS days."""
    token = str(uuid.uuid4())
    expires = datetime.datetime.utcnow() + datetime.timedelta(days=SESSION_DAYS)
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires.isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"create_session error: {e}")
    return token


def get_session_user(token: str) -> Optional[Dict[str, Any]]:
    """Returns the user dict if the token is valid and not expired, else None."""
    if not token:
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        now = datetime.datetime.utcnow().isoformat()
        cursor.execute(
            """
            SELECT u.id, u.username, u.email, u.full_name, u.created_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ? AND s.expires_at > ?
            """,
            (token, now),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "username": row[1],
            "email": row[2],
            "full_name": row[3] or row[1],
            "created_at": row[4],
        }
    except Exception as e:
        print(f"get_session_user error: {e}")
        return None


def delete_session(token: str) -> None:
    """Deletes a session token from the DB (called on logout)."""
    if not token:
        return
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"delete_session error: {e}")
