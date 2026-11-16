import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


class Database:
    def __init__(self, db_path: str = "data/tutor.db"):
        database_path = Path(db_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(database_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Internal helper to establish a connection with Row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create the four required tables if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learner_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    item_type TEXT NOT NULL,
                    times_seen INTEGER DEFAULT 0,
                    times_missed INTEGER DEFAULT 0,
                    last_seen TEXT,
                    next_due TEXT,
                    difficulty TEXT DEFAULT 'normal'
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    ended_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_state (
                    session_id INTEGER PRIMARY KEY,
                    current_turn INTEGER NOT NULL,
                    state_data TEXT,
                    FOREIGN KEY (session_id) REFERENCES sessions (id)
                )
            """)
            conn.commit()

    def record_result(self, item_id: int, correct: bool) -> None:
        """Updates item review stats based on performance."""
        now = datetime.now(UTC)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT times_seen, times_missed FROM learner_items WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return

            times_seen = row["times_seen"] + 1
            times_missed = row["times_missed"] + (0 if correct else 1)

            if correct:
                next_due = now + timedelta(days=1)
            else:
                delta_minutes = 5 if row["times_missed"] >= 1 else 10
                next_due = now + timedelta(minutes=delta_minutes)

            cursor.execute("""
                UPDATE learner_items
                SET times_seen = ?, times_missed = ?, last_seen = ?, next_due = ?
                WHERE id = ?
            """, (times_seen, times_missed, now.isoformat(), next_due.isoformat(), item_id))
            conn.commit()

    def get_due_items(self, limit: int) -> List[Dict[str, Any]]:
        """Retrieves items due for revision, prioritized by frequency of misses."""
        now_str = datetime.now(UTC).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM learner_items
                WHERE next_due IS NULL OR next_due <= ?
                ORDER BY times_missed DESC, next_due ASC
                LIMIT ?
            """, (now_str, limit))
            return [dict(row) for row in cursor.fetchall()]

    def save_checkpoint(self, session_id: int, current_turn: int, state_data: str = "") -> None:
        """Saves or updates the current session position checkpoint."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO session_state (session_id, current_turn, state_data)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) 
                DO UPDATE SET current_turn = excluded.current_turn, state_data = excluded.state_data
            """, (session_id, current_turn, state_data))
            conn.commit()

    def load_checkpoint(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves the saved session position checkpoint."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT session_id, current_turn, state_data FROM session_state WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None