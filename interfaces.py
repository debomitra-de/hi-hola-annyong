import os
from typing import Any

_pronunciation_scorer: Any = None
_whisper_transcriber: Any = None
_kokoro_synthesizer: Any = None
PRONUNCIATION_ENABLED = False
_checkpoints: dict[str, Any] = {}
_books: dict[str, Any] = {}


def get_audio_adapter_mode() -> str:
    mode = os.getenv("TUTOR_ADAPTER_MODE", "fake").strip().lower()
    if mode not in {"fake", "real"}:
        raise ValueError("TUTOR_ADAPTER_MODE must be 'fake' or 'real'")
    return mode


def configure_audio_adapters(mode: str) -> None:
    if mode not in {"fake", "real"}:
        raise ValueError("mode must be 'fake' or 'real'")
    os.environ["TUTOR_ADAPTER_MODE"] = mode


def _get_whisper_transcriber() -> Any:
    global _whisper_transcriber
    if _whisper_transcriber is None:
        from audio.pipeline import WhisperTranscriber

        _whisper_transcriber = WhisperTranscriber(
            model_name="small",
            device="cpu",
            compute_type="int8",
        )
    return _whisper_transcriber


def _get_kokoro_synthesizer() -> Any:
    global _kokoro_synthesizer
    if _kokoro_synthesizer is None:
        from audio.pipeline import KokoroSynthesizer

        _kokoro_synthesizer = KokoroSynthesizer(
            voice="ef_dora",
            lang_code="e",
            sample_rate=24_000,
        )
    return _kokoro_synthesizer


def transcribe(audio_bytes: bytes) -> dict:
    if not isinstance(audio_bytes, bytes):
        raise TypeError("audio_bytes must be bytes")
    if not audio_bytes:
        raise ValueError("audio_bytes cannot be empty")
    if get_audio_adapter_mode() == "fake":
        return {
            "text": "Hola, ¿cómo estás?",
            "word_confidences": [0.98, 0.95, 0.91],
        }

    result = _get_whisper_transcriber().transcribe(audio_bytes)
    return {
        "text": result["text"],
        "word_confidences": [confidence for _, confidence in result["words"]],
    }


def speak(text: str, voice: str) -> bytes:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text.strip():
        raise ValueError("text cannot be empty")
    if get_audio_adapter_mode() == "fake":
        return b"fake_audio_data"

    kokoro_voice = "ef_dora" if voice in {"", "default"} else voice
    return _get_kokoro_synthesizer().speak(text, kokoro_voice)


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

def score_pronunciation(audio_bytes: bytes, target_text: str):
    if not PRONUNCIATION_ENABLED:
        return None

    global _pronunciation_scorer

    if _pronunciation_scorer is None:
        from pronunciation.scorer import PronunciationScorer
        _pronunciation_scorer = PronunciationScorer()

    return _pronunciation_scorer.score(audio_bytes, target_text)