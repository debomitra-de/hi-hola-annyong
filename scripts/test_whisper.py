
import time
from faster_whisper import WhisperModel

MODEL = "small"
AUDIO_FILE = "samples/spanish_sample.mp3"


def main():
    start = time.perf_counter()

    try:
        model = WhisperModel(
            MODEL,
            device="cpu",
            compute_type="int8",
        )

        segments, info = model.transcribe(
            AUDIO_FILE,
            language="es",
        )

        transcription = " ".join(
            segment.text.strip() for segment in segments
        )

        elapsed = time.perf_counter() - start

        print(f"Model: {MODEL}")
        print(f"Detected language: {info.language}")
        print(f"Transcription: {transcription}")
        print(f"Time: {elapsed:.2f} seconds")
        print("PASS")

    except Exception as error:
        elapsed = time.perf_counter() - start
        print(f"FAIL: {error}")
        print(f"Time: {elapsed:.2f} seconds")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
