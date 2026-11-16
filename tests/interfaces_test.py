from interfaces import speak, transcribe


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

def score_pronunciation(audio_bytes, target_text):
    # This is a placeholder implementation for the pronunciation scoring function.
    # In a real scenario, this function would analyze the audio and compare it to the target text.
    return 0.85  # Returning a fixed score for testing purposes.