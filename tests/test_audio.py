import builtins
import sys
from io import BytesIO
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

from audio.pipeline import (
    AudioRecorder,
    convert_wav,
    play_wav,
    record_wav,
)


def make_wav(sample_rate: int = 44_100, seconds: float = 0.02) -> bytes:
    samples = np.zeros(int(sample_rate * seconds), dtype=np.float32)
    output = BytesIO()
    sf.write(output, samples, sample_rate, format="WAV", subtype="PCM_16")
    return output.getvalue()


def test_convert_wav_resamples_and_mono():
    source = make_wav(sample_rate=44_100)

    converted = convert_wav(source, 16_000)

    audio, sample_rate = sf.read(BytesIO(converted), dtype="float32")
    assert sample_rate == 16_000
    assert audio.ndim == 1
    assert len(audio) > 0


def test_convert_wav_rejects_empty_audio():
    output = BytesIO()
    sf.write(output, np.array([], dtype=np.float32), 16_000, format="WAV")

    try:
        convert_wav(output.getvalue(), 16_000)
    except ValueError as error:
        assert str(error) == "Audio cannot be empty"
    else:
        raise AssertionError("Expected ValueError")


@pytest.mark.parametrize("duration", [0, -1])
def test_record_wav_rejects_invalid_time_limits(duration):
    with pytest.raises(ValueError):
        record_wav(duration_seconds=duration)


def test_audio_recorder_rejects_stop_before_start():
    recorder = AudioRecorder()

    with pytest.raises(RuntimeError, match="No recording is in progress"):
        recorder.stop()


class MockInputStream:
    def __init__(self, **kwargs):
        self.callback = kwargs["callback"]
        self.stopped = False
        self.closed = False
        self.callback(
            np.zeros((160, 1), dtype=np.float32),
            160,
            None,
            None,
        )

    def start(self):
        return None

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


def test_audio_recorder_start_stop_returns_wav(monkeypatch):
    mock_sounddevice = SimpleNamespace(
        InputStream=MockInputStream,
    )
    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        mock_sounddevice,
    )

    recorder = AudioRecorder(sample_rate=16_000)
    recorder.start()
    wav = recorder.stop()

    audio, sample_rate = sf.read(BytesIO(wav), dtype="float32")
    assert sample_rate == 16_000
    assert len(audio) == 160


def test_record_wav_uses_sample_rate_and_returns_wav(monkeypatch):
    calls = {}

    def mock_rec(frames, samplerate, channels, dtype):
        calls.update(
            frames=frames,
            samplerate=samplerate,
            channels=channels,
            dtype=dtype,
        )
        return np.zeros((frames, channels), dtype=np.float32)

    mock_sounddevice = SimpleNamespace(
        rec=mock_rec,
        wait=lambda: None,
    )
    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        mock_sounddevice,
    )

    wav = record_wav(duration_seconds=0.5, sample_rate=16_000)
    audio, sample_rate = sf.read(BytesIO(wav), dtype="float32")

    assert calls == {
        "frames": 8000,
        "samplerate": 16_000,
        "channels": 1,
        "dtype": "float32",
    }
    assert sample_rate == 16_000
    assert len(audio) == 8000


def test_play_wav_calls_audio_device(monkeypatch):
    calls = {}
    mock_sounddevice = SimpleNamespace(
        play=lambda audio, sample_rate: calls.update(
            audio=audio,
            sample_rate=sample_rate,
        ),
        wait=lambda: calls.update(waited=True),
    )
    monkeypatch.setitem(
        sys.modules,
        "sounddevice",
        mock_sounddevice,
    )
    wav = make_wav(sample_rate=16_000)

    play_wav(wav)

    assert calls["sample_rate"] == 16_000
    assert calls["waited"] is True
    assert calls["audio"].size > 0


def test_missing_portaudio_reports_clear_error(monkeypatch):
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "sounddevice":
            raise OSError("PortAudio library not found")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    with pytest.raises(RuntimeError, match="Microphone recording"):
        record_wav(duration_seconds=1)
