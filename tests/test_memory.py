import pytest
from datetime import UTC, datetime, timedelta
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
        cursor.execute("INSERT INTO learner_items (content, item_type, next_due, times_missed) VALUES (?, ?, ?, ?)",
                       ("Manzana", "vocab", past_due, 0))
        cursor.execute("INSERT INTO learner_items (content, item_type, next_due, times_missed) VALUES (?, ?, ?, ?)",
                       ("Por favor", "vocab", past_due, 3))
        conn.commit()

    due_items = db.get_due_items(limit=2)
    assert due_items[0]["content"] == "Por favor"
    assert due_items[1]["content"] == "Manzana"

def test_due_items_limit(db):
    """Test 2: If 10 items are due and you request 3, you get only 3."""
    past_due = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    with db._get_connection() as conn:
        cursor = conn.cursor()
        for i in range(10):
            cursor.execute("INSERT INTO learner_items (content, item_type, next_due) VALUES (?, ?, ?)",
                           (f"Item {i}", "vocab", past_due))
        conn.commit()

    due_items = db.get_due_items(limit=3)
    assert len(due_items) == 3

def test_checkpoint_save_and_load(db):
    """Test 3: Save a session state, reload it, and compare the result."""
    session_id = 1
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sessions (id, started_at) VALUES (?, ?)", (session_id, datetime.now(UTC).isoformat()))
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
        cursor.execute("INSERT INTO sessions (id, started_at) VALUES (?, ?)", (session_id, datetime.now(UTC).isoformat()))
        conn.commit()

    db.save_checkpoint(session_id=session_id, current_turn=2)

    loaded = db.load_checkpoint(session_id=session_id)
    resumed_turn = loaded["current_turn"] + 1

    assert resumed_turn == 3
    