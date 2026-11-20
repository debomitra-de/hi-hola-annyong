import pytest

import interfaces
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

    assert result["text"] == "Hola, ¿cómo estás?"
    assert result["word_confidences"] == [0.98, 0.95, 0.91]
    assert result["unclear"] is False


def test_speak_returns_audio_bytes():
    result = speak("Hola, ¿cómo estás?", "default")

    assert result == b"fake_audio_data"
    assert isinstance(result, bytes)


def test_get_due_items_returns_a_list():
    assert get_due_items(10) == []


def test_plan_lesson_returns_requested_inputs():
    due_items = ["greetings"]

    plan = plan_lesson("Hola", "A1", due_items)

    assert plan["level"] == "A1"
    assert plan["source"] == {"type": "topic", "ref": "Hola"}
    assert plan["conversation_goals"]


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


class MockWhisper:
    def transcribe(self, audio_bytes, initial_prompt=""):
        assert audio_bytes == b"real wav"
        return {
            "text": "Me llamo Ana",
            "words": [("Me", 0.99), ("llamo", 0.96), ("Ana", 0.93)],
            "language": "es",
            "unclear": False,
            "avg_logprob": -0.3,
            "no_speech_prob": 0.1,
        }


class MockKokoro:
    def speak(self, text, voice):
        assert text == "Hola"
        assert voice == "ef_dora"
        return b"real wav"


def test_real_transcribe_interface(monkeypatch):
    monkeypatch.setenv("TUTOR_ADAPTER_MODE", "real")
    monkeypatch.setattr(interfaces, "_whisper_transcriber", MockWhisper())

    result = transcribe(b"real wav")
    assert result["text"] == "Me llamo Ana"
    assert result["word_confidences"] == [0.99, 0.96, 0.93]
    assert result["unclear"] is False


def test_real_speak_interface(monkeypatch):
    monkeypatch.setenv("TUTOR_ADAPTER_MODE", "real")
    monkeypatch.setattr(interfaces, "_kokoro_synthesizer", MockKokoro())

    assert speak("Hola", "default") == b"real wav"


def test_process_voice_answer_connects_stt_llm_and_tts(monkeypatch):
    monkeypatch.setattr(
        interfaces,
        "transcribe",
        lambda wav, initial_prompt="": {
            "text": "Quiero una mesa",
            "word_confidences": [0.99, 0.98, 0.97],
            "unclear": False,
        },
    )
    monkeypatch.setattr(
        interfaces,
        "configure_conversation",
        lambda mode, level, chapter_text="": None,
    )
    monkeypatch.setattr(
        interfaces,
        "generate_tutor_response",
        lambda learner_text: {
            "kind": "feedback",
            "es": "Muy bien.",
            "en": "Very good.",
            "items": [],
        },
    )
    monkeypatch.setattr(
        interfaces,
        "speak",
        lambda text, voice: b"spanish tutor wav",
    )

    result = interfaces.process_voice_answer(
        b"learner wav",
        level="A1",
        voice="ef_dora",
    )

    assert result["learner_text"] == "Quiero una mesa"
    assert result["tutor_message"]["es"] == "Muy bien."
    assert result["response_wav"] == b"spanish tutor wav"


def test_process_voice_answer_silence_skips_llm_and_tts(monkeypatch):
    monkeypatch.setattr(
        interfaces,
        "transcribe",
        lambda wav, initial_prompt="": {"text": "", "word_confidences": [], "unclear": False},
    )
    monkeypatch.setattr(
        interfaces,
        "generate_tutor_response",
        lambda learner_text: pytest.fail("LLM should not run for silence"),
    )
    monkeypatch.setattr(
        interfaces,
        "speak",
        lambda text, voice: pytest.fail("TTS should not run for silence"),
    )

    result = interfaces.process_voice_answer(b"silent wav")

    assert result["learner_text"] == ""
    assert result["response_wav"] == b""
    assert "try speaking again" in result["tutor_message"]["en"]


def test_stop_voice_answer_resets_recorder(monkeypatch):
    class MockRecorder:
        def stop(self):
            return b"learner wav"

    monkeypatch.setattr(interfaces, "_audio_recorder", MockRecorder())
    monkeypatch.setattr(
        interfaces,
        "process_voice_answer",
        lambda wav, level, voice, play_response: {
            "learner_text": "Hola",
            "wav": wav,
        },
    )

    result = interfaces.stop_voice_answer()

    assert result["wav"] == b"learner wav"
    assert interfaces._audio_recorder is None


@pytest.mark.parametrize("mode", ["fake", "real"])
def test_configure_audio_adapters_accepts_valid_modes(monkeypatch, mode):
    monkeypatch.delenv("TUTOR_ADAPTER_MODE", raising=False)
    interfaces.configure_audio_adapters(mode)
    assert interfaces.get_audio_adapter_mode() == mode


def test_configure_audio_adapters_rejects_invalid_mode():
    with pytest.raises(ValueError, match="mode must be 'fake' or 'real'"):
        interfaces.configure_audio_adapters("invalid")

def score_pronunciation(audio_bytes, target_text):
    # This is a placeholder implementation for the pronunciation scoring function.
    # In a real scenario, this function would analyze the audio and compare it to the target text.
    return 0.85  # Returning a fixed score for testing purposes.