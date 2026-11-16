from typing import Any

_checkpoints: dict[str, Any] = {}
_books: dict[str, Any] = {}


def transcribe(audio_bytes: bytes) -> dict:
    return {
        "text": "Hola, ¿cómo estás?",
        "word_confidences": [0.98, 0.95, 0.91]
    }


def speak(text: str, voice: str) -> bytes:
    return b"fake_audio_data"


def get_due_items(limit: int) -> list:
    return []


def plan_lesson(source_text: str, level: str, due_items: list) -> dict:
    return {
        "source_text": source_text,
        "level": level,
        "due_items": due_items,
    }


def ingest_book(file: Any) -> str:
    book_id = f"book_{len(_books) + 1}"
    _books[book_id] = file
    return book_id


def list_chapters(book_id: str) -> list:
    return []


def process_chapter(chapter_id: str) -> dict:
    return {"chapter_id": chapter_id}


def save_checkpoint(session_id: str, state: Any) -> None:
    _checkpoints[session_id] = state


def load_checkpoint(session_id: str) -> Any:
    return _checkpoints.get(session_id)


def generate_quiz(session_id: str) -> list:
    return []