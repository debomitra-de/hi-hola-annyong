from interfaces import (
    generate_quiz,
    get_due_items,
    ingest_book,
    list_chapters,
    load_checkpoint,
    plan_lesson,
    process_chapter,
    save_checkpoint,
    speak,
    transcribe,
)


def test_transcribe_returns_text_and_word_confidences():
    result = transcribe(b"fake_audio_data")

    assert result == {
        "text": "Hola, ¿cómo estás?",
        "word_confidences": [0.98, 0.95, 0.91],
    }


def test_speak_returns_audio_bytes():
    result = speak("Hola, ¿cómo estás?", "default")

    assert result == b"fake_audio_data"
    assert isinstance(result, bytes)


def test_get_due_items_returns_a_list():
    assert get_due_items(10) == []


def test_plan_lesson_returns_requested_inputs():
    due_items = ["greetings"]

    assert plan_lesson("Hola", "beginner", due_items) == {
        "source_text": "Hola",
        "level": "beginner",
        "due_items": due_items,
    }


def test_ingest_book_returns_book_id():
    book_id = ingest_book("book contents")

    assert book_id.startswith("book_")
    assert list_chapters(book_id) == []


def test_process_chapter_returns_chapter_id():
    assert process_chapter("chapter_1") == {"chapter_id": "chapter_1"}


def test_checkpoint_can_be_saved_and_loaded():
    state = {"chapter": 1, "progress": 0.5}

    save_checkpoint("session_1", state)

    assert load_checkpoint("session_1") == state


def test_load_checkpoint_returns_none_for_unknown_session():
    assert load_checkpoint("unknown_session") is None


def test_generate_quiz_returns_a_list():
    assert generate_quiz("session_1") == []

def score_pronunciation(audio_bytes, target_text):
    # This is a placeholder implementation for the pronunciation scoring function.
    # In a real scenario, this function would analyze the audio and compare it to the target text.
    return 0.85  # Returning a fixed score for testing purposes.