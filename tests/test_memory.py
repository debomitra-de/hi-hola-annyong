from datetime import UTC, datetime, timedelta

import pytest

from memory.database import Database


@pytest.fixture
def db(tmp_path):
    """Fixture providing an isolated Database instance using a temporary file."""
    db_file = tmp_path / "test_tutor.db"
    return Database(db_path=str(db_file))

def test_review_priority(db):
    """Test 1: An item missed more frequently appears before an item answered correctly."""
    past_due = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO learner_items "
            "(lemma, surface, kind, gloss_en, next_due, times_missed) "
            "VALUES (?, ?, 'word', ?, ?, ?)",
            ("manzana", "manzana", "apple", past_due, 0),
        )
        cursor.execute(
            "INSERT INTO learner_items "
            "(lemma, surface, kind, gloss_en, next_due, times_missed) "
            "VALUES (?, ?, 'phrase', ?, ?, ?)",
            ("por favor", "por favor", "please", past_due, 3),
        )
        conn.commit()

    due_items = db.get_due_items(limit=2)
    assert due_items[0]["lemma"] == "por favor"
    assert due_items[1]["lemma"] == "manzana"

def test_due_items_limit(db):
    """Test 2: If 10 items are due and you request 3, you get only 3."""
    past_due = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        for i in range(10):
            cursor.execute(
                "INSERT INTO learner_items "
                "(lemma, surface, kind, gloss_en, next_due) "
                "VALUES (?, ?, 'word', 'test', ?)",
                (f"item_{i}", f"Item {i}", past_due),
            )
        conn.commit()

    due_items = db.get_due_items(limit=3)
    assert len(due_items) == 3

def test_checkpoint_save_and_load(db):
    """Test 3: Save a session state, reload it, and compare the result."""
    session_id = 1
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions "
            "(id, started_at, source_type, source_ref, level) "
            "VALUES (?, ?, 'topic', 'restaurant', 'A1')",
            (session_id, datetime.now(UTC).isoformat()),
        )
        conn.commit()

    db.save_checkpoint(session_id=session_id, current_turn=4, state_data="active_vocab_focus")
    
    checkpoint = db.load_checkpoint(session_id=session_id)
    assert checkpoint is not None
    assert checkpoint["current_turn"] == 4
    assert checkpoint["state_data"] == "active_vocab_focus"

def test_crash_recovery(db):
    """Test 4: Simulate completing turn 2, saving checkpoint, and resuming at turn 3."""
    session_id = 1
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions "
            "(id, started_at, source_type, source_ref, level) "
            "VALUES (?, ?, 'topic', 'restaurant', 'A1')",
            (session_id, datetime.now(UTC).isoformat()),
        )
        conn.commit()

    db.save_checkpoint(session_id=session_id, current_turn=2)

    loaded = db.load_checkpoint(session_id=session_id)
    resumed_turn = loaded["current_turn"] + 1

    assert resumed_turn == 3


def test_leitner_correct_advances_box(db):
    fixed_now = datetime(2026, 11, 18, tzinfo=UTC)
    item_id = db.add_learner_item(
        "hablar",
        "hablo",
        "grammar",
        "to speak",
        "topic:restaurant",
    )

    db.record_result(item_id, correct=True, now=fixed_now)

    with db._get_connection() as conn:
        row = conn.execute(
            "SELECT box, next_due FROM learner_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    assert row["box"] == 2
    assert row["next_due"] == (fixed_now + timedelta(days=3)).isoformat()


def test_leitner_wrong_returns_to_box_one(db):
    fixed_now = datetime(2026, 11, 18, tzinfo=UTC)
    item_id = db.add_learner_item(
        "comer",
        "como",
        "grammar",
        "to eat",
        "topic:restaurant",
    )
    db.record_result(item_id, correct=True, now=fixed_now)
    db.record_result(item_id, correct=True, now=fixed_now)
    db.record_result(item_id, correct=False, now=fixed_now)

    with db._get_connection() as conn:
        row = conn.execute(
            "SELECT box, times_missed, next_due "
            "FROM learner_items WHERE id = ?",
            (item_id,),
        ).fetchone()
    assert row["box"] == 1
    assert row["times_missed"] == 1
    assert row["next_due"] == (fixed_now + timedelta(days=1)).isoformat()


def test_schema_contains_srs_tables(db):
    with db._get_connection() as conn:
        names = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {
        "learner_items",
        "sessions",
        "turns",
        "session_state",
        "books",
        "chapters",
        "chapter_progress",
    } <= names
    