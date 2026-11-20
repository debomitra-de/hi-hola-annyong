from io import BytesIO
from typing import Any

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly


def convert_wav(
    wav_bytes: bytes,
    target_sample_rate: int,
    target_channels: int = 1,
) -> bytes:
    """Decode WAV bytes, resample, and return mono/stereo 16-bit PCM WAV bytes."""
    if target_sample_rate <= 0:
        raise ValueError("target_sample_rate must be positive")
    if target_channels not in (1, 2):
        raise ValueError("target_channels must be 1 or 2")

    audio, sample_rate = sf.read(
        BytesIO(wav_bytes),
        dtype="float32",
        always_2d=True,
    )
    if audio.size == 0:
        raise ValueError("Audio cannot be empty")

    if target_channels == 1:
        audio = np.mean(audio, axis=1)
    elif audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)

    if sample_rate != target_sample_rate:
        if audio.ndim == 1:
            gcd = np.gcd(sample_rate, target_sample_rate)
            audio = resample_poly(
                audio,
                target_sample_rate // gcd,
                sample_rate // gcd,
            )
        else:
            channels = []
            for channel in range(audio.shape[1]):
                gcd = np.gcd(sample_rate, target_sample_rate)
                channels.append(
                    resample_poly(
                        audio[:, channel],
                        target_sample_rate // gcd,
                        sample_rate // gcd,
                    )
                )
            audio = np.column_stack(channels)

    output = BytesIO()
    sf.write(output, audio, target_sample_rate, format="WAV", subtype="PCM_16")
    return output.getvalue()


class AudioRecorder:
    """Tap-to-start/tap-to-stop mono WAV recorder."""

    def __init__(self, sample_rate: int = 16_000) -> None:
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive")
        self.sample_rate = sample_rate
        self._stream: Any = None
        self._chunks: list[np.ndarray] = []

    def start(self) -> None:
        try:
            import sounddevice as sd
        except (ImportError, OSError) as error:
            raise RuntimeError(
                "Microphone recording requires sounddevice. Install requirements.txt."
            ) from error

        if self._stream is not None:
            raise RuntimeError("Recording is already in progress")

        def callback(
            indata: np.ndarray,
            frames: int,
            time_info: object,
            status: object,
        ) -> None:
            del frames, time_info, status
            self._chunks.append(np.array(indata[:, 0], copy=True))

        self._chunks = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=callback,
        )
        self._stream.start()

    def stop(self) -> bytes:
        if self._stream is None:
            raise RuntimeError("No recording is in progress")

        self._stream.stop()
        self._stream.close()
        self._stream = None

        if not self._chunks:
            raise RuntimeError("No microphone audio was captured")

        audio = np.concatenate(self._chunks)
        self._chunks = []
        output = BytesIO()
        sf.write(
            output,
            audio,
            self.sample_rate,
            format="WAV",
            subtype="PCM_16",
        )
        return output.getvalue()


