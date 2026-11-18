import time

import numpy as np
import soundfile as sf

from model_diagnostics.paths import fixture_path
from pronunciation.phonemizer import SpanishPhonemizer

CLIPS = [
    str(fixture_path("generated", "clip_1.wav")),
    str(fixture_path("generated", "clip_2.wav")),
    str(fixture_path("generated", "clip_3.wav")),
]

def main():
    print("Loading CNAM model...")
    start = time.time()

    phonemizer = SpanishPhonemizer()

    print(f"Model loaded in {time.time() - start:.2f}s\n")

    for path in CLIPS:
        audio, sample_rate = sf.read(path)

        # Convert stereo audio to mono
        if audio.ndim == 2:
            audio = np.mean(audio, axis=1)

        start = time.time()
        ipa = phonemizer.transcribe(audio, sample_rate)

        print(f"File: {path}")
        print(f"IPA:  {ipa}")
        print(f"Time: {time.time() - start:.2f}s")
        print("-" * 50)


if __name__ == "__main__":
    main()
