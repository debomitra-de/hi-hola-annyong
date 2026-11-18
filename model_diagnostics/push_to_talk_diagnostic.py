"""Manual push-to-talk Whisper diagnostic.

Run from a real terminal:
    python -m model_diagnostics.push_to_talk_diagnostic

This script transcribes microphone audio and does not play the recording back.
"""

import time

from audio.pipeline import AudioRecorder, WhisperTranscriber


def main() -> None:
    recorder = AudioRecorder()

    print("Push-to-talk ready.")
    input("Press Enter to START recording: ")
    recorder.start()
    print("Recording started. Speak naturally.")
    input("Press Enter to STOP recording: ")

    wav = recorder.stop()
    print(f"Captured {len(wav)} bytes; transcribing...")

    started = time.perf_counter()
    try:
        result = WhisperTranscriber(
            model_name="small",
            device="cpu",
            compute_type="int8",
        ).transcribe(wav)
    except (OSError, RuntimeError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1) from error

    elapsed = time.perf_counter() - started
    print(f"Detected language: {result['language']}")
    print(f"Transcription: {result['text']}")
    print(f"Time: {elapsed:.2f} seconds")
    print("PASS")


if __name__ == "__main__":
    main()