def record_wav(duration_seconds: float, sample_rate: int = 16_000) -> bytes:
    """Record mono WAV for a fixed maximum duration."""
    if duration_seconds <= 0:
        raise ValueError("duration_seconds must be positive")
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    try:
        import sounddevice as sd
    except (ImportError, OSError) as error:
        raise RuntimeError(
            "Microphone recording requires sounddevice. Install requirements.txt."
        ) from error

    audio = sd.rec(
        int(duration_seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    output = BytesIO()
    sf.write(output, audio[:, 0], sample_rate, format="WAV", subtype="PCM_16")
    return output.getvalue()


def play_wav(wav_bytes: bytes) -> None:
    """Play WAV bytes using PortAudio. Requires sounddevice."""
    try:
        import sounddevice as sd
    except (ImportError, OSError) as error:
        raise RuntimeError(
            "Audio playback requires sounddevice. Install requirements.txt."
        ) from error

    audio, sample_rate = sf.read(BytesIO(wav_bytes), dtype="float32", always_2d=False)
    sd.play(audio, sample_rate)
    sd.wait()


class WhisperTranscriber:
    """Lazy faster-whisper adapter that accepts and returns in-memory WAV bytes."""

    def __init__(
        self,
        model_name: str = "small",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._model: Any = None

    def _get_model(self) -> Any:
        if self._model is None:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(self, wav_bytes: bytes, initial_prompt: str = "") -> dict:
        converted = convert_wav(wav_bytes, 16_000, 1)
        audio, _sample_rate = sf.read(BytesIO(converted), dtype="float32")
        segments, info = self._get_model().transcribe(
            audio,
            language="es",
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
            temperature=0.0,
            initial_prompt=initial_prompt or None,
        )

        segment_list = list(segments)
        text = " ".join(segment.text.strip() for segment in segment_list).strip()
        words: list[tuple[str, float]] = []
        for segment in segment_list:
            for word in getattr(segment, "words", None) or []:
                confidence = getattr(word, "probability", 0.0)
                words.append((word.word.strip(), float(confidence)))

        # confidence signals for STT gate
        avg_logprob = min((getattr(s, "avg_logprob", 0.0) for s in segment_list), default=0.0)
        no_speech_prob = max((getattr(s, "no_speech_prob", 0.0) for s in segment_list), default=0.0)
        compression_ratio = max((getattr(s, "compression_ratio", 1.0) for s in segment_list), default=1.0)
        unclear = (
            not segment_list
            or avg_logprob < -0.8
            or no_speech_prob > 0.6
            or compression_ratio > 2.4
        )

        return {
            "text": text,
            "words": words,
            "language": info.language,
            "unclear": unclear,
            "avg_logprob": avg_logprob,
            "no_speech_prob": no_speech_prob,
        }


class KokoroSynthesizer:
    """Lazy Kokoro TTS adapter producing in-memory WAV bytes."""

    def __init__(
        self,
        voice: str = "ef_dora",
        lang_code: str = "e",
        sample_rate: int = 24_000,
    ) -> None:
        self.voice = voice
        self.lang_code = lang_code
        self.sample_rate = sample_rate
        self._pipeline: Any = None

    def _get_pipeline(self) -> Any:
        if self._pipeline is None:
            from kokoro import KPipeline

            self._pipeline = KPipeline(lang_code=self.lang_code)
        return self._pipeline

    def speak(self, text: str, voice: str | None = None, speed: float = 0.85) -> bytes:
        if not text.strip():
            raise ValueError("text cannot be empty")

        chunks = [
            audio
            for _, _, audio in self._get_pipeline()(
                text.strip() + ".",  # trailing punctuation prevents end-of-sentence cutoff
                voice=voice or self.voice,
                speed=speed,
            )
        ]
        if not chunks:
            return b""

        # append 200ms silence so the last phoneme isn't clipped on playback
        silence = np.zeros(int(self.sample_rate * 0.2), dtype=np.float32)
        combined = np.concatenate(chunks + [silence])
        output = BytesIO()
        sf.write(output, combined, self.sample_rate, format="WAV", subtype="PCM_16")
        return output.getvalue()

    def speak_clarification(self, heard: str, target: str, voice: str | None = None) -> bytes:
        """Speak '¿[heard]? ... [target] ... [target]' — slow target sandwiched for pronunciation."""
        v = voice or self.voice
        parts = [
            (f"¿{heard}?", 0.9),       # reflect back what was heard, normal pace
            (target, 0.65),             # slow first pass — hear each syllable
            (target, 0.9),              # normal speed — full word
        ]
        silence = np.zeros(int(self.sample_rate * 0.3))  # 300ms gap between parts
        all_chunks: list[np.ndarray] = []
        for text, speed in parts:
            chunks = [a for _, _, a in self._get_pipeline()(text, voice=v, speed=speed)]
            if chunks:
                all_chunks.extend(chunks)
                all_chunks.append(silence)
        if not all_chunks:
            return b""
        combined = np.concatenate(all_chunks)
        output = BytesIO()
        sf.write(output, combined, self.sample_rate, format="WAV", subtype="PCM_16")
        return output.getvalue()
        output = BytesIO()
        sf.write(
            output,
            combined,
            self.sample_rate,
            format="WAV",
            subtype="PCM_16",
        )
        return output.getvalue()
