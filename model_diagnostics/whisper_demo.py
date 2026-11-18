
import sys
import time
from pathlib import Path

from audio.pipeline import AudioRecorder, WhisperTranscriber
from model_diagnostics.paths import fixture_path

MODEL = "small"
AUDIO_FILE = fixture_path("audio", "spanish_sample.mp3")


def main():
    if any(arg in {"--live", "--microphone"} for arg in sys.argv[1:]):
        recorder = AudioRecorder()
        print("Press Enter to start speaking...")
        input()
        recorder.start()
        print("Recording. Press Enter to stop.")
        input()
        wav = recorder.stop()
        print(f"Captured: {len(wav)} WAV bytes")
        start = time.perf_counter()
        result = WhisperTranscriber(
            model_name=MODEL,
            device="cpu",
            compute_type="int8",
        ).transcribe(wav)
        elapsed = time.perf_counter() - start
        print(f"Detected language: {result['language']}")
        print(f"Transcription: {result['text']}")
        print(f"Time: {elapsed:.2f} seconds")
        print("PASS")
        return

    start = time.perf_counter()

    try:
        audio = Path(AUDIO_FILE).read_bytes()
        result = WhisperTranscriber(
            model_name=MODEL,
            device="cpu",
            compute_type="int8",
        ).transcribe(audio)

        elapsed = time.perf_counter() - start

        print(f"Model: {MODEL}")
        print(f"Detected language: {result['language']}")
        print(f"Transcription: {result['text']}")
        print(f"Time: {elapsed:.2f} seconds")
        print("PASS")

    except (OSError, RuntimeError, ValueError) as error:
        elapsed = time.perf_counter() - start
        print(f"FAIL: {error}")
        print(f"Time: {elapsed:.2f} seconds")
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
