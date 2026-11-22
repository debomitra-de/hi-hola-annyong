import logging
import os
import time
import warnings
from typing import Any

# Suppress HuggingFace Hub unauthenticated-request noise
warnings.filterwarnings("ignore", message=".*unauthenticated.*", category=UserWarning)
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

_pronunciation_scorer: Any = None
_whisper_transcriber: Any = None
_kokoro_synthesizer: Any = None
_conversation_engine: Any = None
_conversation_engine_key: tuple[Any, ...] | None = None
_audio_recorder: Any = None
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


def configure_conversation(
    mode: str = "fake",
    level: str = "A1",
    chapter_text: str = "",
    topic: str = "conversation",
    session_id: int | str | None = None,
) -> None:
    global _conversation_engine, _conversation_engine_key
    if mode not in {"fake", "real"}:
        raise ValueError("mode must be 'fake' or 'real'")
    if level not in {"A1", "A2", "B1"}:
        raise ValueError("level must be A1, A2, or B1")

    key = (session_id, mode, level, topic, chapter_text)
    if _conversation_engine is not None and _conversation_engine_key == key:
        os.environ["TUTOR_LLM_MODE"] = mode
        return

    if mode == "real":
        from tutor.conversation import ConversationEngine, OllamaLLM

        llm = OllamaLLM(model="qwen2.5:7b")
    else:
        from tutor.conversation import ConversationEngine, MockLLM

        llm = MockLLM()
    _conversation_engine = ConversationEngine(
        llm=llm,
        level=level,
        chapter_text=chapter_text,
        topic=topic,
    )
    _conversation_engine_key = key
    os.environ["TUTOR_LLM_MODE"] = mode


def generate_tutor_response(learner_text: str) -> dict[str, Any]:
    global _conversation_engine
    if not learner_text.strip():
        raise ValueError("learner_text cannot be empty")
    if _conversation_engine is None:
        configure_conversation(mode="fake")
    logging.info("LLM: generating tutor response for input=%r …", learner_text[:60])
    t0 = time.monotonic()
    message = _conversation_engine.chat(learner_text)
    logging.info("LLM done in %.1fs — es=%r", time.monotonic() - t0, message.es[:80])
    return message.model_dump()


def _get_whisper_transcriber() -> Any:
    global _whisper_transcriber
    if _whisper_transcriber is None:
        from audio.pipeline import WhisperTranscriber

        _whisper_transcriber = WhisperTranscriber(
            model_name="medium",
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


def transcribe(audio_bytes: bytes, initial_prompt: str = "") -> dict:
    del initial_prompt  # STT must preserve the speaker's languages rather than lesson-biasing text
    if not isinstance(audio_bytes, bytes):
        raise TypeError("audio_bytes must be bytes")
    if not audio_bytes:
        raise ValueError("audio_bytes cannot be empty")
    if get_audio_adapter_mode() == "fake":
        return {
            "text": "Hola, ¿cómo estás?",
            "word_confidences": [0.98, 0.95, 0.91],
            "unclear": False,
        }

    logging.info("STT: transcribing %d bytes …", len(audio_bytes))
    t0 = time.monotonic()
    result = _get_whisper_transcriber().transcribe(audio_bytes)
    logging.info("STT done in %.1fs — text=%r unclear=%s lang=%s",
                 time.monotonic() - t0, result["text"], result.get("unclear"), result.get("language"))
    return {
        "text": result["text"],
        "word_confidences": [confidence for _, confidence in result["words"]],
        "unclear": result.get("unclear", False),
    }


def speak(text: str, voice: str) -> bytes:
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text.strip():
        raise ValueError("text cannot be empty")
    if get_audio_adapter_mode() == "fake":
        return b"fake_audio_data"

    logging.info("TTS: synthesising %d chars …", len(text))
    t0 = time.monotonic()
    kokoro_voice = "ef_dora" if voice in {"", "default"} else voice
    wav = _get_kokoro_synthesizer().speak(text, kokoro_voice)
    logging.info("TTS done in %.1fs — %d bytes", time.monotonic() - t0, len(wav))
    return wav


def start_voice_answer(sample_rate: int = 16_000) -> None:
    global _audio_recorder
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if _audio_recorder is not None:
        raise RuntimeError("A voice answer is already being recorded")

    from audio.pipeline import AudioRecorder

    _audio_recorder = AudioRecorder(sample_rate=sample_rate)
    _audio_recorder.start()


def stop_voice_answer(
    level: str = "A1",
    voice: str = "ef_dora",
    play_response: bool = False,
) -> dict[str, Any]:
    global _audio_recorder
    if _audio_recorder is None:
        raise RuntimeError("No voice answer is being recorded")

    try:
        wav = _audio_recorder.stop()
    finally:
        _audio_recorder = None
    return process_voice_answer(
        wav,
        level=level,
        voice=voice,
        play_response=play_response,
    )


def process_voice_answer(
    wav: bytes,
    level: str = "A1",
    voice: str = "ef_dora",
    play_response: bool = False,
) -> dict[str, Any]:
    if level not in {"A1", "A2", "B1"}:
        raise ValueError("level must be A1, A2, or B1")

    if _conversation_engine is None:
        configure_conversation(
            mode=get_audio_adapter_mode(),
            level=level,
        )

    transcript = transcribe(wav)
    learner_text = transcript["text"].strip()

    if not learner_text:
        return {
            "learner_text": "",
            "transcript": transcript,
            "tutor_message": {
                "kind": "system",
                "es": "",
                "en": "I could not hear an answer. Please try speaking again.",
                "items": [],
            },
            "response_wav": b"",
            "unclear": False,
        }

    # STT gate — only skip LLM when there's no speech at all
    if transcript.get("unclear") and not learner_text.strip():
        engine = _conversation_engine
        if engine is not None:
            tutor_msg, slow_word = engine.handle_unclear(learner_text)
        else:
            tutor_msg_dict = {
                "kind": "system", "es": "", "items": [],
                "en": "I didn't catch that. Try once more?",
            }
            return {
                "learner_text": learner_text,
                "transcript": transcript,
                "tutor_message": tutor_msg_dict,
                "response_wav": b"",
                "unclear": True,
            }

        # speak clarification — reflects heard fragment + slow target word
        if slow_word and tutor_msg.es.strip():
            kokoro = _get_kokoro_synthesizer()
            response_wav = kokoro.speak_clarification(
                heard=learner_text.split()[-1] if learner_text.split() else "...",
                target=slow_word,
                voice=voice,
            )
        else:
            response_wav = b""

        if play_response and response_wav:
            from audio.pipeline import play_wav
            play_wav(response_wav)

        return {
            "learner_text": learner_text,
            "transcript": transcript,
            "tutor_message": tutor_msg.model_dump(),
            "response_wav": response_wav,
            "unclear": True,
        }

    tutor_message = generate_tutor_response(learner_text)
    response_wav = speak(tutor_message["es"], voice)

    if play_response:
        if not response_wav:
            raise RuntimeError("Tutor response did not produce audio")
        from audio.pipeline import play_wav
        play_wav(response_wav)

    return {
        "learner_text": learner_text,
        "transcript": transcript,
        "tutor_message": tutor_message,
        "response_wav": response_wav,
        "unclear": False,
    }


def get_due_items(limit: int) -> list:
    return []


def plan_lesson(source_text: str, level: str, due_items: list) -> dict:
    from planner.plan import LessonPlanner

    if not isinstance(due_items, list):
        raise TypeError("due_items must be a list")
    plan = LessonPlanner().plan(source_text, level, due_items)
    return plan.model_dump()


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