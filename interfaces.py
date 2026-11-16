def transcribe(audio_bytes: bytes) -> dict:
    return {
        "text": "Hola, ¿cómo estás?",
        "word_confidences": [0.98, 0.95, 0.91]
    }
def speak(text: str, voice: str) -> bytes:
    return b"fake_audio_data"