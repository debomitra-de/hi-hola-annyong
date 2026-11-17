"""Spanish speech-to-IPA transcription using the CNAM wav2vec2 model."""

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