from io import BytesIO

import soundfile as sf
from phonemizer import phonemize as espeak_phonemize

from pronunciation.phonemizer import SpanishPhonemizer
from pronunciation.alignment import score_ipa


class PronunciationScorer:
    def __init__(self):
        self.phonemizer = SpanishPhonemizer()

    def score(self, audio_bytes: bytes, target_text: str):
        audio, sample_rate = sf.read(
            BytesIO(audio_bytes),
            dtype="float32",
        )
        if audio.size == 0:
            raise ValueError("Audio cannot be empty.")
        if audio.ndim == 2:
            audio = audio.mean(axis=1)

        reference_ipa = espeak_phonemize(
            target_text,
            language="es",
            backend="espeak",
            strip=True,
            with_stress=False,
            njobs=1,
        )

        predicted_ipa = self.phonemizer.transcribe(
            audio, sample_rate
        )

        return {
            "per": score_ipa(reference_ipa, predicted_ipa),
            "reference_ipa": reference_ipa,
            "predicted_ipa": predicted_ipa,
            "validated": False,
        }