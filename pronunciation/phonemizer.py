"""Spanish speech-to-IPA transcription using the CNAM wav2vec2 model."""

import unicodedata
import numpy as np
import torch
from scipy.signal import resample_poly
from transformers import AutoModelForCTC, AutoProcessor

MODEL_ID = "Cnam-LMSSC/wav2vec2-spanish-phonemizer"
TARGET_SAMPLE_RATE = 16_000


class SpanishPhonemizer:
    """Convert Spanish speech audio into an IPA phoneme sequence."""

    def __init__(self):
        self.processor = AutoProcessor.from_pretrained(MODEL_ID)
        self.model = AutoModelForCTC.from_pretrained(MODEL_ID)
        self.model.eval()

    def transcribe(self, audio: np.ndarray, sample_rate: int) -> str:
        """
        Convert audio into IPA.

        Args:
            audio: Mono audio waveform as a NumPy array.
            sample_rate: Original audio sample rate.

        Returns:
            IPA phoneme transcription.
        """
        if audio.ndim != 1:
            raise ValueError("Audio must be mono (one-dimensional).")

        if sample_rate != TARGET_SAMPLE_RATE:
            gcd = np.gcd(sample_rate, TARGET_SAMPLE_RATE)
            audio = resample_poly(
                audio,
                TARGET_SAMPLE_RATE // gcd,
                sample_rate // gcd,
            )

        inputs = self.processor(
            audio.astype(np.float32),
            sampling_rate=TARGET_SAMPLE_RATE,
            return_tensors="pt",
        )

        with torch.no_grad():
            logits = self.model(**inputs).logits

        predicted_ids = torch.argmax(logits, dim=-1)
        return self.processor.batch_decode(predicted_ids)[0]


# Allophones that represent the same underlying Spanish phoneme
ALLOPHONE_MAP = {
    "β": "b",
    "ð": "d",
    "ɣ": "ɡ",
    "g": "ɡ",
}

def fold_allophones(phonemes: list[str]) -> list[str]:
    return [ALLOPHONE_MAP.get(p, p) for p in phonemes]

STRESS_MARKS = {"ˈ", "ˌ"}
SEPARATORS = {" ", "\t", "\n", ",", ".", "¿", "?", "¡", "!"}

def tokenize_ipa(ipa: str) -> list[str]:
    """Tokenize IPA while keeping diacritics and affricates together."""
    ipa = unicodedata.normalize("NFD", ipa)

    tokens = []
    i = 0

    while i < len(ipa):
        char = ipa[i]

        if char in STRESS_MARKS or char in SEPARATORS:
            i += 1
            continue

        token = char
        i += 1

        while i < len(ipa):
            current = ipa[i]

            # Tie bar connects two sounds into one affricate.
            if current == "\u0361":
                token += current
                i += 1

                if i < len(ipa):
                    token += ipa[i]
                    i += 1
                continue

            # Other combining marks belong to the current sound.
            if unicodedata.combining(current):
                token += current
                i += 1
                continue

            break

        tokens.append(token)

    return tokens

def normalize_ipa(ipa: str) -> list[str]:
    return fold_allophones(tokenize_ipa(ipa))

