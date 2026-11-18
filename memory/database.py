import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, db_path: str = "data/tutor.db") -> None:
        database_path = Path(db_path)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(database_path)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=2)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 2000")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

            if "learner_items" in tables:
                columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(learner_items)")
                }
                if "lemma" not in columns:
                    conn.execute(
                        "ALTER TABLE learner_items RENAME TO learner_items_legacy"
                    )

            if "sessions" in tables:
                columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(sessions)")
                }
                if "source_type" not in columns:
                    conn.execute("ALTER TABLE sessions RENAME TO sessions_legacy")

            if "turns" in tables:
                columns = {
                    row["name"]
                    for row in conn.execute("PRAGMA table_info(turns)")
                }
                if "exercise_json" not in columns:
                    conn.execute("ALTER TABLE turns RENAME TO turns_legacy")

            if "session_state" in tables:
                columns = {
                    row["name"]
                    for row in conn.execute(
                        "PRAGMA table_info(session_state)"
                    )
                }
                if "plan_json" not in columns:
                    conn.execute(
                        "ALTER TABLE session_state "
                        "RENAME TO session_state_legacy"
                    )

            conn.executescript("""
                CREATE TABLE IF NOT EXISTS learner_items (
                    id INTEGER PRIMARY KEY,
                    lemma TEXT NOT NULL,
                    surface TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK (kind IN ('word','phrase','grammar')),
                    gloss_en TEXT NOT NULL,
                    box INTEGER NOT NULL DEFAULT 1
                        CHECK (box BETWEEN 1 AND 5),
                    times_seen INTEGER NOT NULL DEFAULT 0,
                    times_missed INTEGER NOT NULL DEFAULT 0,
                    last_seen TEXT,
                    next_due TEXT,
                    source TEXT,
                    UNIQUE (lemma, kind)
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    source_type TEXT NOT NULL CHECK (
                        source_type IN ('topic','chapter')
                    ),
                    source_ref TEXT,
                    level TEXT NOT NULL CHECK (level IN ('A1','A2','B1')),
                    summary TEXT
                );

                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY,
                    session_id INTEGER NOT NULL REFERENCES sessions(id),
                    step INTEGER NOT NULL,
                    exercise_json TEXT NOT NULL,
                    answer_text TEXT,
                    stt_conf REAL,
                    correct INTEGER CHECK (correct IN (1,0) OR correct IS NULL),
                    phoneme_json TEXT,
                    feedback_json TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE (session_id, step)
                );

                CREATE TABLE IF NOT EXISTS session_state (
                    session_id INTEGER PRIMARY KEY REFERENCES sessions(id),
                    mode TEXT NOT NULL,
                    step INTEGER NOT NULL,
                    plan_json TEXT NOT NULL,
                    quiz_json TEXT,
                    state_data TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS books (
                    id INTEGER PRIMARY KEY,
                    sha256 TEXT NOT NULL UNIQUE,
                    filename TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    page_count INTEGER NOT NULL,
                    uploaded_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chapters (
                    id INTEGER PRIMARY KEY,
                    book_id INTEGER NOT NULL REFERENCES books(id),
                    idx INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    page_start INTEGER NOT NULL,
                    page_end INTEGER NOT NULL,
                    word_count INTEGER NOT NULL,
                    cleaned_text TEXT,
                    summary TEXT,
                    vocab_json TEXT,
                    processed_at TEXT,
                    UNIQUE (book_id, idx)
                );

                CREATE TABLE IF NOT EXISTS chapter_progress (
                    chapter_id INTEGER PRIMARY KEY REFERENCES chapters(id),
                    sessions_completed INTEGER NOT NULL DEFAULT 0,
                    mastery REAL NOT NULL DEFAULT 0,
                    last_studied TEXT
                );
            """)

            legacy_exists = conn.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'table' AND name = 'learner_items_legacy'"
            ).fetchone()
            if legacy_exists:
                conn.execute("""
                    INSERT OR IGNORE INTO learner_items (
                        lemma, surface, kind, gloss_en, box, times_seen,
                        times_missed, last_seen, next_due, source
                    )
                    SELECT
                        content,
                        content,
                        CASE
                            WHEN item_type IN ('word','phrase','grammar')
                            THEN item_type ELSE 'word'
                        END,
                        content,
                        1,
                        times_seen,
                        times_missed,
                        last_seen,
                        next_due,
                        'topic'
                    FROM learner_items_legacy
                """)
                conn.execute("DROP TABLE learner_items_legacy")

            sessions_legacy_exists = conn.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'table' AND name = 'sessions_legacy'"
            ).fetchone()
            if sessions_legacy_exists:
                conn.execute("""
                    INSERT OR IGNORE INTO sessions (
                        id, started_at, ended_at, source_type, source_ref, level
                    )
                    SELECT id, started_at, ended_at, 'topic', NULL, 'A1'
                    FROM sessions_legacy
                """)
                conn.execute("DROP TABLE sessions_legacy")

            turns_legacy_exists = conn.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'table' AND name = 'turns_legacy'"
            ).fetchone()
            if turns_legacy_exists:
                conn.execute("""
                    INSERT OR IGNORE INTO turns (
                        id, session_id, step, exercise_json, answer_text,
                        stt_conf, correct, phoneme_json, feedback_json, created_at
                    )
                    SELECT
                        id,
                        session_id,
                        id,
                        '{"type":"repeat"}',
                        CASE WHEN role = 'learner' THEN content ELSE NULL END,
                        NULL,
                        NULL,
                        NULL,
                        CASE WHEN role = 'assistant' THEN content ELSE NULL END,
                        timestamp
                    FROM turns_legacy
                """)
                conn.execute("DROP TABLE turns_legacy")

            state_legacy_exists = conn.execute(
                "SELECT 1 FROM sqlite_master "
                "WHERE type = 'table' AND name = 'session_state_legacy'"
            ).fetchone()
            if state_legacy_exists:
                conn.execute("""
                    INSERT OR IGNORE INTO session_state (
                        session_id, mode, step, plan_json, quiz_json,
                        state_data, updated_at
                    )
                    SELECT
                        session_id,
                        'lesson',
                        current_turn,
                        '{}',
                        NULL,
                        state_data,
                        COALESCE(
                            (SELECT MAX(created_at)
                             FROM turns
                             WHERE turns.session_id = session_state_legacy.session_id),
                            CURRENT_TIMESTAMP
                        )
                    FROM session_state_legacy
                """)
                conn.execute("DROP TABLE session_state_legacy")
            conn.commit()

    @staticmethod
    def wait_days(box: int) -> int:
        return {1: 1, 2: 3, 3: 7, 4: 14, 5: 30}[box]

    def add_learner_item(
        self,
        lemma: str,
        surface: str,
        kind: str,
        gloss_en: str,
        source: str,
    ) -> int:
        if kind not in {"word", "phrase", "grammar"}:
            raise ValueError("kind must be word, phrase, or grammar")
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO learner_items (
                    lemma, surface, kind, gloss_en, source
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (lemma, surface, kind, gloss_en, source),
            )
            conn.commit()
            if cursor.lastrowid:
                return cursor.lastrowid
            row = conn.execute(
                "SELECT id FROM learner_items WHERE lemma = ? AND kind = ?",
                (lemma, kind),
            ).fetchone()
            if row is None:
                raise RuntimeError("Failed to add learner item")
            return row["id"]

    def record_result(
        self,
        item_id: int,
        correct: bool,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT times_seen, times_missed, box "
                "FROM learner_items WHERE id = ?",
                (item_id,),
            ).fetchone()
            if row is None:
                return

            times_seen = row["times_seen"] + 1
            times_missed = row["times_missed"]
            if correct:
                box = min(row["box"] + 1, 5)
            else:
                box = 1
                times_missed += 1
            next_due = now + timedelta(days=self.wait_days(box))

            conn.execute(
                """
                UPDATE learner_items
                SET times_seen = ?, times_missed = ?, box = ?,
                    last_seen = ?, next_due = ?
                WHERE id = ?
                """,
                (
                    times_seen,
                    times_missed,
                    box,
                    now.isoformat(),
                    next_due.isoformat(),
                    item_id,
                ),
            )
            conn.commit()

    def get_due_items(
        self,
        limit: int = 20,
        now: datetime | None = None,
    ) -> list[dict[str, Any]]:
        now = now or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        if limit < 0:
            raise ValueError("limit cannot be negative")

        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM learner_items
                WHERE next_due IS NULL OR next_due <= ?
                ORDER BY times_missed DESC, next_due ASC
                LIMIT ?
                """,
                (now.isoformat(), limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def create_session(
        self,
        source_type: str,
        source_ref: str,
        level: str,
        now: datetime | None = None,
    ) -> int:
        if source_type not in {"topic", "chapter"}:
            raise ValueError("source_type must be topic or chapter")
        if level not in {"A1", "A2", "B1"}:
            raise ValueError("level must be A1, A2, or B1")
        now = now or datetime.now(UTC)
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions (
                    started_at, source_type, source_ref, level
                ) VALUES (?, ?, ?, ?)
                """,
                (now.isoformat(), source_type, source_ref, level),
            )
            conn.commit()
            return cursor.lastrowid

    def record_turn(
        self,
        session_id: int,
        step: int,
        exercise_json: str,
        answer_text: str | None,
        stt_conf: float | None,
        correct: bool | None,
        phoneme_json: str | None,
        feedback_json: str,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        correct_value = None if correct is None else int(correct)
        with self._get_connection() as conn:
            conn.execute("BEGIN")
            conn.execute(
                """
                INSERT INTO turns (
                    session_id, step, exercise_json, answer_text, stt_conf,
                    correct, phoneme_json, feedback_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    step,
                    exercise_json,
                    answer_text,
                    stt_conf,
                    correct_value,
                    phoneme_json,
                    feedback_json,
                    now.isoformat(),
                ),
            )
            conn.execute(
                """
                INSERT INTO session_state (
                    session_id, mode, step, plan_json, quiz_json, updated_at
                ) VALUES (?, 'lesson', ?, '{}', NULL, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    step = excluded.step,
                    updated_at = excluded.updated_at
                """,
                (session_id, step, now.isoformat()),
            )
            conn.commit()

    def save_checkpoint(
        self,
        session_id: int,
        current_turn: int,
        state_data: str = "",
        plan_json: str = "{}",
        mode: str = "lesson",
        quiz_json: str | None = None,
        now: datetime | None = None,
    ) -> None:
        now = now or datetime.now(UTC)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO session_state (
                    session_id, mode, step, plan_json, quiz_json,
                    state_data, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    mode = excluded.mode,
                    step = excluded.step,
                    plan_json = excluded.plan_json,
                    quiz_json = excluded.quiz_json,
                    state_data = excluded.state_data,
                    updated_at = excluded.updated_at
                """,
                (
                    session_id,
                    mode,
                    current_turn,
                    plan_json,
                    quiz_json,
                    state_data,
                    now.isoformat(),
                ),
            )
            conn.commit()

    def load_checkpoint(self, session_id: int) -> dict[str, Any] | None:
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT session_id, mode, step, plan_json, quiz_json,
                       state_data, updated_at
                FROM session_state
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["current_turn"] = result["step"]
            return result
