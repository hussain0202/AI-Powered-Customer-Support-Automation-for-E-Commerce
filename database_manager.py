import sqlite3
import pandas as pd
from pathlib import Path

# Setup paths for database
DB_DIR = Path(__file__).parent / 'database'
DB_PATH = DB_DIR / 'support.db'

def init_db():
    """Initializes the SQLite database and performs safe migrations for new columns."""
    if not DB_DIR.exists():
        DB_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Users table — must be created before tables that reference it
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            full_name     TEXT,
            password_hash TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login    TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_query TEXT,
            bot_response TEXT,
            sentiment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Safe Migrations for Intent, Escalation, and User tracking
    for col_sql in [
        "ALTER TABLE chat_logs ADD COLUMN intent TEXT",
        "ALTER TABLE chat_logs ADD COLUMN escalated INTEGER DEFAULT 0",
        "ALTER TABLE chat_logs ADD COLUMN user_id INTEGER REFERENCES users(id)",
    ]:
        try:
            cursor.execute(col_sql)
        except sqlite3.OperationalError:
            pass  # Column already exists

    # Support tickets table — logs payment issues, complaints, tech issues
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_tickets (
            ticket_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    TEXT,
            issue_type  TEXT,
            description TEXT,
            status      TEXT DEFAULT 'open',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    try:
        cursor.execute("ALTER TABLE support_tickets ADD COLUMN user_id INTEGER REFERENCES users(id)")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Persistent login sessions — token stored in browser cookie
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            token      TEXT PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


def log_support_ticket(order_id: str, issue_type: str, description: str, user_id: int = None) -> int:
    """
    Inserts a support ticket and returns the new ticket_id.
    issue_type: 'payment_issue' | 'complaint' | 'technical_support' | 'human_escalation'
    """
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO support_tickets (order_id, issue_type, description, user_id) VALUES (?, ?, ?, ?)",
            (order_id or "N/A", issue_type, description, user_id),
        )
        ticket_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return ticket_id
    except Exception as e:
        print(f"Database error on log_support_ticket: {e}")
        return -1


def save_chat(user_query, bot_response, sentiment, intent="unknown", escalated=0, user_id: int = None):
    """Saves a single chat interaction including user attribution."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_logs (user_query, bot_response, sentiment, intent, escalated, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (user_query, bot_response, sentiment, intent, escalated, user_id),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database error on save_chat: {e}")

def get_recent_chats(limit=10):
    """Retrieves the most recent chat interactions."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_query, bot_response, sentiment, created_at, intent, escalated 
            FROM chat_logs 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Database error on get_recent_chats: {e}")
        return []

def get_all_chats_df():
    """Retrieves all chat logs as a pandas DataFrame."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        df = pd.read_sql_query("SELECT * FROM chat_logs ORDER BY created_at DESC", conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Database error on get_all_chats_df: {e}")
        return pd.DataFrame()


def get_tickets_summary() -> dict:
    """Returns aggregate metrics for the support_tickets table."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM support_tickets")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM support_tickets WHERE status = 'open'")
        open_count = cursor.fetchone()[0]
        cursor.execute(
            "SELECT issue_type, COUNT(*) as cnt FROM support_tickets GROUP BY issue_type ORDER BY cnt DESC"
        )
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        return {"total": total, "open": open_count, "by_type": by_type}
    except Exception as e:
        print(f"Database error on get_tickets_summary: {e}")
        return {"total": 0, "open": 0, "by_type": {}}


def get_recent_tickets(limit: int = 10) -> list:
    """Returns the most recent support tickets as a list of dicts."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ticket_id, order_id, issue_type, description, status, created_at
            FROM support_tickets
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        cols = ["ticket_id", "order_id", "issue_type", "description", "status", "created_at"]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Database error on get_recent_tickets: {e}")
        return []


def get_user_chats(user_id: int, limit: int = 20) -> list:
    """Returns chat history for a specific user."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_query, bot_response, sentiment, intent, escalated, created_at
            FROM chat_logs
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        cols = ["user_query", "bot_response", "sentiment", "intent", "escalated", "created_at"]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Database error on get_user_chats: {e}")
        return []


def get_user_tickets(user_id: int, limit: int = 20) -> list:
    """Returns support tickets raised by a specific user."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ticket_id, order_id, issue_type, description, status, created_at
            FROM support_tickets
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        cols = ["ticket_id", "order_id", "issue_type", "description", "status", "created_at"]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Database error on get_user_tickets: {e}")
        return []
